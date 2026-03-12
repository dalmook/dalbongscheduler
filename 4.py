### PART 4/4
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

