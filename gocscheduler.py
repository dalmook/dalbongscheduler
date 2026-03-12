# -*- coding: utf-8 -*-
"""
Messenger Scheduler (Tkinter + APScheduler + KnoxMessenger)
필수: pip install -U requests pandas pycryptodome jinja2 apscheduler SQLAlchemy oracledb python-dateutil openpyxl

"""

# ===== 민감 설정(코드에만 보관; UI 비노출) =====
CONFIG = {
    "HOST": "https://openapi.samsung.net/",
    "SYSTEM_ID": "KCC10REST01591",
    "TOKEN": "Bearer 0937decd-9394-38fe-bb5a-348d2d618c67",
    "DEVICE_ID": None,     # 장비등록 후 자동 세팅
    "KEY_HEX":   None,     # 키획득 후 자동 세팅
    "VERIFY_SSL": False,   # 내부망 인증서 이슈 시 False
    "PROXIES": None,
}
LOG_PATH = "scheduler.log"
MAX_BOOT_LOG_LINES = 1000  # 부팅 시 불러올 최대 라인 수

# ===== 표준/외부 모듈 =====
import os
import sys
import json
import gzip
import base64
import time
import io
import logging
from logging.handlers import RotatingFileHandler
from base64 import b64encode
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from urllib.parse import urljoin

import requests
import pandas as pd
from Cryptodome.Cipher import AES
import html as html_mod
import jinja2
from jinja2 import Template
from jinja2 import Environment

# Tkinter
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import tkinter.font as tkfont
from tkinter import colorchooser

# APScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_REMOVED
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.jobstores.base import JobLookupError
import mimetypes
import tempfile
import oracledb as cx_Oracle

cx_Oracle.init_oracle_client(lib_dir=r"C:\instantclient")  # <- 본인 경로로 수정

from dateutil.relativedelta import relativedelta
import re
import openpyxl
from zoneinfo import ZoneInfo  # 이미 추가했으면 생략



# ===== 로깅(회전 로그) 설정 =====
logger = logging.getLogger("MessengerScheduler")
logger.setLevel(logging.INFO)

# 10MB 단위로 5개까지 순환
_rot = RotatingFileHandler(LOG_PATH, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
_rot.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(_rot)

# 콘솔도 보고 싶으면 아래 주석 해제
# _console = logging.StreamHandler(sys.stdout)
# _console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
# logger.addHandler(_console)

# ===== AESCipher & 압축 유틸 =====
class AESCipher:
    def __init__(self, key_hex: str):
        raw = bytes.fromhex(key_hex)
        if len(raw) < 48:
            raise ValueError("key_hex는 48바이트(96 hex)여야 합니다.")
        self.key = raw[:32]
        self.iv = raw[32:48]
        self.BS = 16

    def _pad(self, b: bytes) -> bytes:
        pad_len = self.BS - (len(b) % self.BS)
        return b + bytes([pad_len]) * pad_len

    def _unpad(self, b: bytes) -> bytes:
        return b[:-b[-1]]

    def encrypt(self, data: str) -> str:
        data_b = self._pad(data.encode("utf-8"))
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        enc = cipher.encrypt(data_b)
        return base64.b64encode(enc).decode("utf-8")

    def decrypt(self, data_b64: str) -> str:
        enc = base64.b64decode(data_b64)
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        dec = cipher.decrypt(enc)
        return self._unpad(dec).decode("utf-8")

def compress_csv_payload(csv_text: str) -> str:
    tag = '<!-- {"COMMAND":"SNDCL", "SNDCL":{"KND":"CLDT", "TYPE":"CSV"}} -->'
    raw = bytearray(csv_text, encoding="utf-8")
    comp = gzip.compress(raw)
    length_prefix = len(raw).to_bytes(4, byteorder="little")
    return tag + b64encode(length_prefix + comp).decode("utf-8")

def compress_tagged_payload(text: str, type_name: str = "CSV") -> str:
    """
    Knox Messenger가 인식하는 압축 포맷으로 문자열(text) 래핑.
    주의: HTML도 TYPE="CSV" 로 보내야 정상 렌더되는 환경을 가정.
    """
    tag = f'<!-- {{"COMMAND":"SNDCL", "SNDCL":{{"KND":"CLDT", "TYPE":"{type_name}"}}}} -->'
    raw = bytearray(text, encoding="utf-8")
    comp = gzip.compress(raw)
    length_prefix = len(raw).to_bytes(4, byteorder="little")
    return tag + b64encode(length_prefix + comp).decode("utf-8")

# ===== HTML/RTF 변환 =====
def df_to_html_styled(
    df: pd.DataFrame,
    table_width_px: int = 1000,
    font_size_px: int = 13,
    header_bg: str = "#BBE9F0",
    font_family: str = "Malgun Gothic",
    font_color: str = "#000000",     # 표 글자색
    title: Optional[str] = None,
    title_color: str = "#000000"     # 제목 글자색
) -> str:
    """
    DataFrame을 HTML 테이블로 변환 + CSS 적용
    - 제목의 줄바꿈(\n) → <br/> 변환
    - 표/제목 글자색 분리, 폰트/폰트크기/헤더배경/표너비 지정
    """
    output = io.StringIO()
    df.to_html(output, index=False)
    html_table = output.getvalue()
    output.close()

    css = f"""
    <style>
      table {{ border-collapse: collapse; font-family: '{font_family}', sans-serif; color: {font_color}; }}
      th, td {{ border: 1px solid #999; font-size: {font_size_px}px; text-align: center; }}
      th {{ background-color: {header_bg}; font-weight: bold; }}
    </style>
    """

    title_html = ""
    if title:
        safe_title = html_mod.escape(title).replace("\n", "<br/>")
        title_html = (
            f'<div style="font-weight:bold; margin:6px 0 8px 0; '
            f'font-size:{font_size_px + 2}px; text-align:left; '
            f'font-family:{font_family}; color:{title_color};">'
            f'{safe_title}</div>'
        )

    wrapper = (
        f'<div style="width:{table_width_px}px; font-size:{font_size_px}px; '
        f'text-align:left; font-family:{font_family}; color:{font_color};">'
        f'{title_html}{html_table}</div>'
    )
    return css + wrapper

def compress_rtf_payload(rtf_text: str) -> str:
    """RTF 문서를 메신저 포맷으로 압축/인코딩"""
    tag = '<!-- {"COMMAND":"SNDCL", "SNDCL":{"KND":"CLDT", "TYPE":"RTF"}} -->'
    raw = bytearray(rtf_text, encoding="utf-8")
    comp = gzip.compress(raw)
    length_prefix = len(raw).to_bytes(4, byteorder="little")
    return tag + b64encode(length_prefix + comp).decode("utf-8")

def _rtf_escape(text: str) -> str:
    # RTF 예약문자 이스케이프
    return (text.replace('\\', r'\\')
                .replace('{', r'\{')
                .replace('}', r'\}')
                .replace('\n', r'\line '))

def df_to_rtf_table(df: pd.DataFrame, title: Optional[str] = None) -> str:
    """
    DataFrame → RTF 테이블(헤더 볼드, 셀 테두리)
    - 폰트 'Malgun Gothic'(맑은 고딕), 없으면 기본 폰트 대체
    - 열 너비는 단순 균등
    """
    cols = list(df.columns)
    ncol = len(cols)
    if ncol == 0:
        cols = ["내용"]
        df = pd.DataFrame({"내용": ["(데이터 없음)"]})
        ncol = 1

    col_width = 2600
    cell_positions = []
    acc = 0
    for _ in range(ncol):
        acc += col_width
        cell_positions.append(acc)

    def _rtf_row(cells, header=False):
        parts = [r"\trowd\trgaph108\trleft0"]
        for cx in cell_positions:
            parts.append(
                rf"\clbrdrt\brdrs\brdrw10\clbrdrl\brdrs\brdrw10"
                rf"\clbrdrb\brdrs\brdrw10\clbrdrr\brdrs\brdrw10\cellx{cx}"
            )
        row_cells = []
        for c in cells:
            txt = _rtf_escape("" if c is None else str(c))
            if header:
                row_cells.append(rf"\intbl\b {txt}\b0\cell")
            else:
                row_cells.append(rf"\intbl {txt}\cell")
        parts.append("".join(row_cells))
        parts.append(r"\row")
        return "".join(parts)

    rtf = [r"{\rtf1\ansi\deff0",
           r"{\fonttbl{\f0 Malgun Gothic;}}",
           r"\fs20"]  # 10pt

    if title:
        rtf.append(r"\pard\b " + _rtf_escape(title) + r"\b0\par")

    rtf.append(_rtf_row(cols, header=True))
    for _, row in df.iterrows():
        rtf.append(_rtf_row([row.get(c) for c in cols], header=False))

    rtf.append("}")
    return "".join(rtf)

# ===== 템플릿 치환 유틸 =====
def render_row_template(row: pd.Series, template: str) -> str:
    """(기존 호환) 행 컬럼만 치환"""
    text = template
    for col in row.index:
        text = text.replace("{"+str(col)+"}", str(row[col]))
    return text

def render_with_globals(row: Optional[pd.Series], template: str, gvars: Dict[str, str]) -> str:
    """행 컬럼 + 전역 치환(오늘/전일 등)을 함께 적용
       우선순위: 행 컬럼 > 전역값"""
    text = template
    for k, v in (gvars or {}).items():
        text = text.replace("{"+str(k)+"}", str(v))
    if row is not None:
        for col in row.index:
            text = text.replace("{"+str(col)+"}", str(row[col]))
    return text

# ===== DB 실행 =====
def run_sql(dsn: str, user: str, password: str, sql: str) -> pd.DataFrame:
    with cx_Oracle.connect(user=user, password=password, dsn=dsn) as con:
        df = pd.read_sql(sql, con)
    return df


# ===== KnoxMessenger =====
#== 방 제목 길이 보정 유틸(이모지 포함 안전하게 128바이트 제한)
def _limit_utf8mb4_bytes(s: str, max_bytes: int = 128) -> str:
    """utf-8 기준 바이트 길이로 잘라서 반환 (이모지 포함 안전)"""
    if not s:
        return s
    b = s.encode("utf-8")
    if len(b) <= max_bytes:
        return s
    # 바이트 단위로 잘라서 디코드 가능한 지점까지 후퇴
    cut = max_bytes
    while cut > 0:
        try:
            return b[:cut].decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            cut -= 1
    return ""  # 안전망


class KnoxMessenger:
    def __init__(self, host: str, systemId: str, token: str, *,
                 proxies: Optional[Dict[str,str]] = None,
                 verify_ssl: bool = True,
                 timeout: int = 30):
        self.host = host
        self.systemId = systemId
        self.token = token  # 'Bearer ...'

        self.userID: str = ""
        self.x_device_id: str = ""
        self.key: str = ""
        self.channelAuthKey: str = ""

        self.adaptivecard: Dict[str, Any] = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.3",
            "body": [
                {"type":"Container","items":[
                    {"type":"TextBlock","text":"공급망 챗봇","fontType":"Default","size":"Small","weight":"Bolder"},
                    {"type":"TextBlock","text":"FAMILY 미등록 등록 알림","spacing":"Small","fontType":"Default","size":"Medium","weight":"Bolder"}
                ]},
                {"type":"Container","spacing":"Padding","items":[
                    {"type":"TextBlock","text":"아래 FAMILY 코드 미등록 ITEM 송부드립니다.","fontType":"Default","isSubtle":True,"wrap":True},
                    {"type":"TextBlock","text":"확인 하여 입력 부탁드립니다.","fontType":"Default","isSubtle":True,"spacing":"None","wrap":True},
                    {"type":"TextBlock","text":"※ FAMILY 등록 메뉴얼","spacing":"Medium","fontType":"Default","separator":True,"isSubtle":True,"color":"Accent","weight":"Bolder"}
                ]},
            ]
        }

        self._session = requests.Session()
        if proxies:
            self._session.proxies.update(proxies)
        self._verify_ssl = verify_ssl
        self._timeout = timeout
        self._aes: Optional[AESCipher] = None

    # 내부 헬퍼
    def _headers(self, *, json_ct=True) -> Dict[str,str]:
        h = {"Authorization": self.token, "x-device-id": self.x_device_id or "", "x-device-type": "relation"}
        if json_ct:
            h["Accept"] = "application/json"
            h["Content-Type"] = "application/json"
        return h

    def _encrypt_body(self, body_obj: dict) -> str:
        if not self._aes:
            if not self.key:
                raise RuntimeError("암호화 키 없음: getKeys() 먼저 호출")
            self._aes = AESCipher(self.key)
        return self._aes.encrypt(str(body_obj))

    def _decrypt_body(self, enc_text: str) -> dict:
        if not self._aes:
            if not self.key:
                raise RuntimeError("암호화 키 없음: getKeys() 먼저 호출")
            self._aes = AESCipher(self.key)
        dec = self._aes.decrypt(enc_text)
        return json.loads(dec)

    # 1) 장비 등록 & 키 획득
    def device_regist(self) -> str:
        url = f"{self.host}/messenger/contact/api/v1.0/device/o1/reg"
        headers = {"Authorization": self.token, "System-ID": self.systemId}
        r = self._session.get(url, headers=headers, timeout=self._timeout, verify=self._verify_ssl)
        r.raise_for_status()
        data = r.json()
        self.userID = str(data.get("userID",""))
        self.x_device_id = str(data.get("deviceServerID",""))
        if not self.x_device_id:
            raise RuntimeError("device_regist 실패: deviceServerID 없음")
        return self.x_device_id

    def getKeys(self) -> Dict[str,str]:
        if not self.x_device_id:
            raise RuntimeError("x_device_id 없음: device_regist() 먼저")
        url = f"{self.host}/messenger/msgctx/api/v1.0/key/getkeys"
        headers = {"Authorization": self.token, "x-device-id": self.x_device_id}
        r = self._session.get(url, headers=headers, timeout=self._timeout, verify=self._verify_ssl)
        r.raise_for_status()
        data = r.json()
        self.key = data.get("key","")
        self.channelAuthKey = data.get("channelauthkey","")
        if not self.key:
            raise RuntimeError("getKeys 실패: key 없음")
        self._aes = AESCipher(self.key)
        return {"key": self.key, "channelAuthKey": self.channelAuthKey}

    # 2) 사용자 조회
    def getuserpid(self, sso_ids: List[str]) -> List[str]:
        if not self.x_device_id:
            raise RuntimeError("x_device_id 없음: device_regist() 먼저")
        url = f"{self.host}/messenger/contact/api/v1.0/profile/o1/search/loginid"
        # (일부 엔드포인트가 사내 배포 환경마다 다를 수 있음: 필요 시 수정)
        url = f"{self.host}/messenger/contact/api/v1.0/profile/o1/search/loginid"
        headers = self._headers(json_ct=True)
        headers["System-ID"] = self.systemId
        body = {"singleIdList": [{"singleId": x} for x in sso_ids]}
        r = self._session.post(url, headers=headers, data=json.dumps(body),
                               timeout=self._timeout, verify=self._verify_ssl)
        r.raise_for_status()
        data = r.json()
        res = data.get("userSearchResult", {}).get("searchResultList", [])
        users = [x.get("userID") for x in res if x.get("userID")]
        if not users:
            raise RuntimeError("getuserpid 결과 없음")
        self.userpid = users
        return users

    # 3) 채팅방 생성
    def room_create(
        self,
        receivers_userid: List[str],
        *,
        chatType: int = 1,
        chatroom_title: Optional[str] = None,  # ← 이름 인자
    ) -> str:
        if not self.key:
            raise RuntimeError("암호화 키 없음: getKeys() 먼저")
        url = f"{self.host}/messenger/message/api/v1.0/message/createChatroomRequest"
        headers = self._headers(json_ct=True)
        request_id = int(time.time() * 1000)

        body = {
            "requestId": request_id,
            "chatType": chatType,
            "receivers": receivers_userid,
        }
        if chatroom_title:
            body["chatroomTitle"] = _limit_utf8mb4_bytes(chatroom_title, 128)  # ← 문서 규격 준수

        enc = self._encrypt_body(body)
        r = self._session.post(url, headers=headers, data=enc,
                               timeout=self._timeout, verify=self._verify_ssl)
        r.raise_for_status()
        data = self._decrypt_body(r.text)
        cid = data.get("chatroomId")
        if not cid:
            raise RuntimeError("room_create 실패: chatroomId 없음")
        return cid

    # 4) 메시지 전송
    def chat_request(self, chatroom_id: str, *, msg_type: int, chat_msg: str, msg_ttl: int = 3600) -> dict:
        if not self.key:
            raise RuntimeError("암호화 키 없음: getKeys() 먼저")
        url = f"{self.host}/messenger/message/api/v1.0/message/chatRequest"
        headers = self._headers(json_ct=True)
        request_id = int(time.time() * 1000)
        body = {"requestId": request_id, "chatroomId": chatroom_id,
                "chatMessageParams": [{"msgId": request_id, "msgType": msg_type, "chatMsg": chat_msg, "msgTtl": msg_ttl}]}
        enc = self._encrypt_body(body)
        r = self._session.post(url, headers=headers, data=enc, timeout=self._timeout, verify=self._verify_ssl)
        r.raise_for_status()
        return self._decrypt_body(r.text)

    def send_text(self, chatroom_id: str, text: str) -> dict:
        return self.chat_request(chatroom_id, msg_type=0, chat_msg=text)

    def send_adaptive_card(self, chatroom_id: str, card: Optional[Dict[str,Any]] = None) -> dict:
        obj = card if card is not None else self.adaptivecard
        # Knox 측이 문자열 JSON을 기대하는 구현에 맞춤
        payload = json.dumps({"adaptiveCards": str(obj).replace("True","true").replace("'", '\"')})
        return self.chat_request(chatroom_id, msg_type=19, chat_msg=payload)

    def send_table_csv(self, chatroom_id: str, df: pd.DataFrame) -> dict:
        csv_text = df.to_csv(index=False)
        payload = compress_csv_payload(csv_text)
        return self.chat_request(chatroom_id, msg_type=7, chat_msg=payload)

    def send_table_html(
        self,
        chatroom_id: str,
        df: pd.DataFrame,
        title: Optional[str] = None,
        *,
        table_width_px: int = 1000,
        font_size_px: int = 13,
        header_bg: str = "#BBE9F0",
        font_family: str = "Malgun Gothic",
        font_color: str = "#000000",
        title_color: str = "#000000",
    ) -> dict:
        html = df_to_html_styled(
            df,
            table_width_px=table_width_px,
            font_size_px=font_size_px,
            header_bg=header_bg,
            font_family=font_family,
            font_color=font_color,
            title=title,
            title_color=title_color,
        )
        payload = compress_tagged_payload(html, type_name="CSV")  # Knox HTML은 CSV 태그로 송신
        return self.chat_request(chatroom_id, msg_type=7, chat_msg=payload)

    def send_table_rtf(self, chatroom_id: str, df: pd.DataFrame, title: Optional[str] = None) -> dict:
        rtf_text = df_to_rtf_table(df, title=title)
        payload = compress_rtf_payload(rtf_text)
        return self.chat_request(chatroom_id, msg_type=7, chat_msg=payload)

    # 호환 유틸
    def get_compressed_msg(self, msg: str) -> str:
        raw = bytearray(msg, encoding="utf-8")
        comp = gzip.compress(raw)
        length_prefix = len(raw).to_bytes(4, byteorder="little")
        return b64encode(length_prefix + comp).decode("utf-8")

    def get_dataframe_to_chat_msg(self, df: pd.DataFrame) -> str:
        tag = '<!-- {"COMMAND":"SNDCL", "SNDCL":{"KND":"CLDT", "TYPE":"CSV"}} -->'
        csv_text = df.to_csv(index=False)
        return tag + self.get_compressed_msg(csv_text)
# ===== Part 1/3 끝 =====
# ===== Part 2/3 시작 =====
# ---------------- 수신자/스케줄러/잡 실행 ----------------

def build_receivers(manual_sso_csv: str, df: Optional[pd.DataFrame], df_receiver_col: Optional[str]) -> List[str]:
    receivers = []
    if manual_sso_csv and manual_sso_csv.strip():
        receivers += [x.strip() for x in manual_sso_csv.split(",") if x.strip()]
    if df is not None and df_receiver_col:
        if df_receiver_col in df.columns:
            receivers += [str(x) for x in df[df_receiver_col].dropna().astype(str).tolist()]
    # 중복 제거 + 정렬
    return sorted(list(set(receivers)))


# ---------------- 스케줄러 ----------------
JOB_DB_URL = "sqlite:///jobs.sqlite"  # 실행 폴더에 jobs.sqlite 생성
scheduler = BackgroundScheduler(
    jobstores={"default": SQLAlchemyJobStore(url=JOB_DB_URL)},
    job_defaults={"coalesce": True, "max_instances": 1}
)
scheduler.start()

def _apply_globals_brace(text: str, gvars: dict) -> str:
    """문자열 내 {key} 형태를 gvars 값으로 단순 치환 (JSON 안전)"""
    if not text or not gvars:
        return text
    out = text
    for k, v in gvars.items():
        out = out.replace("{" + str(k) + "}", str(v))
    return out

def _runtime_gvars() -> dict:
    now = datetime.now()
    today = now.date()
    yday = today - timedelta(days=1)
    first_day_of_month = today.replace(day=1)
    last_day_of_prev_month = first_day_of_month - timedelta(days=1)
    return {
        "now": now.strftime("%Y-%m-%d %H:%M:%S"),
        "today": today.strftime("%Y-%m-%d"),
        "yesterday": yday.strftime("%Y-%m-%d"),
        "ymd": today.strftime("%Y%m%d"),
        "md": today.strftime("%m/%d"),          # ← 이 줄 추가
        "ym": today.strftime("%Y%m"),
        "first_day_of_month": first_day_of_month.strftime("%Y-%m-%d"),
        "last_day_of_prev_month": last_day_of_prev_month.strftime("%Y-%m-%d"),
    }


def job_send_messages(payload: dict):
    """
    payload keys (발췌):
    - host, system_id, token, key_hex?, device_id?, verify_ssl, proxies, dryrun
    - dsn, user, pw, sql
    - send_general, send_template, send_table, send_card
    - general_text, template, card_json
    - table_title_from_general, receivers_csv, df_receiver_col, group_send, chatroom_id
    - table_width_px, font_size_px, header_bg, font_family, font_color, title_color
    - globals (전역 치환 변수: today, yesterday, now 등)
    """
    try:
        # Knox 인스턴스
        km = KnoxMessenger(
            CONFIG["HOST"], CONFIG["SYSTEM_ID"], CONFIG["TOKEN"],
            proxies=CONFIG["PROXIES"],
            verify_ssl=CONFIG["VERIFY_SSL"],
            timeout=30
        )

        # device_id/key_hex 준비
        if not CONFIG["DEVICE_ID"]:
            device_id = km.device_regist()
            CONFIG["DEVICE_ID"] = device_id
            logger.info(f"[INIT] device_id: {device_id}")
        else:
            km.x_device_id = CONFIG["DEVICE_ID"]

        if not CONFIG["KEY_HEX"]:
            keys = km.getKeys()
            CONFIG["KEY_HEX"] = keys["key"]
            logger.info(f"[INIT] key_hex len={len(keys['key'])}")
        else:
            km.key = CONFIG["KEY_HEX"]

        # 데이터 조회(옵션)
        df = None
        if payload.get("sql") and all(payload.get(k) for k in ("dsn", "user", "pw")):
            df = run_sql(payload["dsn"], payload["user"], payload["pw"], payload["sql"])
            logger.info(f"[DATA] rows={0 if df is None else len(df)}")

        # 수신자
        receivers = build_receivers(payload.get("receivers_csv", ""), df, payload.get("df_receiver_col"))
        if not receivers:
            logger.warning("[WARN] 수신자 없음, 전송 중단")
            return
                # === 가드: 표 전송 체크인데 표 데이터가 없으면 전체 전송 차단 ===
        if payload.get("send_table", False) and (df is None or getattr(df, "empty", True)):
            logger.warning("[BLOCK] '표 전송'이 선택되었지만 표 데이터가 없습니다. 모든 전송을 중단합니다.")
            return


        # 채팅방
        chatroom_id = payload.get("chatroom_id")
        chatroom_title = payload.get("chatroom_title")  # ← 추가

        if not chatroom_id:
            if payload.get("group_send", True):
                users = km.getuserpid(receivers)
                chatroom_id = km.room_create(
                    users,
                    chatType=1,
                    chatroom_title=chatroom_title,  # ← 제목 전달
                )
                logger.info(f"[INFO] 방 생성: chatroom_id={chatroom_id}, title={chatroom_title or '(미지정)'}")
            else:
                # 1:1 전송 시에는 서버에서 제목을 무시할 가능성 있음
                pass

        # 전송 플래그
        send_general  = payload.get("send_general", False)
        send_template = payload.get("send_template", False)
        send_table    = payload.get("send_table", False)
        send_card     = payload.get("send_card", False)

        # 전역 치환값
        # 전역 치환값(실행 시각 기준으로 재계산 + 페이로드 병합)
        payload_g = payload.get("globals", {}) or {}
        gvars = {**payload_g, **_runtime_gvars()}  # 같은 키는 ‘실행 시각’ 값이 우선


        # 공통 텍스트
        general_text = payload.get("general_text", "")
        # 일반 메시지에도 전역 치환 적용
        for k, v in gvars.items():
            general_text = general_text.replace("{"+str(k)+"}", str(v))

        template     = payload.get("template", "")
        use_title    = payload.get("table_title_from_general", False)

        # 4) Adaptive Card (마지막)
        if send_card:
            import json as _json
            card_text = payload.get("card_json") or ""

            # 전역 치환({today} 등)
            for k, v in gvars.items():
                card_text = card_text.replace("{"+str(k)+"}", str(v))

            try:
                card_obj = _json.loads(card_text)
            except Exception as e:
                logger.error(f"[ERROR] Adaptive Card JSON 파싱 실패: {e}")
                card_obj = None

            if card_obj:
                if payload.get("group_send", True):
                    if payload.get("dryrun", True):
                        logger.info(f"[DRYRUN] send_adaptive_card to chatroom={chatroom_id}\n{str(card_obj)[:400]}")
                    else:
                        km.send_adaptive_card(chatroom_id, card=card_obj)
                        logger.info(f"[OK] Adaptive Card 전송 완료 chatroom={chatroom_id}")
                else:
                    users = km.getuserpid(receivers)
                    for u in users:
                        cr = km.room_create([u], chatType=0)
                        if payload.get("dryrun", True):
                            logger.info(f"[DRYRUN] send_adaptive_card to chatroom={cr}\n{str(card_obj)[:400]}")
                        else:
                            km.send_adaptive_card(cr, card=card_obj)
                            logger.info(f"[OK] Adaptive Card 전송 완료 chatroom={cr}")

        # 1) 일반 메시지 (가장 먼저)
        if send_general:
            if payload.get("group_send", True):
                if payload.get("dryrun", True):
                    logger.info(f"[DRYRUN] send_general to chatroom={chatroom_id}\n{general_text[:500]}")
                else:
                    km.send_text(chatroom_id, general_text)
                    logger.info(f"[OK] 일반 메시지 전송 완료 chatroom={chatroom_id}, bytes={len(general_text.encode('utf-8'))}")
            else:
                users = km.getuserpid(receivers)
                for u in users:
                    cr = km.room_create([u], chatType=0)
                    if payload.get("dryrun", True):
                        logger.info(f"[DRYRUN] send_general to chatroom={cr}\n{general_text[:500]}")
                    else:
                        km.send_text(cr, general_text)
                        logger.info(f"[OK] 일반 메시지 전송 완료 chatroom={cr}, bytes={len(general_text.encode('utf-8'))}")

        # 2) 템플릿 메시지 (두 번째, 전역 치환 + 행 컬럼 치환)
        if send_template:
            if df is None or df.empty:
                logger.info("[INFO] 템플릿 전송 선택됨: 데이터가 없어 렌더링 대상이 없습니다. 건너뜀.")
            else:
                msgs = [render_with_globals(r, template, gvars) for _, r in df.iterrows()]
                # (옵션) 중복 제거 원하면 아래 주석 해제
                # msgs = list(dict.fromkeys(msgs))
                text = "\n".join(msgs)

                if payload.get("group_send", True):
                    if payload.get("dryrun", True):
                        logger.info(f"[DRYRUN] send_template to chatroom={chatroom_id}\n{text[:500]}")
                    else:
                        km.send_text(chatroom_id, text)
                        logger.info(f"[OK] 템플릿 전송 완료 chatroom={chatroom_id}, bytes={len(text.encode('utf-8'))}")
                else:
                    users = km.getuserpid(receivers)
                    for u in users:
                        cr = km.room_create([u], chatType=0)
                        if payload.get("dryrun", True):
                            logger.info(f"[DRYRUN] send_template to chatroom={cr}\n{text[:500]}")
                        else:
                            km.send_text(cr, text)
                            logger.info(f"[OK] 템플릿 전송 완료 chatroom={cr}, bytes={len(text.encode('utf-8'))}")

        # 3) 표(HTML) (세 번째)
        if send_table:
            if df is None or df.empty:
                logger.warning("[WARN] 표 전송이 선택되었지만 데이터가 없어 작업 전체를 중단합니다.")
                return
            else:
                # UI에서 넘어온 값(없으면 기본값)
                tw = int(payload.get("table_width_px", 1000))
                fs = int(payload.get("font_size_px", 13))
                hb = payload.get("header_bg", "#BBE9F0")
                ff = payload.get("font_family", "Malgun Gothic")
                fc = payload.get("font_color", "#000000")
                tc = payload.get("title_color", "#000000")

                # 제목: 옵션 활성 시 일반 메시지(치환 적용됨)를 제목으로 사용
                title_for_table = general_text if use_title and general_text else None

                if payload.get("group_send", True):
                    if payload.get("dryrun", True):
                        logger.info(
                            f"[DRYRUN] send_table(HTML) to chatroom={chatroom_id}, "
                            f"rows={len(df)}, title={'ON' if title_for_table else 'OFF'} "
                            f"| width={tw} font={fs} header_bg={hb} font_color={fc} title_color={tc}"
                        )
                    else:
                        km.send_table_html(
                            chatroom_id, df, title=title_for_table,
                            table_width_px=tw, font_size_px=fs, header_bg=hb,
                            font_family=ff, font_color=fc, title_color=tc
                        )
                        logger.info(
                            f"[OK] 표 전송 완료 chatroom={chatroom_id}, rows={len(df)}, "
                            f"title={'ON' if title_for_table else 'OFF'} "
                            f"| width={tw} font={fs} header_bg={hb} font_color={fc} title_color={tc}"
                        )
                else:
                    users = km.getuserpid(receivers)
                    for u in users:
                        cr = km.room_create([u], chatType=0)
                        if payload.get("dryrun", True):
                            logger.info(
                                f"[DRYRUN] send_table(HTML) to chatroom={cr}, rows={len(df)}, "
                                f"title={'ON' if title_for_table else 'OFF'} "
                                f"| width={tw} font={fs} header_bg={hb} font_color={fc} title_color={tc}"
                            )
                        else:
                            km.send_table_html(
                                cr, df, title=title_for_table,
                                table_width_px=tw, font_size_px=fs, header_bg=hb,
                                font_family=ff, font_color=fc, title_color=tc
                            )
                            logger.info(
                                f"[OK] 표 전송 완료 chatroom={cr}, rows={len(df)}, "
                                f"title={'ON' if title_for_table else 'OFF'} "
                                f"| width={tw} font={fs} header_bg={hb} font_color={fc} title_color={tc}"
                            )



        logger.info("[OK] 작업 완료")

    except Exception as e:
        # 스택 포함
        logger.exception(f"[ERROR] 작업 실패: {e}")

# ---------------- Tkinter App ----------------

# 첨부 없으면 JSON, 있으면 멀티파트로 자동 전송
# ← 전역 함수이므로 @staticmethod 제거
def send_mail_api(
    *, sender_id: str, subject: str, contents: str,
    content_type: str = "HTML", doc_secu_type: str = "PERSONAL",  # PERSONAL | OFFICIAL | PROHIBIT_FORWARD
    recipients: List[Dict[str, str]], reserved_time: Optional[str] = None,
    attachments: Optional[List[str]] = None, proxies: Optional[Dict[str, str]] = None,
    verify_ssl: bool = False, timeout: int = 30,
) -> dict:
    headers_common = {
        "Authorization": CONFIG["TOKEN"],
        "System-ID": CONFIG["SYSTEM_ID"],
    }
    mail_json: Dict[str, Any] = {
        "subject": subject,
        "contents": contents,
        "contentType": content_type,     # "TEXT" | "HTML" | "MIME"
        "docSecuType": doc_secu_type,    # "PERSONAL" | "OFFICIAL" | "PROHIBIT_FORWARD"
        "sender": {"emailAddress": f"{sender_id}@samsung.com"},
        "recipients": recipients,
    }
    if reserved_time:
        mail_json["reservedTime"] = reserved_time  # "yyyy-MM-dd HH:mm"

    url = f'{CONFIG["HOST"].rstrip("/")}/mail/api/v2.0/mails/send?userId={sender_id}'
    s = requests.Session()
    if proxies:
        s.proxies.update(proxies)

    attach_list = attachments or []
    if not attach_list:
        headers = dict(headers_common)
        headers["Content-Type"] = "application/json"
        r = s.post(
            url,
            data=json.dumps(mail_json, ensure_ascii=False),
            headers=headers,
            verify=verify_ssl,
            timeout=timeout,
        )
    else:
        files = [("mail", (None, json.dumps(mail_json, ensure_ascii=False), "application/json"))]
        for path in attach_list:
            try:
                fname = os.path.basename(path)
                ctype = mimetypes.guess_type(fname)[0] or "application/octet-stream"
                files.append(("attachments", (fname, open(path, "rb"), ctype)))
            except Exception as e:
                logger.warning(f"[MAIL] 첨부 실패: {path} ({e})")
        r = s.post(url, headers=headers_common, files=files, verify=verify_ssl, timeout=timeout)
        for _, ft in files[1:]:
            try:
                ft[1].close()
            except Exception:
                pass

    if not (200 <= r.status_code < 300):
        logger.error(f"[MAIL][HTTP {r.status_code}] {r.text[:1000]}")
    r.raise_for_status()
    return r.json() if r.text.strip() else {"ok": True}


# [추가] 동적 파이썬 실행(안전 축소 환경)
# [추가] 동적 파이썬 실행(안전 축소 환경)

def run_py_safely(code: str, env: dict) -> dict:
    # 한 공간(ns)에 다 넣고, exec도 그 공간 하나만 사용
    ns = {}
    ns.update(globals())      # 바깥에서 쓸 수 있는 것들(예: run_sql, df_to_html_styled 등) 복사
    ns.update(env or {})      # 스케줄러가 넘겨준 df/gvars/dsn 등 주입

    exec(code, ns, ns)  # globals=locals 동일
    main_fn = ns.get("main")
    if callable(main_fn):
        ret = main_fn(env or {})
        if isinstance(ret, dict):
            ns.update(ret)
        elif isinstance(ret, (str, bytes)):
            ns["html"] = ret.decode("utf-8", errors="ignore") if isinstance(ret, bytes) else ret
        else:
            ns["html"] = str(ret)
    return ns







# --- 상단 유틸(전역) 추가 ---
def _normalize_email(em: str) -> str:
    em = em.strip()
    return em if "@" in em else f"{em}@samsung.com"

def _split_csv(s: Optional[str]) -> list[str]:
    return [x.strip() for x in (s or "").split(",") if x and x.strip()]


# --- 교체: 원메일 합치기 ---
def job_send_mail(payload: dict) -> None:
    """
    여러 블록(sql_blocks)을 하나의 메일로 묶어 전송.
    - 제목: payload["mail_subject"] 우선, 없으면 'YYYY-MM-DD 블록 N건'
    - 본문: 각 블록을 <h2>{블록제목}</h2> + 렌더링 결과로 섹션화하여 결합
    - 수신자/첨부: 모든 블록의 합집합
    """
    try:
        import tempfile  # ✅ 자동 첨부 사용 시 필요 (상단에 이미 있으면 삭제 가능)

        payload_g: dict = payload.get("globals", {}) or {}
        gvars: dict = {**payload_g, **_runtime_gvars()}  # 실행 시각 기준 값 우선

        # ✅ 전체 옵션: 모든 블록 SQL이 공백이면 전송 중단
        if payload.get("skip_if_no_sql"):
            if all(not (blk.get("sql") or "").strip() for blk in payload.get("sql_blocks", [])):
                logger.info("[MAIL] skip_if_no_sql=ON, 모든 블록 SQL 비어있음 → 전송 취소")
                return

        content_type: str = (payload.get("content_type") or "HTML").upper()
        doc_secu: str = payload.get("doc_secu_type", "PERSONAL")
        reserved: Optional[str] = payload.get("reserved_time")

        # ✅ 첨부 합집합 (payload + block)
        attach_union: set[str] = set(payload.get("attachments") or [])

        # ✅ 수신자 합집합
        to_set  = set(_normalize_email(e) for e in _split_csv(payload.get("receivers_csv")))
        cc_set  = set(_normalize_email(e) for e in _split_csv(payload.get("receivers_cc_csv")))
        bcc_set = set(_normalize_email(e) for e in _split_csv(payload.get("receivers_bcc_csv")))

        sections: list[str] = []
        subject_ctx: dict[str, Any] = dict(gvars)

        def _subst_subject(s: str, ctx: dict) -> str:
            out = s or ""
            for k, v in (ctx or {}).items():
                out = out.replace("{"+str(k)+"}", str(v))
            return out

        for idx, blk in enumerate(payload.get("sql_blocks", []), start=1):
            title: str = blk.get("title", f"블록{idx}")
            sql: str = (blk.get("sql") or "").strip()
            subj_t: str = blk.get("subject", "")
            html_t: str = blk.get("html_tpl", "")

            # ✅ 블록별 첨부도 합집합에 포함
            attach_union.update(blk.get("attachments") or [])

            if blk.get("skip_if_no_sql") and not sql:
                logger.info(f"[MAIL][{title}] SQL 비어있음 + 미전송 옵션 → 이 블록 건너뜀")
                continue

            py_code: str = (blk.get("py_code") or "").strip()

            # 1) SQL (블록 단위 접속 정보 우선)
            df: Optional[pd.DataFrame] = None
            dsn_b  = (blk.get("dsn")  or payload.get("dsn")  or "").strip()
            user_b = (blk.get("user") or payload.get("user") or "").strip()
            pw_b   = (blk.get("pw")   or payload.get("pw")   or "").strip()

            if sql and all([dsn_b, user_b, pw_b]):
                s = sql
                for k, v in gvars.items():
                    s = s.replace("{"+str(k)+"}", str(v))
                df = run_sql(dsn_b, user_b, pw_b, s)
                logger.info(f"[MAIL][{title}] SQL rows={0 if df is None else len(df)} (dsn={dsn_b})")

                # ✅ 자동 첨부(SQL→엑셀)
                try:
                    if blk.get("auto_attach_sql_excel") and isinstance(df, pd.DataFrame):
                        safe_title = "".join(c if c.isalnum() or c in " ._-" else "_" for c in title)
                        fname = f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                        tmp_path = os.path.join(tempfile.gettempdir(), fname)
                        df.to_excel(tmp_path, index=False)
                        attach_union.add(tmp_path)
                        logger.info(f"[MAIL][{title}] 자동 첨부 생성: {tmp_path}")
                except Exception as e:
                    logger.warning(f"[MAIL][{title}] 자동 첨부 실패: {e}")

            elif sql:
                logger.warning(f"[MAIL][{title}] SQL 지정됨 but 접속정보 부족 → 건너뜀 (dsn/user/pw 필요)")

            # 2) PY (df/gvars + 실제 사용한 접속정보 제공)
            env = {"df": df, "gvars": gvars, "dsn": dsn_b, "user": user_b, "pw": pw_b}
            extra: dict = run_py_safely(py_code, env) if py_code else {}

            # 메일 제목 치환 컨텍스트에 extra 반영
            try:
                for k, v in (extra or {}).items():
                    if isinstance(v, (str, int, float)):
                        subject_ctx[k] = v
            except Exception as e:
                logger.warning(f"[MAIL] 제목 컨텍스트(extra) 갱신 실패: {e}")

            # 3) HTML 표 생성
            html_table: str = ""
            if isinstance(df, pd.DataFrame) and not df.empty:
                html_table = df_to_html_styled(df, table_width_px=1000, font_size_px=13)
                # 첫 행 값도 subject_ctx에(선택)
                try:
                    row0 = df.iloc[0].to_dict()
                    for k, v in row0.items():
                        if isinstance(v, (str, int, float)):
                            subject_ctx.setdefault(str(k), v)
                except Exception as e:
                    logger.warning(f"[MAIL] 제목 컨텍스트(df row0) 갱신 실패: {e}")

            # py가 HTML을 돌려줬을 때 우선권 처리
            html_from_py = None
            for k in ("__RESULT_HTML__", "RESULT_HTML", "result_html", "html"):
                v = (extra or {}).get(k)
                if isinstance(v, (str, bytes)):
                    html_from_py = v.decode("utf-8", errors="ignore") if isinstance(v, bytes) else v
                    break

            # 4) 템플릿 렌더
            ctx: dict[str, Any] = {}
            ctx.update(gvars); ctx.update(extra); ctx["html_table"] = html_table

            def _subst(s: str) -> str:
                out = s or ""
                for k, v in ctx.items():
                    out = out.replace("{"+str(k)+"}", str(v))
                return out

            section_title = _subst(subj_t) or title
            section_body  = _subst(html_t)

            if not section_body.strip() and isinstance(html_from_py, str):
                section_body = html_from_py

            if "py_html" not in ctx and isinstance(html_from_py, str):
                ctx["py_html"] = html_from_py
                if "{py_html}" in (html_t or "") and not section_body.strip():
                    section_body = _subst(html_t)

            sections.append(f"<h2>{section_title}</h2>\n{section_body}")

        # ✅ 블록이 전부 스킵되면 메일 자체를 보내지 않음
        if not sections:
            logger.warning("[MAIL] 유효한 섹션이 0건 → 전송 취소")
            return

        # ✅ 최종 본문/제목은 루프 밖에서 1회만 생성
        contents: str = "<html><body>\n" + "\n<hr/>\n".join(sections) + "\n</body></html>"

        mail_subject_tpl = (payload.get("mail_subject") or "")
        mail_subject = _subst_subject(mail_subject_tpl, subject_ctx).strip() if mail_subject_tpl else \
            f"[보고] {(gvars.get('today') or datetime.now().strftime('%Y-%m-%d'))} 블록 {len(sections)}건"

        # 수신자 객체
        rec_objs: list[dict] = []
        for em in sorted(to_set):
            rec_objs.append({"emailAddress": em, "recipientType": "TO"})
        for em in sorted(cc_set):
            rec_objs.append({"emailAddress": em, "recipientType": "CC"})
        for em in sorted(bcc_set):
            rec_objs.append({"emailAddress": em, "recipientType": "BCC"})
        if not rec_objs:
            logger.warning("[MAIL] 수신자 없음. 취소")
            return

        if payload.get("mail_no_send"):
            logger.info(f"[MAIL] mail_no_send=ON → 메일 전송 스킵 (sections={len(sections)}, attach={len(attach_union)})")
            return

        if payload.get("dryrun", False):
            logger.info(f"[DRYRUN][MAIL] subject={mail_subject} | sections={len(sections)} "
                        f"| TO={len(to_set)} CC={len(cc_set)} BCC={len(bcc_set)} "
                        f"| attach={len(attach_union)}")
            return

        send_mail_api(
            sender_id=payload["sender_id"],
            subject=mail_subject,
            contents=contents,
            content_type=content_type,
            doc_secu_type=doc_secu,
            recipients=rec_objs,
            reserved_time=reserved,
            attachments=sorted(attach_union),
            proxies=payload.get("proxies"),
            verify_ssl=payload.get("verify_ssl", False),
        )
        logger.info(f"[OK][MAIL] one-shot sent. sections={len(sections)} "
                    f"| TO={len(to_set)} CC={len(cc_set)} BCC={len(bcc_set)}")

    except Exception as e:
        logger.exception(f"[ERROR] 메일 작업 실패: {e}")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("메신저 자동 전송 머신")
        self.geometry("1120x950")
        self.minsize(920, 700)  # 창 최소 크기 보장
        self.jobs = {}

        # [메일 블록 상태 선초기화]
        from typing import Optional
        self._mail_blocks: list[dict] = []          # 빈 리스트로 초기화
        self._mail_selected: Optional[int] = None   # 현재 선택 인덱스  
        # ✅ 추가: "현재 편집중인 메일 job id"
        self._mail_edit_job_id = None     
        self._mail_editing_job_id = None 

        # UI 구성
        self._build_ui()

        # APScheduler 리스너
        scheduler.add_listener(self._on_job_executed, EVENT_JOB_EXECUTED)
        scheduler.add_listener(self._on_job_removed,  EVENT_JOB_REMOVED)

        # 기존 잡 로딩
        self._load_jobs_into_tree()
    # ---- 메일 잡 아카이브(삭제 백업) 도구 ----

    def on_mail_clear_edit(self):
        """✅ 편집 모드 해제(신규 등록 모드로 복귀)"""
        self._mail_edit_job_id = None
        if hasattr(self, "var_mail_edit_hint"):
            self.var_mail_edit_hint.set("현재: 신규 등록 모드")
        logger.info("[MAIL] 편집 모드 해제 → 신규 등록 모드")

    def on_mail_update_job(self):
        """
        ✅ 더블클릭으로 로드한 '기존 메일 job'을 수정 후 업데이트(재등록)
        - job id 유지
        - trigger/kwargs/name 갱신
        """
        jid = getattr(self, "_mail_edit_job_id", None)
        if not jid:
            messagebox.showwarning("확인", "업데이트할 메일 작업을 먼저 더블클릭으로 불러오세요.")
            return

        # ✅ 현재 에디터 내용이 blocks에 반영 안됐을 수 있으니 저장 한번
        try:
            if hasattr(self, "_mail_save_block"):
                self._mail_save_block()
        except Exception:
            pass

        res = self._mail_collect_payload(require_schedule=True)
        if not res:
            return
        trigger, payload, mode = res

        # 메일 잡 태그 보장
        payload["job_category"] = "mail"

        # 제목 우선순위
        title = payload.get("mail_subject") or payload.get("job_title") or f"MAIL-{mode}"

        # 기존 상태(일시중지 여부) 보존
        old = scheduler.get_job(jid)
        was_paused = (old is not None and old.next_run_time is None)

        try:
            # ✅ 1) 트리거(스케줄) 갱신
            scheduler.reschedule_job(jid, trigger=trigger)
            # ✅ 2) payload/name 갱신
            scheduler.modify_job(jid, name=title, kwargs={"payload": payload})

            # paused 상태였으면 유지
            if was_paused:
                scheduler.pause_job(jid)

            # 로컬 캐시/트리 갱신
            if not hasattr(self, "mail_jobs"):
                self.mail_jobs = {}
            self.mail_jobs[jid] = payload

            if hasattr(self, "var_mail_edit_hint"):
                self.var_mail_edit_hint.set(f"현재: 편집중({jid})")

            self._update_mail_job_row(jid)
            logger.info(f"[MAIL] 기존 작업 업데이트 완료: {jid} (mode={mode})")

        except JobLookupError:
            # 혹시 job이 사라졌으면 신규로 등록하고 edit id 갱신
            logger.warning(f"[MAIL] 업데이트 대상 작업이 스케줄러에 없음 → 신규 등록으로 대체: {jid}")
            job = scheduler.add_job(job_send_mail, trigger=trigger, kwargs={"payload": payload}, name=title)
            self.mail_jobs[job.id] = payload
            self._mail_edit_job_id = job.id
            if hasattr(self, "var_mail_edit_hint"):
                self.var_mail_edit_hint.set(f"현재: 편집중({job.id})")
            self._update_mail_job_row(job.id)


    def _archive_path(self) -> str:
        base = os.path.dirname(os.path.abspath(LOG_PATH if 'LOG_PATH' in globals() else __file__))
        return os.path.join(base, "mail_jobs_archive.json")

    def _load_mail_archive(self) -> list[dict]:
        try:
            p = self._archive_path()
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as fp:
                    return json.load(fp)
        except Exception as e:
            logger.warning(f"[MAIL][ARCHIVE] 로드 실패: {e}")
        return []

    def _save_mail_archive(self) -> None:
        try:
            p = self._archive_path()
            with open(p, "w", encoding="utf-8") as fp:
                json.dump(self.mail_jobs_archive, fp, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.warning(f"[MAIL][ARCHIVE] 저장 실패: {e}")

    def _archive_mail_job(self, job_id: str, payload: dict, job_name: str = "", next_run: str = "") -> None:
        try:
            snap = {
                "job_id": job_id,
                "job_name": job_name or "",
                "next_run": next_run or "",
                "archived_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                # payload는 JSON 직렬화 가능한 값 위주라 default=str로 안전 저장
                "payload": payload or {},
            }
            self.mail_jobs_archive.append(snap)
            self._save_mail_archive()
            logger.info(f"[MAIL][ARCHIVE] 백업 완료: {job_id}")
        except Exception as e:
            logger.warning(f"[MAIL][ARCHIVE] 백업 실패: {e}")

    def _mail_add_block(self):
        if not hasattr(self, "_mail_blocks"):
            self._mail_blocks = []
        if not hasattr(self, "_mail_selected"):
            self._mail_selected = None

        # ✅ 기본 DB값: 메인 DB 입력이 있으면 그걸 우선 사용, 없으면 MEMSCM 기본
        dsn0  = (self.ent_dsn.get().strip()  if hasattr(self, "ent_dsn")  else "") or "gmgsdd09-vip.sec.samsung.net:2541/MEMSCM"
        user0 = (self.ent_user.get().strip() if hasattr(self, "ent_user") else "") or "memscm"
        pw0   = (self.ent_pw.get().strip()   if hasattr(self, "ent_pw")   else "") or "mem01scm"

        blk = {
            "title": f"블록{len(self._mail_blocks)+1}",
            "sql": "",
            "subject": "[제목] {ymd}",
            "html_tpl": "<h2>{ymd} 결과</h2>{html_table}",
            "py_code": "",
            "dsn": dsn0,
            "user": user0,
            "pw": pw0,
            "skip_if_no_sql": False,
            "auto_attach_sql_excel": False,
            "attachments": [],
        }

        self._mail_blocks.append(blk)
        self.lb_mail_blocks.insert("end", blk["title"])

        new_idx = len(self._mail_blocks) - 1
        self.lb_mail_blocks.selection_clear(0, "end")
        self.lb_mail_blocks.selection_set(new_idx)
        self.lb_mail_blocks.activate(new_idx)
        self.lb_mail_blocks.see(new_idx)
        self._mail_selected = new_idx
        self._mail_load_block(new_idx)



    def _mail_del_block(self):
        idxs = self.lb_mail_blocks.curselection()
        i = idxs[0] if idxs else (self._mail_selected if self._mail_selected is not None else -1)
        if i < 0: return
        self.lb_mail_blocks.delete(i)
        self._mail_blocks.pop(i)
        if self._mail_blocks:
            ni = max(0, i-1)
            self.lb_mail_blocks.selection_clear(0, "end")
            self.lb_mail_blocks.selection_set(ni)
            self.lb_mail_blocks.activate(ni)
            self.lb_mail_blocks.see(ni)
            self._mail_selected = ni
            self._mail_load_block(ni)
        else:
            self._mail_selected = None
            self._mail_clear_editor()


    def _mail_move_block(self, delta: int):
        idxs = self.lb_mail_blocks.curselection()
        if not idxs: return
        i = idxs[0]; j = max(0, min(len(self._mail_blocks)-1, i+delta))
        if i == j: return
        self._mail_blocks[i], self._mail_blocks[j] = self._mail_blocks[j], self._mail_blocks[i]
        titles = [b["title"] for b in self._mail_blocks]
        self.lb_mail_blocks.delete(0, "end")
        for t in titles: self.lb_mail_blocks.insert("end", t)
        self.lb_mail_blocks.selection_set(j)
        self._mail_load_block(j)

    def _mail_on_select(self, _evt=None):
        idxs = self.lb_mail_blocks.curselection()
        if not idxs:
            return
        i = idxs[0]
        self._mail_selected = i                 # 선택 인덱스 기억
        self._mail_load_block(i)


    def _mail_load_block(self, i: int):
        blk = self._mail_blocks[i]
        self.var_blk_title.set(blk.get("title",""))
        self.txt_blk_sql.delete("1.0","end"); self.txt_blk_sql.insert("1.0", blk.get("sql",""))
        self.txt_blk_subject.delete("1.0","end"); self.txt_blk_subject.insert("1.0", blk.get("subject",""))
        self.txt_blk_html.delete("1.0","end"); self.txt_blk_html.insert("1.0", blk.get("html_tpl",""))
        # 바로 위 한 줄
        self.txt_blk_py.delete("1.0","end"); self.txt_blk_py.insert("1.0", blk.get("py_code",""))
        # ↓ 추가
        if hasattr(self, "var_mail_skip_if_no_sql"):
            self.var_mail_skip_if_no_sql.set(bool(blk.get("skip_if_no_sql", False)))
        if hasattr(self, "var_auto_attach_sql_excel"):
            self.var_auto_attach_sql_excel.set(bool(blk.get("auto_attach_sql_excel", False)))        

        # 블록별 DB/옵션 복원
        if hasattr(self, "ent_blk_dsn"):
            self.ent_blk_dsn.delete(0,"end");  self.ent_blk_dsn.insert(0, blk.get("dsn",""))
        if hasattr(self, "ent_blk_user"):
            self.ent_blk_user.delete(0,"end"); self.ent_blk_user.insert(0, blk.get("user",""))
        if hasattr(self, "ent_blk_pw"):
            self.ent_blk_pw.delete(0,"end");   self.ent_blk_pw.insert(0, blk.get("pw",""))
        if hasattr(self, "var_mail_skip_if_no_sql"):
            self.var_mail_skip_if_no_sql.set(bool(blk.get("skip_if_no_sql", False)))
        if hasattr(self, "var_auto_attach_sql_excel"):
            self.var_auto_attach_sql_excel.set(bool(blk.get("auto_attach_sql_excel", False)))



    def _mail_clear_editor(self):
        self.var_blk_title.set("")
        widgets = (
            getattr(self, "txt_blk_sql", None),
            getattr(self, "txt_blk_subject", None),
            getattr(self, "txt_blk_html", None),
            getattr(self, "txt_blk_py", None),
            getattr(self, "ent_blk_dsn", None),
            getattr(self, "ent_blk_user", None),
            getattr(self, "ent_blk_pw", None),
        )
        for w in widgets:
            if not w:
                continue
            # Text(ScrolledText) vs Entry 구분
            if isinstance(w, (tk.Text, scrolledtext.ScrolledText)):
                w.delete("1.0", "end")
            else:
                try:
                    w.delete(0, "end")
                except Exception:
                    # ttk.Entry 등 공통 delete 지원
                    try: w.delete(0, "end")
                    except: pass


    def _mail_save_block(self):
        # 포커스 이동으로 selection이 비어도 마지막 선택을 사용
        if self._mail_selected is None and self.lb_mail_blocks.curselection():
            self._mail_selected = self.lb_mail_blocks.curselection()[0]
        i = self._mail_selected
        if i is None or i < 0 or i >= len(self._mail_blocks):
            logger.warning("[MAIL] 저장 대상 블록이 선택되지 않았습니다.")
            return

        blk = self._mail_blocks[i]
        blk["title"]    = self.var_blk_title.get().strip() or f"블록{i+1}"
        blk["sql"]      = self.txt_blk_sql.get("1.0","end").strip()
        blk["subject"]  = self.txt_blk_subject.get("1.0","end").strip()
        blk["html_tpl"] = self.txt_blk_html.get("1.0","end").strip()
        # 바로 위 한 줄
        blk["py_code"]  = self.txt_blk_py.get("1.0","end").strip()
        blk["dsn"]  = self.ent_blk_dsn.get().strip() if hasattr(self, "ent_blk_dsn") else ""
        blk["user"] = self.ent_blk_user.get().strip() if hasattr(self, "ent_blk_user") else ""
        blk["pw"]   = self.ent_blk_pw.get().strip() if hasattr(self, "ent_blk_pw") else ""
        blk["skip_if_no_sql"] = bool(self.var_mail_skip_if_no_sql.get()) if hasattr(self, "var_mail_skip_if_no_sql") else False
        blk["auto_attach_sql_excel"] = bool(self.var_auto_attach_sql_excel.get()) if hasattr(self, "var_auto_attach_sql_excel") else False
        blk.setdefault("attachments", [])



        # 리스트 갱신 + 선택 유지
        self.lb_mail_blocks.delete(i)
        self.lb_mail_blocks.insert(i, blk["title"])
        self.lb_mail_blocks.selection_clear(0, "end")
        self.lb_mail_blocks.selection_set(i)
        self.lb_mail_blocks.activate(i)
        self.lb_mail_blocks.see(i)
        # ↓ 추가: 블록별 DB/옵션/첨부 필드 반영
        blk["dsn"] = getattr(self, "ent_blk_dsn", None).get().strip() if hasattr(self, "ent_blk_dsn") else ""
        blk["user"] = getattr(self, "ent_blk_user", None).get().strip() if hasattr(self, "ent_blk_user") else ""
        blk["pw"] = getattr(self, "ent_blk_pw", None).get().strip() if hasattr(self, "ent_blk_pw") else ""
        blk["skip_if_no_sql"] = bool(self.var_mail_skip_if_no_sql.get()) if hasattr(self, "var_mail_skip_if_no_sql") else False
        blk["auto_attach_sql_excel"] = bool(self.var_auto_attach_sql_excel.get()) if hasattr(self, "var_auto_attach_sql_excel") else False
        blk.setdefault("attachments", [])


    # [추가] 메일 미리보기/전송/스케줄
    def _mail_collect_payload(self, require_schedule: bool = False):
        gvars = self._build_global_vars()
        sender_id = self.ent_mail_sender.get().strip()
        receivers_csv = self.ent_mail_receivers.get().strip()
        df_receiver_col = self.ent_mail_recv_col.get().strip() or None

        # ★★★ 바로 아래 2줄 추가: CC/BCC 읽기
        receivers_cc_csv  = (self.ent_mail_receivers_cc.get().strip()  if hasattr(self, "ent_mail_receivers_cc")  else "")
        receivers_bcc_csv = (self.ent_mail_receivers_bcc.get().strip() if hasattr(self, "ent_mail_receivers_bcc") else "")


        # 공통 DB/SQL (메신저 탭과 공유 인풋 사용)
        dsn = self.ent_dsn.get().strip(); user = self.ent_user.get().strip(); pw = self.ent_pw.get().strip()

        blocks = list(self._mail_blocks)  # shallow copy

        payload = {
            "sender_id": sender_id,
            "receivers_csv": receivers_csv,
            "df_receiver_col": df_receiver_col,

            # ★★★ CC/BCC 추가
            "receivers_cc_csv":  receivers_cc_csv,
            "receivers_bcc_csv": receivers_bcc_csv,

            "sql_blocks": blocks,
            "globals": gvars,
            "dsn": dsn, "user": user, "pw": pw,
            "verify_ssl": CONFIG["VERIFY_SSL"],
            "proxies": CONFIG["PROXIES"],
            "dryrun": (bool(self.var_mail_dryrun.get()) if hasattr(self, "var_mail_dryrun") else False),
            "mail_no_send": (self.var_mail_no_send.get() if hasattr(self, "var_mail_no_send") else False),
            "skip_if_no_sql": (bool(self.var_mail_skip_if_no_sql.get()) if hasattr(self, "var_mail_skip_if_no_sql") else False),
            "mail_subject": (getattr(self, "ent_mail_subject", None).get().strip() if hasattr(self, "ent_mail_subject") else None),
                        # ✅ 재전송 금지 옵션 → docSecuType 결정
            "doc_secu_type": ("PROHIBIT_FORWARD"
                             if (hasattr(self, "var_mail_prohibit_forward") and self.var_mail_prohibit_forward.get())
                             else "PERSONAL"),

        }


        if not require_schedule:
            return None, payload, "now"

        # 메일 탭 전용 스케줄 위젯을 직접 읽어서 트리거 생성
        sch = getattr(self, "var_mail_sch_mode", None)
        sch_mode = sch.get() if sch else "once"
        try:
            if sch_mode == "once":
                dt = self.ent_mail_once_dt.get().strip()
                if not dt:
                    raise ValueError("한 번 전송 시각(YYYY-MM-DD HH:MM)을 입력")
                trigger = DateTrigger(run_date=datetime.strptime(dt, "%Y-%m-%d %H:%M"))

            elif sch_mode == "daily":
                hh, mm = [int(x) for x in self.ent_mail_daily_time.get().strip().split(":")]
                trigger = CronTrigger(hour=hh, minute=mm)

            elif sch_mode == "weekly":
                hh, mm = [int(x) for x in self.ent_mail_weekly_time.get().strip().split(":")]
                dow_map = {"월":"mon","화":"tue","수":"wed","목":"thu","금":"fri","토":"sat","일":"sun"}
                dow = dow_map.get(self.cmb_mail_weekday.get().strip() or "월", "mon")
                trigger = CronTrigger(day_of_week=dow, hour=hh, minute=mm)

            elif sch_mode == "monthly":
                hh, mm = [int(x) for x in self.ent_mail_monthly_time.get().strip().split(":")]
                dom = self._safe_int(self.spin_mail_dom.get(), 1)
                if not (1 <= dom <= 31):
                    raise ValueError("매월 일자(1~31)를 확인")
                trigger = CronTrigger(day=dom, hour=hh, minute=mm)

            else:  # interval
                hours = self._safe_int(self.ent_mail_iv_h.get(), 0)
                minutes = self._safe_int(self.ent_mail_iv_m.get(), 0)
                if hours == 0 and minutes == 0:
                    raise ValueError("간격(분/시간) 중 하나 이상 입력")
                trigger = IntervalTrigger(hours=hours, minutes=minutes)
        except Exception as e:
            messagebox.showerror("스케줄 오류", str(e))
            return None

        return trigger, payload, sch_mode


    def _on_mail_sched_mode_changed(self):
        for frm in (getattr(self, "frame_mail_once", None),
                    getattr(self, "frame_mail_daily", None),
                    getattr(self, "frame_mail_weekly", None),
                    getattr(self, "frame_mail_monthly", None),
                    getattr(self, "frame_mail_interval", None)):
            if frm and frm.winfo_manager():
                frm.grid_forget()
        mode = getattr(self, "var_mail_sch_mode", tk.StringVar(value="once")).get()
        target = {
            "once": self.frame_mail_once,
            "daily": self.frame_mail_daily,
            "weekly": self.frame_mail_weekly,
            "monthly": self.frame_mail_monthly,
            "interval": self.frame_mail_interval,
        }.get(mode)
        if target:
            target.grid(row=2, column=0, columnspan=6, sticky="w", padx=4, pady=(0,6))

    def _preset_mail_now_plus_5(self):
        self.var_mail_sch_mode.set("once"); self._on_mail_sched_mode_changed()
        dt = (datetime.now() + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")
        try:
            self.ent_mail_once_dt.delete(0, "end"); self.ent_mail_once_dt.insert(0, dt)
        except: pass

    def _preset_mail_time(self, hhmm: str):
        m = self.var_mail_sch_mode.get()
        if m == "once":
            today = datetime.now().strftime("%Y-%m-%d")
            self.ent_mail_once_dt.delete(0,"end"); self.ent_mail_once_dt.insert(0, f"{today} {hhmm}")
        elif m == "daily":
            self.ent_mail_daily_time.delete(0,"end"); self.ent_mail_daily_time.insert(0, hhmm)
        elif m == "weekly":
            self.ent_mail_weekly_time.delete(0,"end"); self.ent_mail_weekly_time.insert(0, hhmm)
        elif m == "monthly":
            self.ent_mail_monthly_time.delete(0,"end"); self.ent_mail_monthly_time.insert(0, hhmm)


    def on_mail_preview(self):
        # 첫 블록만 간단 실행해서 로그로 확인
        _, payload, _ = self._mail_collect_payload(require_schedule=False)
        if not payload: return
        try:
            test = dict(payload); test["dryrun"] = True
            job_send_mail(test)
            logger.info("[MAIL] 미리보기 완료")
        except Exception as e:
            logger.exception(f"[MAIL] 미리보기 실패: {e}")

    def on_mail_send_now(self):
        _, payload, _ = self._mail_collect_payload(require_schedule=False)
        if not payload: return
        try:
            logger.info("[MAIL] 바로전송 시작")
            job_send_mail(payload)
            logger.info("[MAIL] 바로전송 완료")
        except Exception as e:
            logger.exception(f"[MAIL] 바로전송 실패: {e}")

    def on_mail_add_job(self):
        res = self._mail_collect_payload(require_schedule=True)
        if not res:
            return
        trigger, payload, mode = res

        # 메일 전용 태그 + 제목 우선
        payload["job_category"] = "mail"
        title = payload.get("mail_subject") or payload.get("job_title") or f"MAIL-{mode}"

        edit_id = getattr(self, "_mail_editing_job_id", None)
        old_job = scheduler.get_job(edit_id) if edit_id else None

        # =========================
        # ✅ UPDATE(동일 id 유지)
        # =========================
        if edit_id and old_job:
            was_paused = (old_job.next_run_time is None)

            # ✅ remove_job까지 할 필요 없음. replace_existing=True로 덮어쓰기면 끝.
            new_job = scheduler.add_job(
                job_send_mail,
                trigger=trigger,
                kwargs={"payload": payload},
                name=title,
                id=edit_id,
                replace_existing=True,
            )

            if was_paused:
                try:
                    scheduler.pause_job(edit_id)
                except Exception:
                    pass

            if not hasattr(self, "mail_jobs"):
                self.mail_jobs = {}
            self.mail_jobs[edit_id] = payload

            if hasattr(self, "_update_mail_job_row"):
                self._update_mail_job_row(edit_id)

            self._mail_editing_job_id = None
            logger.info(f"[MAIL] 작업 업데이트(동일 id 유지): {edit_id}")
            return

        # edit_id가 남아있는데 old_job이 없으면(이미 삭제/재시작 등) 편집모드 해제
        if edit_id and not old_job:
            self._mail_editing_job_id = None

        # =========================
        # ✅ NEW(신규 등록)
        # =========================
        job = scheduler.add_job(
            job_send_mail,
            trigger=trigger,
            kwargs={"payload": payload},
            name=title
        )

        if not hasattr(self, "mail_jobs"):
            self.mail_jobs = {}
        self.mail_jobs[job.id] = payload

        if hasattr(self, "_update_mail_job_row"):
            self._update_mail_job_row(job.id)

        self._mail_editing_job_id = None
        logger.info(f"[MAIL] 스케줄 등록: {job.id}")




    # 변경 코드 (헬퍼 메서드 추가) · App 클래스 내부 아무 곳에 추가
    def _on_sched_mode_changed(self) -> None:
        """라디오 선택에 따라 모드별 섹션 표시/비표시."""
        mode = self.var_sch_mode.get()
        # 모두 숨기고 선택 모드만 보이기
        for frm in (getattr(self, "frame_once", None),
                    getattr(self, "frame_daily", None),
                    getattr(self, "frame_weekly", None),
                    getattr(self, "frame_monthly", None),
                    getattr(self, "frame_interval", None)):
            if frm and frm.winfo_manager():
                frm.grid_forget()

        if mode == "once" and self.frame_once:
            self.frame_once.grid(row=2, column=0, columnspan=6, sticky="w", padx=4, pady=(0, 6))
        elif mode == "daily" and self.frame_daily:
            self.frame_daily.grid(row=2, column=0, columnspan=6, sticky="w", padx=4, pady=(0, 6))
        elif mode == "weekly" and self.frame_weekly:
            self.frame_weekly.grid(row=2, column=0, columnspan=6, sticky="w", padx=4, pady=(0, 6))
        elif mode == "monthly" and self.frame_monthly:
            self.frame_monthly.grid(row=2, column=0, columnspan=6, sticky="w", padx=4, pady=(0, 6))
        elif mode == "interval" and self.frame_interval:
            self.frame_interval.grid(row=2, column=0, columnspan=6, sticky="w", padx=4, pady=(0, 6))

    def _preset_now_plus_5(self) -> None:
        """현재 시각 + 5분을 '한 번' 입력칸에 세팅."""
        self.var_sch_mode.set("once")
        self._on_sched_mode_changed()
        dt = (datetime.now() + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")
        try:
            self.ent_once_dt.delete(0, "end"); self.ent_once_dt.insert(0, dt)
        except Exception:
            pass

    def _preset_time(self, hhmm: str) -> None:
        """HH:MM 프리셋을 현재 모드의 시각 필드에 세팅."""
        mode = self.var_sch_mode.get()
        if mode == "once":
            # 오늘 날짜 + 프리셋 시간
            today = datetime.now().strftime("%Y-%m-%d")
            try:
                self.ent_once_dt.delete(0, "end")
                self.ent_once_dt.insert(0, f"{today} {hhmm}")
            except Exception:
                pass
        elif mode == "daily":
            self.ent_daily_time.delete(0, "end"); self.ent_daily_time.insert(0, hhmm)
        elif mode == "weekly":
            self.ent_weekly_time.delete(0, "end"); self.ent_weekly_time.insert(0, hhmm)
        elif mode == "monthly":
            self.ent_monthly_time.delete(0, "end"); self.ent_monthly_time.insert(0, hhmm)


    # 추가: App 클래스 내부 헬퍼 (필드 초기화)
    def _clear_sched_fields(self) -> None:
        # 존재 체크 후 안전 초기화
        for w in [
            getattr(self, "ent_once_dt", None),
            getattr(self, "ent_daily_time", None),
            getattr(self, "ent_weekly_time", None),
            getattr(self, "ent_monthly_time", None),
            getattr(self, "ent_iv_h", None),
            getattr(self, "ent_iv_m", None),
        ]:
            if w:
                try:
                    w.delete(0, "end")
                except:
                    pass
        if hasattr(self, "cmb_weekday"): self.cmb_weekday.set("월")
        if hasattr(self, "spin_dom"):
            try:
                self.spin_dom.delete(0, "end"); self.spin_dom.insert(0, "1")
            except:
                pass

    def _clear_mail_sched_fields(self) -> None:
        # 메일 탭 전용 스케줄 입력칸 안전 초기화
        for w in [
            getattr(self, "ent_mail_once_dt", None),
            getattr(self, "ent_mail_daily_time", None),
            getattr(self, "ent_mail_weekly_time", None),
            getattr(self, "ent_mail_monthly_time", None),
            getattr(self, "ent_mail_iv_h", None),
            getattr(self, "ent_mail_iv_m", None),
        ]:
            if w:
                try: w.delete(0, "end")
                except: pass
        if hasattr(self, "cmb_mail_weekday"):
            try: self.cmb_mail_weekday.set("월")
            except: pass
        if hasattr(self, "spin_mail_dom"):
            try:
                self.spin_mail_dom.delete(0, "end")
                self.spin_mail_dom.insert(0, "1")
            except: pass


    # ---------------- 공용 유틸 (App 메서드) ----------------
    def _build_global_vars(self) -> dict:
        tz = ZoneInfo("Asia/Seoul")
        now = datetime.now(tz)
        today = now.date()
        yday = today - timedelta(days=1)
        first_day_of_month = today.replace(day=1)
        last_day_of_prev_month = first_day_of_month - timedelta(days=1)
        return {
            "now": now.strftime("%Y-%m-%d %H:%M:%S"),
            "today": today.strftime("%Y-%m-%d"),
            "yesterday": yday.strftime("%Y-%m-%d"),
            "ymd": today.strftime("%Y%m%d"),
            "md": today.strftime("%m/%d"),
            "ym": today.strftime("%Y%m"),
            "mm": today.strftime("%m"),
            "first_day_of_month": first_day_of_month.strftime("%Y-%m-%d"),
            "last_day_of_prev_month": last_day_of_prev_month.strftime("%Y-%m-%d"),
        }

    def _safe_int(self, val, default):
        try:
            return int(str(val).strip())
        except:
            return default

    def _resolve_color(self, val: str, default_hex: str) -> str:
        if not val:
            return default_hex
        v = val.strip()
        # HEX 직접 입력/피커 선택
        if v.startswith("#") and (len(v) in (4, 7)):
            return v
        # 이름 매핑(텍스트/헤더 합산)
        all_map = {}
        all_map.update(getattr(self, "text_color_map", {}))
        all_map.update(getattr(self, "header_color_map", {}))
        return all_map.get(v, default_hex)

    def _trigger_mode(self, job):
        # 1) job.name에 우리가 넣은 모드/제목이 있으면 우선 사용
        if getattr(job, "name", None) in {"once", "daily", "weekly", "monthly", "interval"}:
            return job.name
        # 2) 트리거로 유추
        t = job.trigger
        if isinstance(t, DateTrigger):
            return "once"
        elif isinstance(t, IntervalTrigger):
            return "interval"
        elif isinstance(t, CronTrigger):
            try:
                fields = {f.name: f for f in t.fields}
                day = fields.get("day")
                dow = fields.get("day_of_week")

                def _is_all(field):
                    return str(field).strip() == "*"

                if dow and not _is_all(dow):
                    return "weekly"
                if day and not _is_all(day):
                    return "monthly"
                return "daily"
            except:
                return "daily"
        return t.__class__.__name__.lower()

    # ---------------- 상단 탭/스크롤 프레임 ----------------
    def _build_ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        # 메인 탭: 스크롤 가능한 래퍼
        self.tab_main = ttk.Frame(nb)
        nb.add(self.tab_main, text="스케줄 설정")

        main_canvas = tk.Canvas(self.tab_main, highlightthickness=0)
        main_vsb = ttk.Scrollbar(self.tab_main, orient="vertical", command=main_canvas.yview)
        main_canvas.configure(yscrollcommand=main_vsb.set)

        main_vsb.pack(side="right", fill="y")
        main_canvas.pack(side="left", fill="both", expand=True)

        self.main_wrap = ttk.Frame(main_canvas)
        main_canvas.create_window((0, 0), window=self.main_wrap, anchor="nw")

        def _on_configure(event):
            # 내부 프레임 크기에 맞춰 캔버스 스크롤영역 갱신
            main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        self.main_wrap.bind("<Configure>", _on_configure)

        # 내용 빌드
        self._build_main(self.main_wrap)

        # 로그 탭
        self.tab_log = ttk.Frame(nb)
        nb.add(self.tab_log, text="로그")
        self._build_log(self.tab_log)

        # [추가] 메일 스케줄 탭 생성
        self.tab_mail = ttk.Frame(nb)
        nb.add(self.tab_mail, text="메일 스케줄")
        self._build_mail(self.tab_mail)


    # ---------------- 메인 구성 ----------------
    def _build_main(self, parent):
        pad = {"padx": 8, "pady": 6}

        # Knox/실행
        f_knox = ttk.LabelFrame(parent, text="Knox/실행 설정"); f_knox.pack(fill="x", **pad)
        self.var_dryrun = tk.BooleanVar(value=False)
        ttk.Checkbutton(f_knox, text="DRY-RUN(실전 전송 안 함)", variable=self.var_dryrun)\
            .grid(row=0, column=0, sticky="w", **pad)
        ttk.Button(f_knox, text="장비등록 & 키받기", command=self.on_device_and_keys)\
            .grid(row=0, column=3, sticky="e", **pad)

        # DB/SQL
        f_db = ttk.LabelFrame(parent, text="DB / SQL"); f_db.pack(fill="x", **pad)
        ttk.Label(f_db, text="DSN").grid(row=0, column=0, sticky="e")
        ttk.Label(f_db, text="User").grid(row=0, column=2, sticky="e")
        ttk.Label(f_db, text="Password").grid(row=0, column=4, sticky="e")
        self.ent_dsn = ttk.Entry(f_db, width=36)
        self.ent_user = ttk.Entry(f_db, width=18)
        self.ent_pw = ttk.Entry(f_db, width=18, show="*")
        self.ent_dsn.grid(row=0, column=1, **pad)
        self.ent_user.grid(row=0, column=3, **pad)
        self.ent_pw.grid(row=0, column=5, **pad)

        # 기본값
        self.ent_dsn.insert(0, "gmgsdd09-vip.sec.samsung.net:2541/MEMSCM")
        self.ent_user.insert(0, "memscm")
        self.ent_pw.insert(0, "mem01scm")

        ttk.Label(f_db, text="SQL").grid(row=1, column=0, sticky="ne", **pad)
        self.txt_sql = scrolledtext.ScrolledText(f_db, height=6)
        self.txt_sql.grid(row=1, column=1, columnspan=5, sticky="we", **pad)
        ttk.Button(f_db, text="미리보기", command=self.on_preview).grid(row=2, column=5, sticky="e", **pad)

        # 전송 옵션
        f_send = ttk.LabelFrame(parent, text="전송 옵션"); f_send.pack(fill="x", **pad)
        self.var_send_general  = tk.BooleanVar(value=False)
        self.var_send_template = tk.BooleanVar(value=True)
        self.var_send_table    = tk.BooleanVar(value=False)

        ttk.Checkbutton(f_send, text="일반 메시지",   variable=self.var_send_general).grid(row=0, column=0, sticky="w", **pad)
        ttk.Checkbutton(f_send, text="템플릿 메시지", variable=self.var_send_template).grid(row=0, column=1, sticky="w", **pad)
        ttk.Checkbutton(f_send, text="표(HTML) 전송", variable=self.var_send_table).grid(row=0, column=2, sticky="w", **pad)

        # 표 제목에 일반메시지 사용
        self.var_table_title_from_general = tk.BooleanVar(value=False)
        ttk.Checkbutton(f_send, text="표 제목에 일반 메시지 사용", variable=self.var_table_title_from_general)\
            .grid(row=0, column=3, sticky="w", **pad)

        # Adaptive Card 옵션
        self.var_send_card = tk.BooleanVar(value=False)
        ttk.Checkbutton(f_send, text="Adaptive Card 전송", variable=self.var_send_card)\
           .grid(row=0, column=4, sticky="w", **pad)

        # 수신자/방/그룹
        ttk.Label(f_send, text="수신자(SSO, 쉼표구분)").grid(row=1, column=0, sticky="e")
        self.ent_receivers = ttk.Entry(f_send, width=60)
        self.ent_receivers.grid(row=1, column=1, columnspan=3, sticky="we", **pad)
        self.ent_receivers.insert(0, "sungmook.cho")

        ttk.Label(f_send, text="수신자 컬럼명(선택)").grid(row=2, column=0, sticky="e")
        self.ent_recv_col = ttk.Entry(f_send, width=20)
        self.ent_recv_col.grid(row=2, column=1, sticky="w", **pad)

        self.var_group_send = tk.BooleanVar(value=True)
        ttk.Checkbutton(f_send, text="그룹방으로 한번에 전송(해제 시 1:1)", variable=self.var_group_send)\
            .grid(row=2, column=2, sticky="w", **pad)

        ttk.Label(f_send, text="기존 Chatroom ID(선택)").grid(row=2, column=3, sticky="e")
        self.ent_chatroom = ttk.Entry(f_send, width=24)
        self.ent_chatroom.grid(row=2, column=4, sticky="w", **pad)

        # 작업 제목
        ttk.Label(f_send, text="작업 제목(선택)").grid(row=1, column=4, sticky="e")
        self.ent_job_title = ttk.Entry(f_send, width=24)
        self.ent_job_title.grid(row=1, column=5, sticky="w", **pad)

        ttk.Label(f_send, text="대화방 이름(선택)").grid(row=2, column=5, sticky="e")
        self.ent_chatroom_title = ttk.Entry(f_send, width=24)
        self.ent_chatroom_title.grid(row=2, column=6, sticky="w", **pad)


        # 메시지 입력
        ttk.Label(f_send, text="일반 메시지").grid(row=3, column=0, sticky="ne")
        self.txt_general = scrolledtext.ScrolledText(f_send, height=3)
        self.txt_general.grid(row=3, column=1, columnspan=5, sticky="we", **pad)
        self.txt_general.insert("1.0", "안녕하세요")

        ttk.Label(f_send, text="템플릿 메시지").grid(row=4, column=0, sticky="ne")
        self.txt_tpl = scrolledtext.ScrolledText(f_send, height=4)
        self.txt_tpl.grid(row=4, column=1, columnspan=5, sticky="we", **pad)
        self.txt_tpl.insert("1.0", "[자동알림]\n{FAM1} {ITEM} : {QTY}")

        # Adaptive Card JSON
        ttk.Label(f_send, text="Adaptive Card JSON").grid(row=5, column=0, sticky="ne", **pad)
        self.txt_card_json = scrolledtext.ScrolledText(f_send, height=6)
        self.txt_card_json.grid(row=5, column=1, columnspan=5, sticky="we", **pad)
        _default_card = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.3",
            "body": [
                {"type": "TextBlock", "text": "알림", "weight": "Bolder", "size": "Medium"},
                {"type": "TextBlock", "text": "오늘: {today} / 전일: {yesterday}", "wrap": True}
            ]
        }
        self.txt_card_json.insert("1.0", json.dumps(_default_card, ensure_ascii=False, indent=2))

        # 표 스타일 옵션
        ttk.Label(f_send, text="표 너비(px)").grid(row=6, column=0, sticky="e", **pad)
        self.spin_tbl_width = tk.Spinbox(f_send, from_=400, to=2000, increment=50, width=8)
        self.spin_tbl_width.delete(0, "end"); self.spin_tbl_width.insert(0, "1000")
        self.spin_tbl_width.grid(row=6, column=1, sticky="w", **pad)

        ttk.Label(f_send, text="폰트 크기(px)").grid(row=6, column=2, sticky="e", **pad)
        self.spin_font_px = tk.Spinbox(f_send, from_=8, to=24, increment=1, width=6)
        self.spin_font_px.delete(0, "end"); self.spin_font_px.insert(0, "13")
        self.spin_font_px.grid(row=6, column=3, sticky="w", **pad)

        # 헤더 색상(이름→HEX)
        self.header_color_map = {
            "파랑": "#BBE9F0",
            "노랑": "#FDE68A",
            "민트": "#DCFCE7",
            "회색": "#E5E7EB",
            "연파랑": "#BFDBFE",
            "핑크": "#FBCFE8",
        }
        ttk.Label(f_send, text="헤더 색상").grid(row=6, column=4, sticky="e", **pad)
        self.cmb_header_bg = ttk.Combobox(f_send, values=list(self.header_color_map.keys()), state="readonly", width=10)
        self.cmb_header_bg.set("파랑")
        self.cmb_header_bg.grid(row=6, column=5, sticky="w", **pad)

        # 글씨체
        ttk.Label(f_send, text="글씨체").grid(row=7, column=0, sticky="e", **pad)
        self.cmb_font_family = ttk.Combobox(
            f_send, width=18,
            values=["Malgun Gothic", "Arial", "Calibri", "Times New Roman",
                    "Courier New", "맑은 고딕", "굴림", "돋움", "궁서"],
            state="readonly"
        )
        self.cmb_font_family.set("Arial")
        self.cmb_font_family.grid(row=7, column=1, sticky="w", **pad)

        # 텍스트/제목 색상 이름 → HEX 맵
        self.text_color_map = {
            "검정": "#000000", "회색": "#6B7280", "빨강": "#EF4444", "주황": "#F97316",
            "노랑": "#FDE68A", "초록": "#10B981", "민트": "#DCFCE7", "파랑": "#3B82F6",
            "연파랑": "#BFDBFE", "남색": "#1F2A68", "보라": "#8B5CF6", "핑크": "#FBCFE8",
        }

        # 표 글자색
        ttk.Label(f_send, text="표 글자색").grid(row=8, column=0, sticky="e", **pad)
        self.cmb_font_color = ttk.Combobox(f_send, width=10, values=list(self.text_color_map.keys()), state="readonly")
        self.cmb_font_color.set("검정")
        self.cmb_font_color.grid(row=8, column=1, sticky="w", **pad)
        ttk.Button(f_send, text="선택…", command=self.on_pick_font_color)\
            .grid(row=8, column=2, sticky="w", **pad)

        # 제목 글자색
        ttk.Label(f_send, text="제목 글자색").grid(row=8, column=3, sticky="e", **pad)
        self.cmb_title_color = ttk.Combobox(f_send, width=10, values=list(self.text_color_map.keys()), state="readonly")
        self.cmb_title_color.set("검정")
        self.cmb_title_color.grid(row=8, column=4, sticky="w", **pad)
        ttk.Button(f_send, text="선택…", command=self.on_pick_title_color)\
            .grid(row=8, column=5, sticky="w", **pad)

        # ---------------- 스케줄 ----------------
        f_sch = ttk.LabelFrame(parent, text="스케줄"); f_sch.pack(fill="x", **pad)

        # (A) 모드 선택 라디오 + 빠른 프리셋
        top_bar = ttk.Frame(f_sch); top_bar.grid(row=0, column=0, columnspan=6, sticky="we", padx=4, pady=(6, 0))
        self.var_sch_mode = tk.StringVar(value="once")
        modes = [("한 번", "once"), ("매일", "daily"), ("매주", "weekly"), ("매월", "monthly"), ("간격", "interval")]
        for i, (label, val) in enumerate(modes):
            ttk.Radiobutton(top_bar, text=label, value=val, variable=self.var_sch_mode,
                            command=self._on_sched_mode_changed).grid(row=0, column=i, sticky="w", padx=(0, 8))

        # 프리셋: 지금+5분 / 09:00 / 18:00
        preset = ttk.Frame(f_sch); preset.grid(row=1, column=0, columnspan=6, sticky="w", padx=4, pady=(2, 6))
        ttk.Button(preset, text="지금+5분", width=10, command=self._preset_now_plus_5).grid(row=0, column=0, padx=4)
        ttk.Button(preset, text="09:00", width=8, command=lambda: self._preset_time("09:00")).grid(row=0, column=1, padx=4)
        ttk.Button(preset, text="18:00", width=8, command=lambda: self._preset_time("18:00")).grid(row=0, column=2, padx=4)

        # (B) 모드별 섹션(필요한 입력만 보이게)
        # 1) 한 번
        self.frame_once = ttk.Frame(f_sch)
        ttk.Label(self.frame_once, text="날짜시각 (YYYY-MM-DD HH:MM)").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self.ent_once_dt = ttk.Entry(self.frame_once, width=20); self.ent_once_dt.grid(row=0, column=1, sticky="w", padx=4, pady=4)

        # 2) 매일
        self.frame_daily = ttk.Frame(f_sch)
        ttk.Label(self.frame_daily, text="시각 (HH:MM)").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self.ent_daily_time = ttk.Entry(self.frame_daily, width=10); self.ent_daily_time.grid(row=0, column=1, sticky="w", padx=4, pady=4)

        # 3) 매주
        self.frame_weekly = ttk.Frame(f_sch)
        ttk.Label(self.frame_weekly, text="요일").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self.cmb_weekday = ttk.Combobox(self.frame_weekly, width=8, values=["월","화","수","목","금","토","일"], state="readonly")
        self.cmb_weekday.set("월"); self.cmb_weekday.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(self.frame_weekly, text="시각 (HH:MM)").grid(row=0, column=2, sticky="e", padx=4, pady=4)
        self.ent_weekly_time = ttk.Entry(self.frame_weekly, width=10); self.ent_weekly_time.grid(row=0, column=3, sticky="w", padx=4, pady=4)

        # 4) 매월
        self.frame_monthly = ttk.Frame(f_sch)
        ttk.Label(self.frame_monthly, text="일자(1~31)").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self.spin_dom = tk.Spinbox(self.frame_monthly, from_=1, to=31, width=6)
        self.spin_dom.delete(0, "end"); self.spin_dom.insert(0, "1"); self.spin_dom.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(self.frame_monthly, text="시각 (HH:MM)").grid(row=0, column=2, sticky="e", padx=4, pady=4)
        self.ent_monthly_time = ttk.Entry(self.frame_monthly, width=10); self.ent_monthly_time.grid(row=0, column=3, sticky="w", padx=4, pady=4)

        # 5) 간격
        self.frame_interval = ttk.Frame(f_sch)
        ttk.Label(self.frame_interval, text="간격(시간)").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self.ent_iv_h = ttk.Entry(self.frame_interval, width=6); self.ent_iv_h.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(self.frame_interval, text="간격(분)").grid(row=0, column=2, sticky="e", padx=4, pady=4)
        self.ent_iv_m = ttk.Entry(self.frame_interval, width=6); self.ent_iv_m.grid(row=0, column=3, sticky="w", padx=4, pady=4)

        # 초기 표시
        self._on_sched_mode_changed()


        # ---------------- 작업 리스트 + 툴바 ----------------
        f_job = ttk.LabelFrame(parent, text="작업"); f_job.pack(fill="both", expand=True, **pad)

        # 상단 툴바
        toolbar = ttk.Frame(f_job)
        toolbar.pack(fill="x", padx=8, pady=(8, 0))
        ttk.Button(toolbar, text="선택작업 중지", command=self.on_pause_job).pack(side="left", padx=4)
        ttk.Button(toolbar, text="선택작업 재개", command=self.on_resume_job).pack(side="left", padx=4)
        ttk.Button(toolbar, text="선택작업 삭제", command=self.on_remove_job).pack(side="left", padx=4)
        right_box = ttk.Frame(toolbar); right_box.pack(side="right")
        ttk.Button(right_box, text="스케줄 등록", command=self.on_add_job).pack(side="left", padx=4)
        ttk.Button(right_box, text="바로전송",     command=self.on_send_now).pack(side="left", padx=4)

        # 트리 + 스크롤
        tree_wrap = ttk.Frame(f_job)
        tree_wrap.pack(fill="both", expand=True, padx=8, pady=6)
        tree_wrap.rowconfigure(0, weight=1)
        tree_wrap.columnconfigure(0, weight=1)

        self.style = ttk.Style(self)
        self.style.configure("Custom.Treeview", rowheight=22)

        base = tkfont.nametofont("TkDefaultFont")
        self.font_normal = base.copy()
        self.font_paused = base.copy()
        self.font_paused.configure(overstrike=1)

        self.tree = ttk.Treeview(
            tree_wrap,
            columns=( "desc", "mode","id"),
            show="headings",
            style="Custom.Treeview"
        )
        self.tree.heading("desc", text="설명")
        self.tree.heading("mode", text="유형/제목")
        self.tree.heading("id",   text="Job ID")
        
        

        vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.tree.tag_configure("paused",    foreground="gray",  font=self.font_paused)
        self.tree.tag_configure("scheduled", foreground="black", font=self.font_normal)

        # 더블클릭 → 상단 폼 로드
        self.tree.bind("<Double-1>", self._on_tree_dblclick)
        
    # [추가] 메일 탭 UI
    def _build_mail(self, parent):
        pad = {"padx": 8, "pady": 6}
        # [안전 가드] __init__에서 못 거쳤을 경우 대비
        if not hasattr(self, "_mail_blocks"):
            self._mail_blocks = []
        if not hasattr(self, "_mail_selected"):
            self._mail_selected = None        
        # ↓ 교체: 블록 기본값에 dsn/user/pw 추가
        blk = {
            "title": f"블록{len(self._mail_blocks)+1}",
            "sql": "",
            "subject": "[제목] {ymd}",
            "html_tpl": "<h2>{ymd} 결과</h2>{html_table}",
            "py_code": "",
            "dsn": "gmgsdd09-vip.sec.samsung.net:2541/MEMSCM",
            "user": "memscm",
            "pw": "mem01scm",
        }


        # === (A) 메일 탭 스크롤 래퍼 생성 ===
        mail_canvas = tk.Canvas(parent, highlightthickness=0)
        mail_vsb = ttk.Scrollbar(parent, orient="vertical", command=mail_canvas.yview)
        mail_canvas.configure(yscrollcommand=mail_vsb.set)

        mail_vsb.pack(side="right", fill="y")
        mail_canvas.pack(side="left", fill="both", expand=True)

        self.mail_wrap = ttk.Frame(mail_canvas)
        mail_canvas.create_window((0, 0), window=self.mail_wrap, anchor="nw")

        def _mail_on_configure(_evt):
            # 내부 내용 크기에 맞춰 스크롤 영역 갱신
            mail_canvas.configure(scrollregion=mail_canvas.bbox("all"))
        self.mail_wrap.bind("<Configure>", _mail_on_configure)

        # (선택) 마우스 휠로 스크롤
        def _on_mousewheel_winmac(evt):
            step = int(-evt.delta / 120)  # 방향 보정
            mail_canvas.yview_scroll(step, "units")

        def _on_mousewheel_linux(evt):
            step = -1 if evt.num == 4 else 1
            mail_canvas.yview_scroll(step, "units")

        def _bind_wheel(_evt=None):
            mail_canvas.bind_all("<MouseWheel>", _on_mousewheel_winmac)
            mail_canvas.bind_all("<Button-4>", _on_mousewheel_linux)
            mail_canvas.bind_all("<Button-5>", _on_mousewheel_linux)

        def _unbind_wheel(_evt=None):
            mail_canvas.unbind_all("<MouseWheel>")
            mail_canvas.unbind_all("<Button-4>")
            mail_canvas.unbind_all("<Button-5>")

        mail_canvas.bind("<Enter>", _bind_wheel)
        mail_canvas.bind("<Leave>", _unbind_wheel)


        # === (B) 상단: 송신/수신 공통 ===
        f_top = ttk.LabelFrame(self.mail_wrap, text="메일 기본"); f_top.pack(fill="x", **pad)

        # ★ 바로 위 줄
        # 열 확장 설정: 오른쪽 입력부가 자연스럽게 늘어나도록
        for i in range(0, 6):
            f_top.columnconfigure(i, weight=1)

        ttk.Label(f_top, text="보내는ID(knoxid)").grid(row=0, column=0, sticky="e")
        self.ent_mail_sender = ttk.Entry(f_top, width=24)
        self.ent_mail_sender.grid(row=0, column=1, sticky="we", **pad)
        self.ent_mail_sender.insert(0, "sungmook.cho")

        ttk.Label(f_top, text="수신자 이메일(쉼표)").grid(row=0, column=2, sticky="e")
        self.ent_mail_receivers = ttk.Entry(f_top, width=48)
        self.ent_mail_receivers.grid(row=0, column=3, columnspan=2, sticky="we", **pad)

        # 수신자 컬럼 (왼쪽)
        ttk.Label(f_top, text="수신자 컬럼명(선택)").grid(row=1, column=0, sticky="e")
        self.ent_mail_recv_col = ttk.Entry(f_top, width=24)
        self.ent_mail_recv_col.grid(row=1, column=1, sticky="we", **pad)

        # CC (오른쪽)
        ttk.Label(f_top, text="참조(CC, 쉼표)").grid(row=1, column=2, sticky="e")
        self.ent_mail_receivers_cc = ttk.Entry(f_top, width=48)
        self.ent_mail_receivers_cc.grid(row=1, column=3, columnspan=2, sticky="we", **pad)

        # BCC (오른쪽, 다음 행)
        ttk.Label(f_top, text="숨참조(BCC, 쉼표)").grid(row=2, column=2, sticky="e")
        self.ent_mail_receivers_bcc = ttk.Entry(f_top, width=48)
        self.ent_mail_receivers_bcc.grid(row=2, column=3, columnspan=2, sticky="we", **pad)

        # 제목을 별도 행으로 내려서 좌측~우측 전체 폭 사용
        ttk.Label(f_top, text="메일 제목(선택)").grid(row=3, column=0, sticky="e")
        self.ent_mail_subject = ttk.Entry(f_top)
        self.ent_mail_subject.grid(row=3, column=1, columnspan=4, sticky="we", **pad)






        # self.var_mail_dryrun = tk.BooleanVar(value=False)
        # ttk.Checkbutton(f_top, text="DRY-RUN", variable=self.var_mail_dryrun).grid(row=1, column=4, sticky="w", **pad)


        # === (C) 중단: 블록 관리 + 에디터 ===
        f_blk = ttk.LabelFrame(self.mail_wrap, text="메일 콘텐츠 블록(여러 개)"); f_blk.pack(fill="both", expand=True, **pad)
        f_blk.columnconfigure(1, weight=1)  # 우측 에디터 확장

        # 좌측 리스트 + 스크롤
        left = ttk.Frame(f_blk); left.grid(row=0, column=0, sticky="ns", padx=4, pady=4)
        lb_scroll = ttk.Scrollbar(left, orient="vertical")
        self.lb_mail_blocks = tk.Listbox(
            left, height=12, width=28, exportselection=False, selectmode="browse",
            yscrollcommand=lb_scroll.set
        )
        lb_scroll.config(command=self.lb_mail_blocks.yview)
        self.lb_mail_blocks.grid(row=0, column=0, sticky="ns")
        lb_scroll.grid(row=0, column=1, sticky="ns")
        btns = ttk.Frame(left); btns.grid(row=1, column=0, columnspan=2, pady=(6, 0))
        ttk.Button(btns, text="추가", command=self._mail_add_block).pack(side="left", padx=2)
        ttk.Button(btns, text="삭제", command=self._mail_del_block).pack(side="left", padx=2)
        ttk.Button(btns, text="위",   command=lambda: self._mail_move_block(-1)).pack(side="left", padx=2)
        ttk.Button(btns, text="아래", command=lambda: self._mail_move_block(+1)).pack(side="left", padx=2)

        # 우측 에디터(그리드) — 높이 줄이고 스크롤텍스트가 자체 스크롤 담당
        right = ttk.Frame(f_blk); right.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        right.columnconfigure(1, weight=1)

        self.var_blk_title = tk.StringVar()
        ttk.Label(right, text="블록 제목").grid(row=0, column=0, sticky="e")
        self.ent_blk_title = ttk.Entry(right, textvariable=self.var_blk_title, width=50)
        self.ent_blk_title.grid(row=0, column=1, sticky="we", padx=6, pady=4)

        ttk.Label(right, text="SQL(선택)").grid(row=1, column=0, sticky="ne")
        self.txt_blk_sql = scrolledtext.ScrolledText(right, height=5)   # ↓ 높이 소폭 축소
        # 바로 위 한 줄
        self.txt_blk_sql.grid(row=1, column=1, sticky="we", padx=6, pady=4)
        # ↓ 추가: 블록별 DSN/User/Password 입력
        ttk.Label(right, text="DB 접속(블록 전용)").grid(row=2, column=0, sticky="ne")
        dbline = ttk.Frame(right); dbline.grid(row=2, column=1, sticky="we", padx=6, pady=2)
        dbline.columnconfigure(1, weight=1)
        ttk.Label(dbline, text="DSN").grid(row=0, column=0, sticky="e", padx=(0,6))
        self.ent_blk_dsn = ttk.Entry(dbline, width=48); self.ent_blk_dsn.grid(row=0, column=1, sticky="we")

        ttk.Label(dbline, text="User").grid(row=1, column=0, sticky="e", padx=(0,6))
        self.ent_blk_user = ttk.Entry(dbline, width=24); self.ent_blk_user.grid(row=1, column=1, sticky="w")

        ttk.Label(dbline, text="Password").grid(row=2, column=0, sticky="e", padx=(0,6))
        # 바로 위 한 줄
        self.ent_blk_pw = ttk.Entry(dbline, width=24, show="*"); self.ent_blk_pw.grid(row=2, column=1, sticky="w")
        # ↓ 변경: 체크박스를 row=3로 내려서 DB 프레임과 안겹치게
        opts = ttk.Frame(right); opts.grid(row=3, column=1, sticky="w", padx=6, pady=(0,4))
        self.var_mail_skip_if_no_sql = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            opts, text="SQL이 비어있으면 메일 미전송",
            variable=self.var_mail_skip_if_no_sql
        ).pack(side="left", padx=(0,12))

        # ✅ 재전송 금지(메일 보안) — mail_no_send 위로 배치
        self.var_mail_prohibit_forward = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            opts, text="재전송 금지",
            variable=self.var_mail_prohibit_forward
        ).pack(side="left", padx=(0,12))

        self.var_auto_attach_sql_excel = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            opts, text="전송 시 자동으로 SQL→엑셀 첨부",
            variable=self.var_auto_attach_sql_excel
        ).pack(side="left")


        self.var_mail_no_send = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="메일 미전송(스케줄러만)", variable=self.var_mail_no_send)\
            .pack(side="left", padx=(12, 0))


        ttk.Label(right, text="제목 템플릿").grid(row=4, column=0, sticky="ne")
        self.txt_blk_subject = scrolledtext.ScrolledText(right, height=2)
        self.txt_blk_subject.grid(row=4, column=1, sticky="we", padx=6, pady=4)


        ttk.Label(right, text="HTML 템플릿").grid(row=5, column=0, sticky="ne")
        self.txt_blk_html = scrolledtext.ScrolledText(right, height=7)  # ↓
        self.txt_blk_html.grid(row=5, column=1, sticky="we", padx=6, pady=4)

        ttk.Label(right, text="파이썬 코드(선택)").grid(row=6, column=0, sticky="ne")
        self.txt_blk_py = scrolledtext.ScrolledText(right, height=5)    # ↓
        self.txt_blk_py.grid(row=6, column=1, sticky="we", padx=6, pady=4)

        # 리스트 선택 이벤트
        self.lb_mail_blocks.bind("<<ListboxSelect>>", self._mail_on_select)

        # ✅ 최초 진입 시 블록 1개 보장 (위에서 만든 blk dict 사용)
        if not self._mail_blocks:
            self._mail_blocks.append(blk)
            self.lb_mail_blocks.insert("end", blk.get("title", "블록1"))
            self.lb_mail_blocks.selection_set(0)
            self.lb_mail_blocks.activate(0)
            self._mail_selected = 0
            self._mail_load_block(0)


        f_cmd = ttk.Frame(self.mail_wrap); f_cmd.pack(fill="x", **pad)

        # 왼쪽 버튼
        ttk.Button(f_cmd, text="블록 저장/갱신", command=self._mail_save_block).pack(side="left", padx=4)
        ttk.Button(f_cmd, text="미리보기/실행", command=self.on_mail_preview).pack(side="left", padx=4)

        # ✅ 현재 편집 상태 표시
        self.var_mail_edit_hint = tk.StringVar(value="현재: 신규 등록 모드")
        ttk.Label(f_cmd, textvariable=self.var_mail_edit_hint).pack(side="left", padx=10)

        # 오른쪽 버튼(업데이트/신규/전송)
        ttk.Button(f_cmd, text="편집 해제", command=self.on_mail_clear_edit).pack(side="right", padx=4)
        ttk.Button(f_cmd, text="기존 작업 업데이트", command=self.on_mail_update_job).pack(side="right", padx=4)
        ttk.Button(f_cmd, text="메일 스케줄 등록(신규)", command=self.on_mail_add_job).pack(side="right", padx=4)
        ttk.Button(f_cmd, text="메일 바로전송", command=self.on_mail_send_now).pack(side="right", padx=4)


        # === (E) 메일 스케줄 ===  ← 위로 이동
        f_mail_sch = ttk.LabelFrame(self.mail_wrap, text="메일 스케줄"); f_mail_sch.pack(fill="x", **pad)

        bar = ttk.Frame(f_mail_sch); bar.grid(row=0, column=0, columnspan=6, sticky="we", padx=4, pady=(6,0))
        self.var_mail_sch_mode = tk.StringVar(value="once")
        for i,(label,val) in enumerate([("한 번","once"),("매일","daily"),("매주","weekly"),("매월","monthly"),("간격","interval")]):
            ttk.Radiobutton(bar, text=label, value=val, variable=self.var_mail_sch_mode,
                            command=self._on_mail_sched_mode_changed).grid(row=0, column=i, padx=(0,8), sticky="w")

        preset = ttk.Frame(f_mail_sch); preset.grid(row=1, column=0, columnspan=6, sticky="w", padx=4, pady=(2,6))
        ttk.Button(preset, text="지금+5분", width=10, command=self._preset_mail_now_plus_5).grid(row=0, column=0, padx=4)
        ttk.Button(preset, text="09:00", width=8, command=lambda: self._preset_mail_time("09:00")).grid(row=0, column=1, padx=4)
        ttk.Button(preset, text="18:00", width=8, command=lambda: self._preset_mail_time("18:00")).grid(row=0, column=2, padx=4)

        # 모드별 프레임
        self.frame_mail_once = ttk.Frame(f_mail_sch)
        ttk.Label(self.frame_mail_once, text="날짜시각 (YYYY-MM-DD HH:MM)").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self.ent_mail_once_dt = ttk.Entry(self.frame_mail_once, width=20); self.ent_mail_once_dt.grid(row=0, column=1, sticky="w", padx=4, pady=4)

        self.frame_mail_daily = ttk.Frame(f_mail_sch)
        ttk.Label(self.frame_mail_daily, text="시각 (HH:MM)").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self.ent_mail_daily_time = ttk.Entry(self.frame_mail_daily, width=10); self.ent_mail_daily_time.grid(row=0, column=1, sticky="w", padx=4, pady=4)

        self.frame_mail_weekly = ttk.Frame(f_mail_sch)
        ttk.Label(self.frame_mail_weekly, text="요일").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self.cmb_mail_weekday = ttk.Combobox(self.frame_mail_weekly, width=8, values=["월","화","수","목","금","토","일"], state="readonly")
        self.cmb_mail_weekday.set("월"); self.cmb_mail_weekday.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(self.frame_mail_weekly, text="시각 (HH:MM)").grid(row=0, column=2, sticky="e", padx=4, pady=4)
        self.ent_mail_weekly_time = ttk.Entry(self.frame_mail_weekly, width=10); self.ent_mail_weekly_time.grid(row=0, column=3, sticky="w", padx=4, pady=4)

        self.frame_mail_monthly = ttk.Frame(f_mail_sch)
        ttk.Label(self.frame_mail_monthly, text="일자(1~31)").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self.spin_mail_dom = tk.Spinbox(self.frame_mail_monthly, from_=1, to=31, width=6)
        self.spin_mail_dom.delete(0, "end"); self.spin_mail_dom.insert(0, "1"); self.spin_mail_dom.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(self.frame_mail_monthly, text="시각 (HH:MM)").grid(row=0, column=2, sticky="e", padx=4, pady=4)
        self.ent_mail_monthly_time = ttk.Entry(self.frame_mail_monthly, width=10); self.ent_mail_monthly_time.grid(row=0, column=3, sticky="w", padx=4, pady=4)

        self.frame_mail_interval = ttk.Frame(f_mail_sch)
        ttk.Label(self.frame_mail_interval, text="간격(시간)").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self.ent_mail_iv_h = ttk.Entry(self.frame_mail_interval, width=6); self.ent_mail_iv_h.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        ttk.Label(self.frame_mail_interval, text="간격(분)").grid(row=0, column=2, sticky="e", padx=4, pady=4)
        self.ent_mail_iv_m = ttk.Entry(self.frame_mail_interval, width=6); self.ent_mail_iv_m.grid(row=0, column=3, sticky="w", padx=4, pady=4)

        self._on_mail_sched_mode_changed()


        # === (F) 메일 작업 ===
        f_mail_jobs = ttk.LabelFrame(self.mail_wrap, text="메일 작업"); f_mail_jobs.pack(fill="both", expand=True, **pad)

        mail_toolbar = ttk.Frame(f_mail_jobs); mail_toolbar.pack(fill="x", padx=8, pady=(8, 0))
        ttk.Button(mail_toolbar, text="선택작업 중지", command=self.on_mail_pause_job).pack(side="left", padx=4)
        ttk.Button(mail_toolbar, text="선택작업 재개", command=self.on_mail_resume_job).pack(side="left", padx=4)
        ttk.Button(mail_toolbar, text="선택작업 삭제", command=self.on_mail_remove_job).pack(side="left", padx=4)

        mail_tree_wrap = ttk.Frame(f_mail_jobs); mail_tree_wrap.pack(fill="both", expand=True, padx=8, pady=6)
        mail_tree_wrap.rowconfigure(0, weight=1); mail_tree_wrap.columnconfigure(0, weight=1)

        self.mail_tree = ttk.Treeview(
            mail_tree_wrap,
            columns=("desc","mode","id"),
            show="headings",
            style="Custom.Treeview"
        )
        self.mail_tree.heading("desc", text="설명")
        self.mail_tree.heading("mode", text="유형/제목")
        self.mail_tree.heading("id",   text="Job ID")

        mv = ttk.Scrollbar(mail_tree_wrap, orient="vertical", command=self.mail_tree.yview)
        self.mail_tree.configure(yscrollcommand=mv.set)
        self.mail_tree.grid(row=0, column=0, sticky="nsew")
        mv.grid(row=0, column=1, sticky="ns")

        self.mail_tree.tag_configure("paused",    foreground="gray",  font=self.font_paused)
        self.mail_tree.tag_configure("scheduled", foreground="black", font=self.font_normal)

        # 더블클릭 → 메일 스케줄 상세(원하면 페이로드 역주입도 가능)
        # 더블클릭 → 메일 작업 로드
        self.mail_tree.bind("<Double-1>", self._on_mail_tree_dblclick)


        # 메일용 저장소
        if not hasattr(self, "mail_jobs"):
            self.mail_jobs = {}

        # ★★★ 바로 아래 한 줄 추가: 삭제 보관함(아카이브) 로드
        self.mail_jobs_archive = self._load_mail_archive()

        # 기존 스케줄에서 이미 살아있는 메일 잡을 트리에 채움
        self._load_mail_jobs_into_tree()


    # ---------------- 로그 탭 ----------------
    def _build_log(self, parent):
        self.txt_log = scrolledtext.ScrolledText(parent, height=24)
        self.txt_log.pack(fill="both", expand=True, padx=8, pady=8)

        # 로깅 핸들러: 텍스트에 출력
        class TextHandler(logging.Handler):
            def __init__(self, widget):
                super().__init__()
                self.widget = widget
            def emit(self, record):
                msg = self.format(record) + "\n"
                # Tkinter 스레드 안전 처리
                self.widget.after(0, lambda: (self.widget.insert("end", msg), self.widget.see("end")))

        th = TextHandler(self.txt_log)
        th.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(th)

        # 시작 시 기존 로그 일부 보여주기
        try:
            if os.path.exists(LOG_PATH):
                with open(LOG_PATH, "r", encoding="utf-8", errors="ignore") as fp:
                    lines = fp.readlines()[-MAX_BOOT_LOG_LINES:]
                    self.txt_log.insert("end", "".join(lines))
                    self.txt_log.see("end")
        except Exception:
            pass

    # ---------------- 트리/잡 갱신 ----------------
    def _load_jobs_into_tree(self):
        for job in scheduler.get_jobs():
            payload = (job.kwargs or {}).get("payload", {})
            if payload.get("job_category") == "mail":
                continue  # 메일 잡은 메일 트리에서만 관리
            self._update_job_row(job.id)
            payload = (job.kwargs or {}).get("payload", {})
            desc = (
                f"title={payload.get('job_title', '')} | "
                f"general={payload.get('send_general')} | "
                f"template={payload.get('send_template')} | "
                f"table={payload.get('send_table')} | "
                f"card={payload.get('send_card')} | "
                f"group={payload.get('group_send')} | dryrun={payload.get('dryrun')} | persisted"
            )
            next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "없음"
            mode = self._trigger_mode(job)
            vals = (f"{desc} | next={next_run}", f"{mode}", job.id)
            if self.tree.exists(job.id):
                self.tree.item(job.id, values=vals)
            else:
                self.tree.insert("", "end", iid=job.id, values=vals)

    def _load_mail_jobs_into_tree(self):
        for job in scheduler.get_jobs():
            payload = (job.kwargs or {}).get("payload", {})
            if payload.get("job_category") != "mail":
                continue
            self._update_mail_job_row(job.id)

    def _job_status_and_next(self, job):
        if job is None:
            return ("deleted", "없음")
        if job.next_run_time is None:
            return ("paused", "없음")
        return ("scheduled", job.next_run_time.strftime("%Y-%m-%d %H:%M:%S"))

    def _update_job_row(self, job_id):
        job = scheduler.get_job(job_id)
        if job is None:
            self._remove_row_safe(job_id)
            return
        mode = self._trigger_mode(job)
        status, next_run = self._job_status_and_next(job)
        payload = (job.kwargs or {}).get("payload", {})
        desc = (
            f"title={payload.get('job_title', '')} | "
            f"general={payload.get('send_general')} | "
            f"template={payload.get('send_template')} | "
            f"table={payload.get('send_table')} | "
            f"card={payload.get('send_card')} | "
            f"group={payload.get('group_send')} | dryrun={payload.get('dryrun')} "
            f"| status={status} | next={next_run}"
        )
        vals = (desc, f"{mode}", job.id)
        if self.tree.exists(job.id):
            self.tree.item(job.id, values=vals, tags=(status,))
        else:
            self.tree.insert("", "end", iid=job.id, values=vals, tags=(status,))

    def _on_job_executed(self, event):
        jid = event.job_id
        job = scheduler.get_job(jid)
        payload = (job.kwargs or {}).get("payload", {}) if job else {}
        cat = payload.get("job_category")
        if cat == "mail" and hasattr(self, "mail_tree"):
            self.after(0, lambda: self._update_mail_job_row(jid))
        else:
            self.after(0, lambda: self._update_job_row(jid))



    def _on_job_removed(self, event):
        jid = event.job_id
        # 두 트리에서 안전 삭제 시도
        self.after(0, lambda: self._remove_row_safe(jid))
        if hasattr(self, "mail_tree") and self.mail_tree.exists(jid):
            self.after(0, lambda: self.mail_tree.delete(jid))
        if hasattr(self, "mail_jobs"):
            self.mail_jobs.pop(jid, None)




    def _remove_row_safe(self, job_id: str):
        if self.tree.exists(job_id):
            self.tree.delete(job_id)
        self.jobs.pop(job_id, None)

    # ---------------- 버튼 핸들러 ----------------
    def on_device_and_keys(self):
        try:
            km = KnoxMessenger(CONFIG["HOST"], CONFIG["SYSTEM_ID"], CONFIG["TOKEN"],
                               proxies=CONFIG["PROXIES"], verify_ssl=CONFIG["VERIFY_SSL"])
            device_id = km.device_regist()
            CONFIG["DEVICE_ID"] = device_id
            keys = km.getKeys()
            CONFIG["KEY_HEX"] = keys["key"]
            logger.info(f"[OK] device_id={device_id}, key_hex_len={len(keys['key'])}")
        except Exception as e:
            logger.exception(f"[ERROR] 장비등록/키획득 실패: {e}")

    def on_preview(self):
        try:
            dsn = self.ent_dsn.get().strip()
            user = self.ent_user.get().strip()
            pw   = self.ent_pw.get().strip()
            sql  = self.txt_sql.get("1.0","end").strip()
            if not (dsn and user and pw and sql):
                messagebox.showwarning("확인", "DSN/USER/PASS/SQL을 입력하세요.")
                return
            df = run_sql(dsn, user, pw, sql)
            logger.info(f"[PREVIEW] {len(df)} 행")
            logger.info("\n" + df.head(20).to_string(index=False))
        except Exception as e:
            logger.exception(f"[ERROR] 미리보기 실패: {e}")

    def on_pick_font_color(self):
        color = colorchooser.askcolor(title="표 글자색 선택")
        if color and color[1]:
            self.cmb_font_color.set(color[1])

    def on_pick_title_color(self):
        color = colorchooser.askcolor(title="제목 글자색 선택")
        if color and color[1]:
            self.cmb_title_color.set(color[1])

    def _collect_payload(self, require_schedule: bool = True):
        # 민감/네트워크
        host = CONFIG["HOST"]; system_id = CONFIG["SYSTEM_ID"]; token = CONFIG["TOKEN"]
        key_hex = CONFIG["KEY_HEX"]; device_id = CONFIG["DEVICE_ID"]
        verify = CONFIG["VERIFY_SSL"]; proxies = CONFIG["PROXIES"]

        # DB/SQL
        dsn = self.ent_dsn.get().strip()
        user = self.ent_user.get().strip()
        pw   = self.ent_pw.get().strip()
        sql  = self.txt_sql.get("1.0","end").strip()

        # 플래그/입력
        send_general  = self.var_send_general.get()
        send_template = self.var_send_template.get()
        send_table    = self.var_send_table.get()
        send_card     = self.var_send_card.get()

        receivers_csv   = self.ent_receivers.get().strip()
        df_receiver_col = self.ent_recv_col.get().strip() or None
        group_send      = self.var_group_send.get()
        chatroom_id     = self.ent_chatroom.get().strip() or None

        general_text = self.txt_general.get("1.0","end").strip()
        template     = self.txt_tpl.get("1.0","end").strip()
        card_json    = self.txt_card_json.get("1.0","end").strip()
        job_title    = self.ent_job_title.get().strip() or None
        dryrun       = self.var_dryrun.get()

        # 검증
        if not receivers_csv and not df_receiver_col:
            messagebox.showwarning("확인", "수신자(SSO) 또는 수신자 컬럼명을 지정하세요.")
            return None
        if not (send_general or send_template or send_table or send_card):
            messagebox.showwarning("확인", "전송 유형을 하나 이상 선택하세요(일반/템플릿/표/카드).")
            return None
        if send_general and not general_text:
            messagebox.showwarning("확인", "일반 메시지를 선택하면 메시지 텍스트가 필요합니다.")
            return None
        if send_template and not template:
            messagebox.showwarning("확인", "템플릿 메시지를 선택하면 텍스트가 필요합니다.")
            return None
        if send_card and not card_json:
            messagebox.showwarning("확인", "Adaptive Card 전송을 선택하면 카드 JSON이 필요합니다.")
            return None

        # 표 스타일 해석
        tw = self._safe_int(self.spin_tbl_width.get(), 1000)
        fs = self._safe_int(self.spin_font_px.get(),   13)

        color_name = self.cmb_header_bg.get().strip()
        hb = color_name if (color_name.startswith("#") and len(color_name) in (4,7)) \
             else self.header_color_map.get(color_name, "#BBE9F0")

        font_family = self.cmb_font_family.get().strip() or "Malgun Gothic"
        fc = self._resolve_color(self.cmb_font_color.get(),  "#000000")
        tc = self._resolve_color(self.cmb_title_color.get(), "#000000")

        # 전역 치환 생성
        gvars = self._build_global_vars()
        chatroom_title = self.ent_chatroom_title.get().strip() or None

        payload = {
            "host": host, "system_id": system_id, "token": token,
            "key_hex": key_hex, "device_id": device_id,
            "verify_ssl": verify, "proxies": proxies, "dryrun": dryrun,

            "dsn": dsn, "user": user, "pw": pw, "sql": sql if sql else None,

            "send_general": send_general,
            "send_template": send_template,
            "send_table": send_table,
            "send_card": send_card,

            "general_text": general_text,
            "template": template,
            "card_json": card_json,
            "job_title": job_title,
            "mail_subject": (self.ent_mail_subject.get().strip() or None),

            "table_title_from_general": self.var_table_title_from_general.get(),

            "receivers_csv": receivers_csv, "df_receiver_col": df_receiver_col,
            "group_send": group_send, "chatroom_id": chatroom_id, "chatroom_title": chatroom_title,

            "table_width_px": tw, "font_size_px": fs, "header_bg": hb,
            "font_family": font_family, "font_color": fc, "title_color": tc,

            "globals": gvars,
        }

        # 변경 코드 (_collect_payload 부분: 모드별 입력 필드 읽기 로직만 보강)
        # 기존 _collect_payload 내부의 "스케줄 처리" if require_schedule: 블록을 아래처럼 교체
        if require_schedule:
            sch_mode = self.var_sch_mode.get()

            try:
                if sch_mode == "once":
                    once_dt = (self.ent_once_dt.get().strip() if hasattr(self, "ent_once_dt") else "")
                    if not once_dt:
                        raise ValueError("한 번 전송 시각(YYYY-MM-DD HH:MM)을 입력")
                    trigger = DateTrigger(run_date=datetime.strptime(once_dt, "%Y-%m-%d %H:%M"))

                elif sch_mode == "daily":
                    daily = (self.ent_daily_time.get().strip() if hasattr(self, "ent_daily_time") else "")
                    if not daily:
                        raise ValueError("매일 시각(HH:MM)을 입력")
                    hh, mm = [int(x) for x in daily.split(":")]
                    trigger = CronTrigger(hour=hh, minute=mm)

                elif sch_mode == "weekly":
                    weekly = (self.ent_weekly_time.get().strip() if hasattr(self, "ent_weekly_time") else "")
                    if not weekly:
                        raise ValueError("매주 시각(HH:MM)을 입력")
                    hh, mm = [int(x) for x in weekly.split(":")]
                    dow_map = {"월": "mon", "화": "tue", "수": "wed", "목": "thu", "금": "fri", "토": "sat", "일": "sun"}
                    sel = self.cmb_weekday.get().strip() or "월"
                    dow = dow_map.get(sel, "mon")
                    trigger = CronTrigger(day_of_week=dow, hour=hh, minute=mm)

                elif sch_mode == "monthly":
                    monthly = (self.ent_monthly_time.get().strip() if hasattr(self, "ent_monthly_time") else "")
                    if not monthly:
                        raise ValueError("매월 시각(HH:MM)을 입력")
                    hh, mm = [int(x) for x in monthly.split(":")]
                    dom = self._safe_int(self.spin_dom.get(), 1)
                    if not (1 <= dom <= 31):
                        raise ValueError("매월 일자(1~31)를 확인")
                    trigger = CronTrigger(day=dom, hour=hh, minute=mm)

                else:  # interval
                    iv_h = (self.ent_iv_h.get().strip() if hasattr(self, "ent_iv_h") else "0")
                    iv_m = (self.ent_iv_m.get().strip() if hasattr(self, "ent_iv_m") else "0")
                    minutes = int(iv_m) if iv_m else 0
                    hours   = int(iv_h) if iv_h else 0
                    if minutes == 0 and hours == 0:
                        raise ValueError("간격(분/시간) 중 하나 이상 입력")
                    trigger = IntervalTrigger(hours=hours, minutes=minutes)
            except Exception as e:
                messagebox.showerror("스케줄 오류", str(e))
                return None
        else:
            trigger  = None
            sch_mode = "now"


        payload["schedule_mode"] = sch_mode
        return trigger, payload, sch_mode

    def on_add_job(self):
        res = self._collect_payload()
        if not res:
            return
        trigger, payload, sch_mode = res

        # ✅ add_job 전에 태그 세팅
        payload["job_category"] = payload.get("job_category") or "msg"

        user_title = payload.get("job_title") or sch_mode
        job = scheduler.add_job(job_send_messages, trigger=trigger, kwargs={"payload": payload}, name=user_title)
        self.jobs[job.id] = payload

        mode = self._trigger_mode(job)
        desc = (
            f"title={payload.get('job_title','')} | "
            f"general={payload['send_general']} | "
            f"template={payload['send_template']} | "
            f"table={payload['send_table']} | "
            f"card={payload['send_card']} | "
            f"group={payload['group_send']} | dryrun={payload['dryrun']}"
        )
        next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "없음"
        self.tree.insert("", "end", iid=job.id, values=(f"{desc} | next={next_run}", mode, job.id))
        self._update_job_row(job.id)
        logger.info(f"[INFO] 작업 등록: {job.id}")


    def on_send_now(self):
        res = self._collect_payload(require_schedule=False)
        if not res:
            return
        _, payload, _ = res
        logger.info("[INFO] 즉시 전송 시작")
        try:
            job_send_messages(payload)
            logger.info("[OK] 즉시 전송 완료")
        except Exception as e:
            logger.exception(f"[ERROR] 바로전송 실패: {e}")

    def _selected_job(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    def _selected_mail_job(self):
        sel = self.mail_tree.selection()
        return sel[0] if sel else None

    def _mail_job_status_and_next(self, job):
        if job is None:
            return ("deleted", "없음")
        if job.next_run_time is None:
            return ("paused", "없음")
        return ("scheduled", job.next_run_time.strftime("%Y-%m-%d %H:%M:%S"))

    def _update_mail_job_row(self, job_id):
        job = scheduler.get_job(job_id)
        if job is None:
            if self.mail_tree.exists(job_id):
                self.mail_tree.delete(job_id)
            self.mail_jobs.pop(job_id, None)
            return
        mode = self._trigger_mode(job)
        status, next_run = self._mail_job_status_and_next(job)
        payload = (job.kwargs or {}).get("payload", {})
        title = (job.name or
                (payload.get("mail_subject") or payload.get("job_title","")))
        desc = (f"title={title} | sections={len(payload.get('sql_blocks',[]))} "
                f"| TO={payload.get('receivers_csv','')} | dryrun={payload.get('dryrun')} "
                f"| status={status} | next={next_run}")
        vals = (desc, f"{mode}", job.id)
        if self.mail_tree.exists(job.id):
            self.mail_tree.item(job.id, values=vals, tags=(status,))
        else:
            self.mail_tree.insert("", "end", iid=job.id, values=vals, tags=(status,))

    def on_mail_pause_job(self):
        jid = self._selected_mail_job()
        if not jid: return
        scheduler.pause_job(jid)
        logger.info(f"[MAIL] 작업 일시중지: {jid}")
        self._update_mail_job_row(jid)

    def on_mail_resume_job(self):
        jid = self._selected_mail_job()
        if not jid: return
        scheduler.resume_job(jid)
        logger.info(f"[MAIL] 작업 재개: {jid}")
        self._update_mail_job_row(jid)

    def on_mail_remove_job(self):
        jid = self._selected_mail_job()
        if not jid: return
        try:
            # ★★★ 바로 위 한 줄
            # 삭제 전에 페이로드 스냅샷 백업
            job = scheduler.get_job(jid)
            payload = (job.kwargs or {}).get("payload", {}) if job else (self.mail_jobs.get(jid) or {})
            job_name = (job.name if job else "") or (payload.get("mail_subject") or payload.get("job_title",""))
            next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if (job and job.next_run_time) else "없음"
            self._archive_mail_job(jid, payload, job_name, next_run)

            scheduler.remove_job(jid)
            logger.info(f"[MAIL] 작업 삭제: {jid}")
        except JobLookupError:
            logger.info(f"[MAIL] 작업이 이미 삭제됨: {jid}")
        finally:
            if self.mail_tree.exists(jid):
                self.mail_tree.delete(jid)
            self.mail_jobs.pop(jid, None)
        if getattr(self, "_mail_edit_job_id", None) == jid:
            self.on_mail_clear_edit()

    def _on_mail_tree_dblclick(self, event):
        item = self.mail_tree.identify_row(event.y)
        if not item:
            return
        self._mail_editing_job_id = item
        job = scheduler.get_job(item)
        if not job:
            return

        payload = (job.kwargs or {}).get("payload", {})
        # ---- 상단/공통 필드 채우기 ----
        try:
            # DB/SQL (공유 인풋 사용)
            if hasattr(self, "ent_dsn"):
                self.ent_dsn.delete(0, "end"); self.ent_dsn.insert(0, payload.get("dsn",""))
            if hasattr(self, "ent_user"):
                self.ent_user.delete(0, "end"); self.ent_user.insert(0, payload.get("user",""))
            if hasattr(self, "ent_pw"):
                self.ent_pw.delete(0, "end");   self.ent_pw.insert(0, payload.get("pw",""))

            # 메일 기본
            if hasattr(self, "ent_mail_sender"):
                self.ent_mail_sender.delete(0, "end"); self.ent_mail_sender.insert(0, payload.get("sender_id",""))
            if hasattr(self, "ent_mail_receivers"):
                self.ent_mail_receivers.delete(0, "end"); self.ent_mail_receivers.insert(0, payload.get("receivers_csv",""))

            # ★★★ CC/BCC 필드 복원
            if hasattr(self, "ent_mail_receivers_cc"):
                self.ent_mail_receivers_cc.delete(0, "end"); self.ent_mail_receivers_cc.insert(0, payload.get("receivers_cc_csv",""))
            if hasattr(self, "ent_mail_receivers_bcc"):
                self.ent_mail_receivers_bcc.delete(0, "end"); self.ent_mail_receivers_bcc.insert(0, payload.get("receivers_bcc_csv",""))

            if hasattr(self, "ent_mail_recv_col"):
                self.ent_mail_recv_col.delete(0, "end")
                self.ent_mail_recv_col.insert(0, payload.get("df_receiver_col","") or "")

            if hasattr(self, "ent_mail_subject"):
                self.ent_mail_subject.delete(0, "end")
                self.ent_mail_subject.insert(0, payload.get("mail_subject","") or "")            
            if hasattr(self, "var_mail_dryrun"):
                self.var_mail_dryrun.set(bool(payload.get("dryrun", False)))
            # ↓ 추가: 'SQL이 비어있으면 메일 미전송' 체크 복원
            if hasattr(self, "var_mail_skip_if_no_sql"):
                self.var_mail_skip_if_no_sql.set(bool(payload.get("skip_if_no_sql", False)))
            if hasattr(self, "var_mail_prohibit_forward"):
                self.var_mail_prohibit_forward.set(payload.get("doc_secu_type") == "PROHIBIT_FORWARD")

            # ✅ 추가: mail_no_send 복원
            if hasattr(self, "var_mail_no_send"):
                self.var_mail_no_send.set(bool(payload.get("mail_no_send", False)))

            # 메일 블록 리스트/에디터
            blocks = list(payload.get("sql_blocks", []))
            # 내부 상태
            self._mail_blocks = blocks
            self._mail_selected = None

            # 좌측 리스트 갱신
            if hasattr(self, "lb_mail_blocks"):
                self.lb_mail_blocks.delete(0, "end")
                for i, b in enumerate(blocks, start=1):
                    self.lb_mail_blocks.insert("end", b.get("title", f"블록{i}"))
                if blocks:
                    self.lb_mail_blocks.selection_clear(0, "end")
                    self.lb_mail_blocks.selection_set(0)
                    self.lb_mail_blocks.activate(0)
                    self.lb_mail_blocks.see(0)
                    self._mail_selected = 0
                    # 에디터에 첫 블록 로드
                    self._mail_load_block(0)

            # ---- 메일 스케줄 복원 ----
            t = job.trigger
            # 1) 모드 추정 → 표시 프레임 전환
            mode_guess = self._trigger_mode(job)
            if hasattr(self, "var_mail_sch_mode"):
                self.var_mail_sch_mode.set(mode_guess if mode_guess in {"once","daily","weekly","monthly","interval"} else "daily")
            if hasattr(self, "_on_mail_sched_mode_changed"):
                self._on_mail_sched_mode_changed()

            # 2) 메일 스케줄 입력칸 초기화
            if hasattr(self, "_clear_mail_sched_fields"):
                self._clear_mail_sched_fields()

            # 3) 트리거별 값 주입
            from apscheduler.triggers.date import DateTrigger as _DT
            from apscheduler.triggers.interval import IntervalTrigger as _IT
            from apscheduler.triggers.cron import CronTrigger as _CT

            if isinstance(t, _DT):
                if hasattr(self, "var_mail_sch_mode"):
                    self.var_mail_sch_mode.set("once"); self._on_mail_sched_mode_changed()
                run_dt = t.run_date
                if hasattr(self, "ent_mail_once_dt") and run_dt:
                    self.ent_mail_once_dt.insert(0, run_dt.strftime("%Y-%m-%d %H:%M"))

            elif isinstance(t, _IT):
                if hasattr(self, "var_mail_sch_mode"):
                    self.var_mail_sch_mode.set("interval"); self._on_mail_sched_mode_changed()
                td = t.interval
                total_minutes = int(td.total_seconds() // 60)
                hours, minutes = divmod(total_minutes, 60)
                if hasattr(self, "ent_mail_iv_h"): self.ent_mail_iv_h.insert(0, str(hours))
                if hasattr(self, "ent_mail_iv_m"): self.ent_mail_iv_m.insert(0, str(minutes))

            elif isinstance(t, _CT):
                fields = {f.name: f for f in t.fields}

                def _first(expr, default="*"):
                    s = (str(expr) if expr is not None else default).strip()
                    if s == "*": return default
                    s = s.split(",")[0]
                    s = s.split("/")[0]
                    s = s.split("-")[0]
                    return s

                hour_s   = _first(fields.get("hour"))
                minute_s = _first(fields.get("minute"))
                hh = "00" if hour_s   in ("*", "") else f"{int(hour_s):02d}"
                mm = "00" if minute_s in ("*", "") else f"{int(minute_s):02d}"
                time_val = f"{hh}:{mm}"

                dow_s = _first(fields.get("day_of_week")) if fields.get("day_of_week") else "*"
                day_s = _first(fields.get("day")) if fields.get("day") else "*"

                eng2kor = {"mon":"월","tue":"화","wed":"수","thu":"목","fri":"금","sat":"토","sun":"일"}

                if dow_s not in ("*", ""):
                    if hasattr(self, "var_mail_sch_mode"):
                        self.var_mail_sch_mode.set("weekly"); self._on_mail_sched_mode_changed()
                    if hasattr(self, "cmb_mail_weekday"):
                        self.cmb_mail_weekday.set(eng2kor.get(dow_s.lower(), "월"))
                    if hasattr(self, "ent_mail_weekly_time"):
                        self.ent_mail_weekly_time.insert(0, time_val)

                elif day_s not in ("*", ""):
                    if hasattr(self, "var_mail_sch_mode"):
                        self.var_mail_sch_mode.set("monthly"); self._on_mail_sched_mode_changed()
                    try:
                        d = int(day_s)
                        if hasattr(self, "spin_mail_dom"):
                            self.spin_mail_dom.delete(0, "end"); self.spin_mail_dom.insert(0, str(d))
                    except:
                        pass
                    if hasattr(self, "ent_mail_monthly_time"):
                        self.ent_mail_monthly_time.insert(0, time_val)

                else:
                    if hasattr(self, "var_mail_sch_mode"):
                        self.var_mail_sch_mode.set("daily"); self._on_mail_sched_mode_changed()
                    if hasattr(self, "ent_mail_daily_time"):
                        self.ent_mail_daily_time.insert(0, time_val)

            # 표시 갱신
            self.update_idletasks()
            self._mail_edit_job_id = item
            if hasattr(self, "var_mail_edit_hint"):
                self.var_mail_edit_hint.set(f"현재: 편집중({item})")            
            logger.info(f"[MAIL] 선택 작업 로드: {item}")
        except Exception as e:
            logger.exception(f"[ERROR] 메일 작업 로드 실패: {e}")


    def on_pause_job(self):
        jid = self._selected_job()
        if not jid: return
        scheduler.pause_job(jid)
        logger.info(f"[INFO] 작업 일시중지: {jid}")
        self._update_job_row(jid)

    def on_resume_job(self):
        jid = self._selected_job()
        if not jid: return
        scheduler.resume_job(jid)
        logger.info(f"[INFO] 작업 재개: {jid}")
        self._update_job_row(jid)

    def on_remove_job(self):
        jid = self._selected_job()
        if not jid:
            return
        try:
            job = scheduler.get_job(jid)
            if job is None:
                logger.info(f"[INFO] 작업이 이미 실행/삭제되어 스케줄러에 없습니다: {jid}")
            else:
                scheduler.remove_job(jid)
                logger.info(f"[INFO] 작업 삭제: {jid}")
        except JobLookupError:
            logger.info(f"[INFO] 작업이 이미 삭제되었습니다: {jid}")
        finally:
            if self.tree.exists(jid):
                self.tree.delete(jid)
            self.jobs.pop(jid, None)

    # ---------------- 트리 더블클릭 → 필드 채우기 ----------------
    def _on_tree_dblclick(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        job = scheduler.get_job(item)
        if not job:
            return
        payload = (job.kwargs or {}).get("payload", {})
        # 상단 필드 채우기(필요한 것들만 대표적으로 채움)
        # 변경: 체크박스/스위치/옵션을 '빠짐없이' 일괄 반영 + 누락 필드 보강 + UI 강제 갱신
        # (위 payload 읽기 직후 ~ SQL 채우기 사이를 아래 블록으로 교체 또는 아래 줄들 추가)

        # ---- 전송 옵션 체크박스 · 스위치 일괄 반영 ----
        self.var_send_general.set(bool(payload.get("send_general", False)))
        self.var_send_template.set(bool(payload.get("send_template", False)))
        self.var_send_table.set(bool(payload.get("send_table", False)))
        self.var_send_card.set(bool(payload.get("send_card", False)))
        self.var_table_title_from_general.set(bool(payload.get("table_title_from_general", False)))
        self.var_group_send.set(bool(payload.get("group_send", True)))
        self.var_dryrun.set(bool(payload.get("dryrun", False)))

        # ---- 식별/대화방 ----
        self.ent_job_title.delete(0, "end"); self.ent_job_title.insert(0, payload.get("job_title",""))
        self.ent_receivers.delete(0, "end"); self.ent_receivers.insert(0, payload.get("receivers_csv",""))
        self.ent_recv_col.delete(0, "end");  self.ent_recv_col.insert(0, payload.get("df_receiver_col","") or "")
        self.ent_chatroom.delete(0, "end");  self.ent_chatroom.insert(0, payload.get("chatroom_id","") or "")
        # 대화방 이름(선택) 필드도 복원
        if hasattr(self, "ent_chatroom_title"):
            self.ent_chatroom_title.delete(0, "end")
            self.ent_chatroom_title.insert(0, payload.get("chatroom_title","") or "")

        # ---- 메시지 영역 ----
        self.txt_general.delete("1.0","end"); self.txt_general.insert("1.0", payload.get("general_text",""))
        self.txt_tpl.delete("1.0","end");     self.txt_tpl.insert("1.0", payload.get("template",""))
        self.txt_card_json.delete("1.0","end"); self.txt_card_json.insert( "1.0", payload.get("card_json",""))

        # ---- SQL 미리보기 ----
        self.txt_sql.delete("1.0", "end"); self.txt_sql.insert("1.0", payload.get("sql", "") or "")

        # ---- 표시 갱신 보증 ----
        self.update_idletasks()


        # 표 스타일
        self.spin_tbl_width.delete(0, "end"); self.spin_tbl_width.insert(0, str(payload.get("table_width_px", 1000)))
        self.spin_font_px.delete(0, "end");   self.spin_font_px.insert(0, str(payload.get("font_size_px", 13)))
        # 헤더 색상 역매핑
        inv_header = {v:k for k,v in self.header_color_map.items()}
        self.cmb_header_bg.set(inv_header.get(payload.get("header_bg","#BBE9F0"), "파랑"))
        self.cmb_font_family.set(payload.get("font_family","Malgun Gothic"))

        # 색상은 이름/HEX 모두 허용
        def _best_name(hexval):
            for k, v in self.text_color_map.items():
                if v.lower() == (hexval or "").lower():
                    return k
            return hexval or "검정"

        self.cmb_font_color.set(_best_name(payload.get("font_color","#000000")))
        self.cmb_title_color.set(_best_name(payload.get("title_color","#000000")))

        # 기존 _on_tree_dblclick 마지막 부분 (스케줄 복원 관련)
        # 스케줄 모드 표기(트리거로 추정)
        self.var_sch_mode.set(self._trigger_mode(job))
        # 교체: _on_tree_dblclick 내 스케줄 복원 블록 전체 교체
        # 스케줄 모드 표기(트리거로 추정) → 프레임 표시 전환 → 필드 초기화 → 모드별 주입
        try:
            t = job.trigger

            # 1) 모드 판정
            mode_guess = self._trigger_mode(job)
            self.var_sch_mode.set(mode_guess)

            # 2) 프레임 표시 상태 먼저 맞춤
            self._on_sched_mode_changed()

            # 3) 모든 스케줄 입력 필드 초기화
            self._clear_sched_fields()

            # 4) 트리거별 값 주입
            if isinstance(t, DateTrigger):
                self.var_sch_mode.set("once")
                self._on_sched_mode_changed()
                run_dt = t.run_date
                if hasattr(self, "ent_once_dt"):
                    self.ent_once_dt.insert(0, run_dt.strftime("%Y-%m-%d %H:%M"))

            elif isinstance(t, IntervalTrigger):
                self.var_sch_mode.set("interval")
                self._on_sched_mode_changed()
                td = t.interval
                total_minutes = int(td.total_seconds() // 60)
                hours = total_minutes // 60
                minutes = total_minutes % 60
                if hasattr(self, "ent_iv_h"): self.ent_iv_h.insert(0, str(hours))
                if hasattr(self, "ent_iv_m"): self.ent_iv_m.insert(0, str(minutes))

            elif isinstance(t, CronTrigger):
                fields = {f.name: f for f in t.fields}

                def _first_token(expr_str: str, default="*"):
                    s = (expr_str or default).strip()
                    if s == "*":
                        return default
                    s = s.split(",")[0]
                    s = s.split("/")[0]
                    s = s.split("-")[0]
                    return s

                hour_s   = _first_token(str(fields.get("hour")))
                minute_s = _first_token(str(fields.get("minute")))
                hh = "00" if hour_s   in ("*", "") else f"{int(hour_s):02d}"
                mm = "00" if minute_s in ("*", "") else f"{int(minute_s):02d}"
                time_val = f"{hh}:{mm}"

                dow_field = fields.get("day_of_week")
                day_field = fields.get("day")
                dow_s  = _first_token(str(dow_field)) if dow_field else "*"
                day_s  = _first_token(str(day_field)) if day_field else "*"

                eng2kor = {"mon":"월","tue":"화","wed":"수","thu":"목","fri":"금","sat":"토","sun":"일"}

                if dow_s not in ("*", ""):
                    # 매주
                    self.var_sch_mode.set("weekly")
                    self._on_sched_mode_changed()
                    if hasattr(self, "cmb_weekday"):
                        self.cmb_weekday.set(eng2kor.get(dow_s.lower(), "월"))
                    if hasattr(self, "ent_weekly_time"):
                        self.ent_weekly_time.insert(0, time_val)

                elif day_s not in ("*", ""):
                    # 매월
                    self.var_sch_mode.set("monthly")
                    self._on_sched_mode_changed()
                    try:
                        d = int(day_s)
                        if hasattr(self, "spin_dom"):
                            self.spin_dom.delete(0, "end"); self.spin_dom.insert(0, str(d))
                    except:
                        pass
                    if hasattr(self, "ent_monthly_time"):
                        self.ent_monthly_time.insert(0, time_val)

                else:
                    # 매일
                    self.var_sch_mode.set("daily")
                    self._on_sched_mode_changed()
                    if hasattr(self, "ent_daily_time"):
                        self.ent_daily_time.insert(0, time_val)

        except Exception as e:
            logger.exception(f"[ERROR] 스케줄 복원 실패: {e}")

        logger.info(f"[INFO] 선택 작업 로드: {item}")


# ---------------- main ----------------
if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    finally:
        try:
            scheduler.shutdown(wait=False)
        except:
            pass
      
