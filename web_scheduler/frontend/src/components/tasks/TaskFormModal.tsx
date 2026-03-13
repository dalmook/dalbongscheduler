import { useEffect, useState } from "react";
import type { Task, TaskCreatePayload } from "../../types/task";

interface Props {
  open: boolean;
  initial?: Task | null;
  onClose: () => void;
  onSubmit: (payload: TaskCreatePayload) => Promise<void>;
}

const DEFAULT_PAYLOAD: TaskCreatePayload = {
  name: "",
  description: "",
  task_type: "python",
  schedule_type: "manual",
  is_enabled: true,
  timezone: "Asia/Seoul",
  python_code: "",
  sql_code: "",
  html_template: "",
  params_json: "",
  output_format: "json",
};

type ScheduleUI = "manual" | "daily" | "weekly" | "monthly" | "interval" | "custom";

function TaskFormModal({ open, initial, onClose, onSubmit }: Props) {
  const [form, setForm] = useState<TaskCreatePayload>(DEFAULT_PAYLOAD);
  const [error, setError] = useState("");

  const [scheduleUi, setScheduleUi] = useState<ScheduleUI>("manual");
  const [timeHHMM, setTimeHHMM] = useState("09:00");
  const [weeklyDay, setWeeklyDay] = useState("mon");
  const [monthlyDay, setMonthlyDay] = useState(1);

  const [mailSend, setMailSend] = useState(false);
  const [mailSubject, setMailSubject] = useState("");
  const [mailRecipients, setMailRecipients] = useState("");

  useEffect(() => {
    if (initial) {
      const next: TaskCreatePayload = {
        ...DEFAULT_PAYLOAD,
        ...initial,
        description: initial.description ?? "",
        cron_expr: initial.cron_expr ?? "",
        interval_seconds: initial.interval_seconds ?? undefined,
        timezone: initial.timezone ?? "Asia/Seoul",
        python_code: initial.python_code ?? "",
        sql_code: initial.sql_code ?? "",
        html_template: initial.html_template ?? "",
        params_json: initial.params_json ?? "",
        output_format: initial.output_format ?? "json",
      };
      setForm(next);

      // mail options from params_json
      try {
        const p = next.params_json ? JSON.parse(next.params_json) : {};
        setMailSend(Boolean(p.mail_send));
        setMailSubject(typeof p.mail_subject === "string" ? p.mail_subject : "");
        setMailRecipients(typeof p.mail_recipients === "string" ? p.mail_recipients : "");
      } catch {
        setMailSend(false);
        setMailSubject("");
        setMailRecipients("");
      }

      if (next.schedule_type === "interval") {
        setScheduleUi("interval");
      } else if (next.schedule_type === "cron") {
        const c = (next.cron_expr ?? "").trim();
        const m = c.match(/^(\d{1,2})\s+(\d{1,2})\s+\*\s+\*\s+\*$/);
        const w = c.match(/^(\d{1,2})\s+(\d{1,2})\s+\*\s+\*\s+([a-z,0-6]+)$/i);
        const mo = c.match(/^(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+\*\s+\*$/);
        if (m) {
          setScheduleUi("daily");
          setTimeHHMM(`${String(Number(m[2])).padStart(2, "0")}:${String(Number(m[1])).padStart(2, "0")}`);
        } else if (w) {
          setScheduleUi("weekly");
          setWeeklyDay(String(w[3]).split(",")[0].toLowerCase());
          setTimeHHMM(`${String(Number(w[2])).padStart(2, "0")}:${String(Number(w[1])).padStart(2, "0")}`);
        } else if (mo) {
          setScheduleUi("monthly");
          setMonthlyDay(Number(mo[3]));
          setTimeHHMM(`${String(Number(mo[2])).padStart(2, "0")}:${String(Number(mo[1])).padStart(2, "0")}`);
        } else {
          // 기존 cron 표현이 단순 daily/weekly/monthly로 변환 불가하면 custom으로 유지
          setScheduleUi("custom");
        }
      } else {
        setScheduleUi("manual");
      }
    } else {
      setForm(DEFAULT_PAYLOAD);
      setScheduleUi("manual");
      setTimeHHMM("09:00");
      setWeeklyDay("mon");
      setMonthlyDay(1);
      setMailSend(false);
      setMailSubject("");
      setMailRecipients("");
    }
    setError("");
  }, [initial, open]);

  if (!open) return null;

  const toCron = (hhmm: string, mode: ScheduleUI) => {
    const [hh, mm] = hhmm.split(":").map((x) => Number(x || 0));
    if (mode === "daily") return `${mm} ${hh} * * *`;
    if (mode === "weekly") return `${mm} ${hh} * * ${weeklyDay}`;
    if (mode === "monthly") return `${mm} ${hh} ${monthlyDay} * *`;
    return "";
  };

  const validate = (payload: TaskCreatePayload) => {
    if (!payload.name.trim()) return "작업 이름은 필수입니다.";
    if (payload.schedule_type === "cron" && !payload.cron_expr?.trim()) return "반복 시간 설정이 필요합니다.";
    if (payload.schedule_type === "interval" && (!payload.interval_seconds || payload.interval_seconds <= 0)) {
      return "간격(초)을 입력하세요.";
    }
    if (payload.params_json?.trim()) {
      try {
        JSON.parse(payload.params_json);
      } catch {
        return "params_json은 유효한 JSON이어야 합니다.";
      }
    }
    return "";
  };

  const submit = async () => {
    const payload: TaskCreatePayload = { ...form };

    if (scheduleUi === "manual") {
      payload.schedule_type = "manual";
      payload.cron_expr = undefined;
      payload.interval_seconds = undefined;
    } else if (scheduleUi === "interval") {
      payload.schedule_type = "interval";
      payload.cron_expr = undefined;
      payload.interval_seconds = payload.interval_seconds ?? 300;
    } else if (scheduleUi === "custom") {
      payload.schedule_type = "cron";
      payload.cron_expr = payload.cron_expr ?? "";
      payload.interval_seconds = undefined;
    } else {
      payload.schedule_type = "cron";
      payload.cron_expr = toCron(timeHHMM, scheduleUi);
      payload.interval_seconds = undefined;
    }

    // merge advanced params + mail options
    let baseParams: Record<string, unknown> = {};
    try {
      baseParams = payload.params_json?.trim() ? JSON.parse(payload.params_json) : {};
      if (typeof baseParams !== "object" || Array.isArray(baseParams)) baseParams = {};
    } catch {
      baseParams = {};
    }
    baseParams.mail_send = mailSend;
    baseParams.mail_subject = mailSubject;
    baseParams.mail_recipients = mailRecipients;
    payload.params_json = JSON.stringify(baseParams, null, 2);

    const msg = validate(payload);
    if (msg) {
      setError(msg);
      return;
    }
    await onSubmit(payload);
  };

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h3>{initial ? "작업 수정" : "작업 생성"}</h3>
        {error && <div className="state error">{error}</div>}

        <div className="grid-2">
          <input className="input" placeholder="작업 이름" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input className="input" placeholder="설명" value={form.description ?? ""} onChange={(e) => setForm({ ...form, description: e.target.value })} />

          <select className="input" value={form.task_type} onChange={(e) => setForm({ ...form, task_type: e.target.value as TaskCreatePayload["task_type"] })}>
            <option value="python">파이썬</option>
            <option value="sql">SQL</option>
            <option value="html">HTML</option>
          </select>

          <select className="input" value={scheduleUi} onChange={(e) => setScheduleUi(e.target.value as ScheduleUI)}>
            <option value="manual">수동 실행</option>
            <option value="daily">매일</option>
            <option value="weekly">매주</option>
            <option value="monthly">매월</option>
            <option value="interval">간격(초)</option>
            <option value="custom">사용자 지정(CRON)</option>
          </select>

          {(scheduleUi === "daily" || scheduleUi === "weekly" || scheduleUi === "monthly") && (
            <input className="input" placeholder="시간(HH:MM)" value={timeHHMM} onChange={(e) => setTimeHHMM(e.target.value)} />
          )}

          {scheduleUi === "weekly" && (
            <select className="input" value={weeklyDay} onChange={(e) => setWeeklyDay(e.target.value)}>
              <option value="mon">월</option>
              <option value="tue">화</option>
              <option value="wed">수</option>
              <option value="thu">목</option>
              <option value="fri">금</option>
              <option value="sat">토</option>
              <option value="sun">일</option>
            </select>
          )}

          {scheduleUi === "monthly" && (
            <input
              className="input"
              placeholder="매월 일자(1~31)"
              type="number"
              min={1}
              max={31}
              value={monthlyDay}
              onChange={(e) => setMonthlyDay(Number(e.target.value || 1))}
            />
          )}

          {scheduleUi === "interval" && (
            <input className="input" placeholder="간격(초)" type="number" value={form.interval_seconds ?? ""} onChange={(e) => setForm({ ...form, interval_seconds: Number(e.target.value) })} />
          )}

          {scheduleUi === "custom" && (
            <input className="input" placeholder="CRON 표현식 (예: 20 17 * * 1,3,5)" value={form.cron_expr ?? ""} onChange={(e) => setForm({ ...form, cron_expr: e.target.value })} />
          )}

          <select className="input" value={form.output_format ?? "json"} onChange={(e) => setForm({ ...form, output_format: e.target.value })}>
            <option value="json">json</option>
            <option value="text">text</option>
            <option value="html">html</option>
            <option value="csv">csv</option>
          </select>

          <label className="check">
            <input type="checkbox" checked={form.is_enabled} onChange={(e) => setForm({ ...form, is_enabled: e.target.checked })} /> 사용
          </label>
        </div>

        <div className="card" style={{ margin: "8px 0" }}>
          <h4>메일 전송 옵션</h4>
          <label className="check">
            <input type="checkbox" checked={mailSend} onChange={(e) => setMailSend(e.target.checked)} />
            실행 성공 시 메일 전송
          </label>
          <input className="input" placeholder="메일 제목 템플릿 (예: [{md}] 출하 현황)" value={mailSubject} onChange={(e) => setMailSubject(e.target.value)} />
          <input className="input" placeholder="수신자 (예: sungmook.cho, user2)" value={mailRecipients} onChange={(e) => setMailRecipients(e.target.value)} />
        </div>

        <textarea
          className="textarea"
          placeholder='추가 params_json (예: {"input_paths":["/path/a.xlsx"],"python_blocks":[{"title":"블록1","code":"RESULT_HTML=\"<h3>ok</h3>\""}],"sql_attachment_blocks":[{"title":"첨부1","sql":"SELECT 1 AS ok"}]})'
          value={form.params_json ?? ""}
          onChange={(e) => setForm({ ...form, params_json: e.target.value })}
        />

        {form.task_type === "python" && <textarea className="textarea code" placeholder="파이썬 코드" value={form.python_code ?? ""} onChange={(e) => setForm({ ...form, python_code: e.target.value })} />}
        {(form.task_type === "python" || form.task_type === "sql") && (
          <textarea className="textarea code" placeholder={form.task_type === "python" ? "첨부 엑셀용 SQL (선택)" : "SQL 문"} value={form.sql_code ?? ""} onChange={(e) => setForm({ ...form, sql_code: e.target.value })} />
        )}
        {form.task_type === "html" && <textarea className="textarea code" placeholder="HTML 템플릿" value={form.html_template ?? ""} onChange={(e) => setForm({ ...form, html_template: e.target.value })} />}

        <div className="row right">
          <button className="btn" onClick={onClose}>닫기</button>
          <button className="btn primary" onClick={submit}>저장</button>
        </div>
      </div>
    </div>
  );
}

export default TaskFormModal;
