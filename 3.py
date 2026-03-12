### PART 3/4





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
