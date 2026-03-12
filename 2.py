### PART 2/4
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
