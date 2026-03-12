### PART 1/4
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
