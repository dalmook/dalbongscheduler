# -*- coding: utf-8 -*-
import oracledb
import pandas as pd
import numpy as np

# Thick mode (Instant Client 사용)
oracledb.init_oracle_client(lib_dir=r"C:\instantclient")

def _as_set_or_none(lst):
    if not lst: return None
    s = [str(x).strip() for x in lst if str(x).strip() != ""]
    return set(s) if s else None

def filter_and_order_long(df: pd.DataFrame,
                          header_levels, header_orders: dict,
                          merge_cols, merge_orders: dict):
    if df is None or df.empty: return df
    df2 = df.copy()

    # 헤더 레벨 필터
    if header_levels:
        for lvl in header_levels:
            allowed = _as_set_or_none(header_orders.get(lvl, [])) if header_orders else None
            if allowed is not None and lvl in df2.columns:
                df2 = df2[df2[lvl].astype(str).isin(allowed)]

    # 머지축(행) 필터
    if merge_cols:
        for mc in merge_cols:
            allowed = _as_set_or_none(merge_orders.get(mc, [])) if merge_orders else None
            if allowed is not None and mc in df2.columns:
                df2 = df2[df2[mc].astype(str).isin(allowed)]

    # 지정 순서 정렬
    if merge_cols and merge_orders:
        for mc in reversed(merge_cols):
            order = merge_orders.get(mc) or []
            if order and mc in df2.columns:
                rank = {str(v): i for i, v in enumerate(order)}
                df2["_rank_"+mc] = df2[mc].astype(str).map(lambda x: rank.get(x, 10**9))
                df2 = df2.sort_values(by=["_rank_"+mc], kind="mergesort").drop(columns=["_rank_"+mc], errors="ignore")
    return df2

def pivot_long_to_wide(df_long, merge_cols, header_levels, value_col, level_orders=None, delim="|"):
    if not isinstance(df_long, pd.DataFrame) or df_long.empty:
        return pd.DataFrame()
    if value_col not in df_long.columns:
        return df_long.copy()
    if not header_levels:
        cols = [c for c in merge_cols if c in df_long.columns]
        cols += [c for c in df_long.columns if c not in cols]
        return df_long[cols].copy()

    miss = [c for c in header_levels if c not in df_long.columns]
    if miss:
        cols = [c for c in merge_cols if c in df_long.columns]
        cols += [c for c in df_long.columns if c not in cols]
        return df_long[cols].copy()

    piv = df_long.pivot_table(index=merge_cols, columns=header_levels, values=value_col, aggfunc="sum")
    if isinstance(piv.columns, pd.MultiIndex):
        cols = [delim.join([str(x) for x in tpl]) for tpl in piv.columns]
        piv.columns = cols
    else:
        piv.columns = [str(c) for c in piv.columns]
    piv = piv.reset_index()

    if level_orders:
        def header_sort_key(col_label):
            parts = col_label.split(delim)
            keys = []
            for lvl, lbl in zip(header_levels, parts):
                order = level_orders.get(lvl)
                keys.append(order.index(lbl) if (order and lbl in order) else 10**6)
            return tuple(keys)
        left_set = set(merge_cols)
        header_cols = [c for c in piv.columns if c not in left_set]
        header_cols_sorted = sorted(header_cols, key=header_sort_key)
        piv = piv[merge_cols + header_cols_sorted]
    return piv

def sort_wide_rows_by_merge_orders(df_wide: pd.DataFrame, merge_cols, merge_orders: dict):
    if df_wide is None or df_wide.empty or not merge_cols or not merge_orders:
        return df_wide
    df2 = df_wide.copy()
    for mc in reversed(merge_cols):
        if mc not in df2.columns: continue
        order = merge_orders.get(mc) or []
        if order:
            rank = {str(v): i for i, v in enumerate(order)}
            df2["_rank_"+mc] = df2[mc].astype(str).map(lambda x: rank.get(x, 10**9))
            df2 = df2.sort_values(by=["_rank_"+mc], kind="mergesort").drop(columns=["_rank_"+mc], errors="ignore")
    return df2.reset_index(drop=True)

def compute_rowspans(df: pd.DataFrame, merge_cols, no_merge_cols=None):
    no_merge_cols = set(no_merge_cols or [])
    spans = {i: {c: 1 for c in merge_cols} for i in range(len(df))}
    for c in merge_cols:
        if c in no_merge_cols:
            continue  # 병합 해제
        col_idx = df.columns.get_loc(c)
        start = 0
        for i in range(1, len(df) + 1):
            is_boundary = (i == len(df)) or (df.iloc[i, col_idx] != df.iloc[i-1, col_idx])
            if is_boundary:
                glen = i - start
                if glen > 1:
                    spans[start][c] = glen
                    for k in range(start+1, i):
                        spans[k][c] = 0
                else:
                    spans[start][c] = 1
                start = i
    return spans

def split_header_grid(header_cols, header_levels, delim='|'):
    if not header_levels: return []
    parts=[c.split(delim) for c in header_cols]
    max_lv=max((len(p) for p in parts), default=0)
    rows=[]
    for lvl in range(max_lv):
        rows.append([(p[lvl] if lvl<len(p) else '') for p in parts])
    return rows

def collapse_spans_in_header(level_labels_row):
    spans=[]; i=0
    while i<len(level_labels_row):
        j=i+1
        while j<len(level_labels_row) and level_labels_row[j]==level_labels_row[i]: j+=1
        spans.append((level_labels_row[i], j-i)); i=j
    return spans

def fmt_value(v, decimals=0, num_default=None, str_default=''):
    _is_empty = (
        v is None
        or (isinstance(v, float) and pd.isna(v))
        or (isinstance(v, str) and v.strip() == "")
    )
    if decimals is None:
        if _is_empty:
            return str_default
        return str(v)
    if _is_empty:
        if num_default is None:
            return ""
        v = num_default
    try:
        if isinstance(v, str):
            v = v.replace(",", "").strip()
        f = float(v)
        if isinstance(decimals, int):
            if decimals == 0:
                return f"{int(round(f)):,}"
            return f"{f:,.{decimals}f}"
        return str(v)
    except:
        return str_default if _is_empty else str(v)

COMMON_STYLE=(
    "<style>"
    "table.oracle-preview{border-collapse:collapse;font-family:'맑은 고딕','Malgun Gothic','Segoe UI',sans-serif;font-size:12px;}"
    "table.oracle-preview th,table.oracle-preview td{border:1px solid #D1D5DB;}"
    ".chart-wrap{margin:8px 0 16px 0}"
    ".chart-title{font-weight:600;margin-bottom:6px}"
    ".bar-row{display:flex;align-items:center;gap:8px;margin:3px 0}"
    ".bar-label{min-width:120px;white-space:nowrap}"
    ".bar{height:16px;display:inline-block}"
    "</style>"
)

def _eval_color_expr(expr, v, row_dict, col_name, row_index):
    """font_color_expr를 안전하게 평가: v(값), r(행dict), c(컬럼명), i(행index) 사용 가능"""
    SAFE_GLOBALS = {"__builtins__": {}}  # 빌트인 차단
    SAFE_LOCALS = {
        "v": v, "r": row_dict, "c": col_name, "i": row_index,
        "abs": abs, "round": round, "min": min, "max": max, "int": int, "float": float, "str": str
    }
    try:
        res = eval(expr, SAFE_GLOBALS, SAFE_LOCALS)
        return str(res) if res is not None else None
    except Exception:
        return None


def render_html_table(df_wide, merge_cols, header_levels, value_decimals_map, col_styles_map,
                      table_font_size=12, header_bg='#f3f7fc', zebra=True, delim='|',
                      null_num=0, null_str='', chart_html='', row_rules=None, spans=None):
    all_cols=list(df_wide.columns)
    left_cols=[c for c in merge_cols if c in all_cols]
    header_cols=[c for c in all_cols if c not in left_cols]
    levels_rows=split_header_grid(header_cols, header_levels, delim=delim)
    levels_count=len(levels_rows)
    row_rules = row_rules or []
    spans = spans or {}

    def to_int(v,d=None):
        try: return int(v)
        except: return d

    def col_css(c, *, role='value'):
        st=col_styles_map.get(c, {})
        width=to_int(st.get('width'), None)
        if role=='header': align=st.get('header_align') or 'center'
        elif role=='left': align=st.get('value_align') or 'center'
        else: align=st.get('value_align') or ('center' if c not in merge_cols else 'left')
        b_w=to_int(st.get('border_w'),1); b_color=st.get('border_color') or '#D1D5DB'; b_style=st.get('border_style') or 'solid'
        border_css=f'border:{b_w}px {b_style} {b_color};'
        apply_header=bool(st.get('apply_header')); bg=st.get('bg'); fs=to_int(st.get('font'), None); fc=st.get('font_color')
        css=[border_css,'padding:4px;vertical-align:middle;white-space:nowrap;',f'text-align:{align};']
        if width: css.append(f'width:{width}px;')
        if role!='header' or apply_header:
            if bg: css.append(f'background:{bg};')
            if fs: css.append(f'font-size:{fs}px;')
            if fc: css.append(f'color:{fc};')
        return ''.join(css)

    thead_rows=[]
    if levels_count==0:
        cells=[]
        for c in left_cols: cells.append(f'<th style="background:{header_bg};{col_css(c, role="header")}">{c}</th>')
        for c in header_cols: cells.append(f'<th style="background:{header_bg};{col_css(c, role="header")}">{c}</th>')
        thead_rows.append('<tr>' + ''.join(cells) + '</tr>')
    else:
        first_cells=[]
        for c in left_cols:
            first_cells.append(f'<th rowspan="{levels_count}" style="background:{header_bg};{col_css(c, role="header")}">{c}</th>')
        for label, span in collapse_spans_in_header(levels_rows[0]):
            first_cells.append(f'<th colspan="{span}" style="background:{header_bg};{col_css("::header", role="header")}">{label}</th>')
        thead_rows.append('<tr>' + ''.join(first_cells) + '</tr>')
        for lvl in range(1, levels_count):
            row_cells=[]
            for label, span in collapse_spans_in_header(levels_rows[lvl]):
                row_cells.append(f'<th colspan="{span}" style="background:{header_bg};{col_css("::header", role="header")}">{label}</th>')
            thead_rows.append('<tr>' + ''.join(row_cells) + '</tr>')

    # TBODY
    tbody = []
    for i in range(len(df_wide)):
        tds = []
        row_dict = df_wide.iloc[i].to_dict()
        row_bg = None
        for rule in (row_rules or []):
            cond = (rule.get("when") or "").strip()
            try:
                ok = bool(eval(cond, {"__builtins__": {}},
                            {"r": row_dict, "i": i, "str": str, "int": int, "float": float}))
            except Exception:
                ok = False
            if ok and rule.get("bg"):
                row_bg = rule["bg"]
        # ─ 왼쪽(머지) 컬럼들 ─
        for c in left_cols:
            span = spans.get(i, {}).get(c, 1)
            if span > 0:
                val = df_wide.at[i, c]
                txt_left = fmt_value(val, decimals=None, num_default=null_num, str_default=null_str)
                cell_style = col_css(c, role="left")

                # 동적 폰트색(조건부 서식)
                expr = (col_styles_map.get(c, {}) or {}).get("font_color_expr", "")
                if expr:
                    dyn = _eval_color_expr(expr, val, row_dict, c, i)
                    if dyn:
                        cell_style += f"color:{dyn};"

                tds.append(f'<td rowspan="{span}" style="{cell_style}">{txt_left}</td>')

        # ─ 값 컬럼들 ─
        for c in header_cols:
            v = df_wide.at[i, c]
            dec = value_decimals_map.get(c, 0)
            txt = fmt_value(v, decimals=dec, num_default=null_num, str_default=null_str)
            cell_style = col_css(c, role="value")

            # 동적 폰트색(조건부 서식)
            expr = (col_styles_map.get(c, {}) or {}).get("font_color_expr", "")
            if expr:
                dyn = _eval_color_expr(expr, v, row_dict, c, i)
                if dyn:
                    cell_style += f"color:{dyn};"

            # (예시) DR이 '합계'인 행은 바닥 보더를 dotted로
            if str(row_dict.get("DR", "")) == "합계":
                cell_style += "border-bottom-style:dotted;"

            tds.append(f'<td style="{cell_style}">{txt}</td>')

        tr_bg = (row_bg if row_bg is not None
                else ("#fff" if ((i % 2 == 0) or not zebra) else "#fafafa"))
        tbody.append(f'<tr style="background:{tr_bg}">' + "".join(tds) + "</tr>")


    thead_html=''.join(thead_rows); tbody_html=''.join(tbody)
    html=("<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
          + COMMON_STYLE + f"<style>table.oracle-preview{{font-size:{int(table_font_size)}px}}</style>"
          + "</head><body>"
          + (chart_html or "")
          + "<table class='oracle-preview' cellspacing='0' cellpadding='0'>"
          + f"<thead>{thead_html}</thead>"
          + f"<tbody>{tbody_html}</tbody>"
          + "</table></body></html>")
    return html

def filter_df_by_filters(df, filters):
    if df is None or df.empty or not filters: return df
    out=df.copy()
    for col, allowed in (filters or {}).items():
        if not allowed: continue
        if col in out.columns:
            out=out[out[col].astype(str).isin({str(v) for v in allowed})]
    return out


def main(env):
    DSN='swgxpd08-vip.sec.samsung.net:2521/MEMSCM'
    USER=env.get('user') or 'memscm'
    PW  =env.get('pw')   or 'mem01scm'
    MERGE_COLS     = ['MONTH','TYPE','ITEM','SHIPTONAME1']
    NO_MERGE_COLS  = ['SHIPTONAME1']
    HEADER_LEVELS  = ['DD']
    VALUE_COL      = 'QTY'
    LEVEL_ORDERS   = {'DD': ['합계', '1일', '2일', '3일', '4일', '5일', '6일', '7일', '8일', '9일', '10일', '11일', '12일', '13일', '14일', '15일', '16일', '17일', '18일', '19일', '20일', '21일', '22일', '23일', '24일', '25일', '26일', '27일', '28일', '29일', '30일', '31일']}
    MERGE_ORDERS   = {}
    VALUE_DECIMALS = {'ITEM': 0, '1': 0, '2': 0, '3': 0, '4': 0, '5': 0, '6': 0, '8': 0, '1일': 0, '2일': 0, '3일': 0, '4일': 0, '5일': 0, '6일': 0, '8일': 0, '합계': 0}
    COL_STYLES     = {'합계': {'font_color': '', 'header_align': 'center', 'value_align': 'center', 'bg': '#F2F2F2', 'font': None, 'font_color_expr': "'#fff' if float(v)==0 else ''", 'border_w': 1, 'border_color': '', 'border_style': 'solid', 'apply_header': False}}
    TABLE_FONT_SIZE= 12
    HEADER_BG      = '#f3f7fc'
    ZEBRA          = False
    DELIM          = '|'
    NULL_NUM       = None
    NULL_STR       = '-'
    SQL            = """\
SELECT
    TO_CHAR(a.salesdate, 'YYYYMM') month,
    NVL(TO_NUMBER(TO_CHAR(a.salesdate,'DD'))||'일','합계') DD,
    a.siteid,
    a.item,
    B.ATTB05 TYPE,
    a.soldtoparty,
    a.soldtoname,
    A.SHIPTOPARTY,
    A.SHIPTONAME1,
    SUM(a.salesqty) qty,
    SUM(a.usdamount) amt
FROM
    slsiscm.dyn_sales a, SLSISCM.GUI_ITEMATTB B
WHERE
    1 = 1
    AND A.ITEM = B.ITEM (+)
    AND a.siteid = 'HA01-01'
    AND a.salesdate >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), 0)
GROUP BY
    TO_CHAR(a.salesdate, 'YYYYMM'),
    ROLLUP(TO_NUMBER(TO_CHAR(a.salesdate,'DD'))||'일'),
    a.siteid,
    a.item,
    B.ATTB05,
    a.soldtoparty,
    a.soldtoname,
    A.SHIPTOPARTY,
    A.SHIPTONAME1        
ORDER BY
1,2,3,4,5
"""

    with oracledb.connect(user=USER, password=PW, dsn=DSN) as conn:
        df=pd.read_sql(SQL, conn)

    df=df.fillna('')
    df_long=filter_and_order_long(df, HEADER_LEVELS, LEVEL_ORDERS, MERGE_COLS, MERGE_ORDERS)
    df_wide=pivot_long_to_wide(df_long, MERGE_COLS, HEADER_LEVELS, VALUE_COL, level_orders=LEVEL_ORDERS, delim=DELIM)
    df_wide=sort_wide_rows_by_merge_orders(df_wide, MERGE_COLS, MERGE_ORDERS)
    # ─ spans 계산(병합 해제 적용)
    left_cols = [c for c in MERGE_COLS if c in df_wide.columns]
    spans = compute_rowspans(df_wide, left_cols, no_merge_cols=NO_MERGE_COLS) if left_cols else {}

    # filtered_df = df[df['DD'] == '합계']
    # grouped = filtered_df[['DENSITY','ITEM_CODE','DESIGNRULE','VERSION','QTY','EQ']].groupby(['DENSITY','DESIGNRULE', 'VERSION','ITEM_CODE']).sum().reset_index()

    # html_result = ""
    # for _, row in grouped.iterrows():
    #     line = f"""<SPAN style="color:#000000;font-weight:400;orphans:2;font-size:10pt;font-family:돋움, sans-serif;">✔️&nbsp;</SPAN><SPAN style="color:rgb(0, 0, 0);orphans:2;font-size:10pt;font-family:돋움, sans-serif;font-weight:bold;">{row['DESIGNRULE']}_{row['VERSION']}_{row['DENSITY']}_</SPAN><SPAN style="color:rgb(0, 0, 0);font-weight:400;orphans:2;font-size:8pt;font-family:돋움, sans-serif;">{row['ITEM_CODE']}</SPAN><SPAN style="color:rgb(0, 0, 0);font-weight:400;orphans:2;font-size:10pt;font-family:돋움, sans-serif;">&nbsp;</SPAN><SPAN style="color:rgb(0, 0, 0);font-weight:400;orphans:2;font-size:10pt;font-family:돋움, sans-serif;">&nbsp;▫ </SPAN><SPAN style="color:rgb(7, 55, 99);font-weight:bold;orphans:2;font-size:10pt;font-family:돋움, sans-serif;">{row['QTY']:,} 개</SPAN><SPAN style="color:rgb(0, 0, 0);font-weight:400;orphans:2;font-size:10pt;font-family:돋움, sans-serif;"> 입고 ({row['EQ']:,} MEQ)</SPAN><br>"""
    #     html_result += line + "\n"    

    html=render_html_table(df_wide, MERGE_COLS, HEADER_LEVELS, VALUE_DECIMALS, COL_STYLES,
        table_font_size=TABLE_FONT_SIZE, header_bg=HEADER_BG, zebra=ZEBRA, delim=DELIM,
        null_num=NULL_NUM, null_str=NULL_STR,  row_rules=[], spans=spans)
    # html = html_result+ """<hr style="border: none; border-top: 1px solid #ddd; margin: 10px 0;">"""+html    
    return {'html': html}

if __name__=='__main__':
    out=main({})
    with open('output.html','w',encoding='utf-8') as f: f.write(out['html'])
    print('saved: output.html')
