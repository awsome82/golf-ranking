"""
generate_html.py
────────────────────────────────────────────────────────────
data.json → index.html 변환
주간·월간 / 남녀 탭 전환 UI
────────────────────────────────────────────────────────────
"""

import json

with open("data.json", encoding="utf-8") as f:
    d = json.load(f)


# ─────────────────────────────────────────────────────────────
# 랭킹 테이블 렌더
# ─────────────────────────────────────────────────────────────
def render_table(items: list) -> str:
    if not items:
        return (
            "<tr><td colspan='4' class='empty-row'>"
            "이번 기간 기록이 없습니다.</td></tr>"
        )

    MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}
    rows = ""
    for item in items:
        rank   = item["rank"]
        medal  = MEDALS.get(rank, f"<span class='rank-badge'>{rank}</span>")
        score  = item["score"]
        s_cls  = "score-under" if score < 0 else ("score-even" if score == 0 else "score-over")
        s_txt  = f"{score:+d}" if score != 0 else "E"

        rows += f"""
        <tr>
          <td class="td-rank">{medal}</td>
          <td class="td-name">
            <span class="player-name">{item['name']}</span>
            <span class="player-course">{item['course']}</span>
          </td>
          <td class="td-date">{item['date'][5:]}</td>
          <td class="td-score {s_cls}">{s_txt}</td>
        </tr>"""
    return rows


# ─────────────────────────────────────────────────────────────
# 카드 렌더 (성별 라벨 + 테이블)
# ─────────────────────────────────────────────────────────────
def render_card(title: str, icon: str, items: list, card_id: str) -> str:
    return f"""
    <div class="card" id="{card_id}">
      <div class="card-header">
        <span class="card-icon">{icon}</span>
        <span class="card-title">{title}</span>
      </div>
      <table>
        <thead>
          <tr>
            <th style="width:40px"></th>
            <th>이름 / 구장</th>
            <th style="width:52px">날짜</th>
            <th style="width:52px">스코어</th>
          </tr>
        </thead>
        <tbody>
          {render_table(items)}
        </tbody>
      </table>
    </div>"""


week_label  = d["period"]["week_start"][5:] + " 주"
month_label = d["period"]["month_start"][:7]

html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>⛳ 베스트 스코어 TOP 5</title>
  <style>
    /* ── 기본 리셋 ── */
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --green-dark:  #1a5c38;
      --green-main:  #217a4b;
      --green-light: #e8f5ee;
      --gold:        #d4a017;
      --silver:      #8a9ba8;
      --bronze:      #b87333;
      --text-primary: #1a1a1a;
      --text-muted:   #6b7280;
      --border:       #e5e7eb;
      --bg:           #f3f7f4;
      --card-bg:      #ffffff;
      --radius:       14px;
      --shadow:       0 2px 12px rgba(0,0,0,0.07);
    }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text-primary);
      min-height: 100vh;
    }}

    /* ── 헤더 ── */
    header {{
      background: linear-gradient(135deg, var(--green-dark) 0%, var(--green-main) 100%);
      color: #fff;
      padding: 24px 20px 20px;
      text-align: center;
    }}
    header h1 {{
      font-size: 1.45rem;
      font-weight: 700;
      letter-spacing: -0.3px;
    }}
    .header-sub {{
      margin-top: 6px;
      font-size: 0.78rem;
      opacity: 0.75;
    }}

    /* ── 탭 ── */
    .tab-bar {{
      display: flex;
      background: var(--card-bg);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 100;
    }}
    .tab-btn {{
      flex: 1;
      padding: 13px 0;
      text-align: center;
      font-size: 0.88rem;
      font-weight: 600;
      color: var(--text-muted);
      cursor: pointer;
      border: none;
      background: none;
      border-bottom: 3px solid transparent;
      transition: color .2s, border-color .2s;
    }}
    .tab-btn.active {{
      color: var(--green-main);
      border-bottom-color: var(--green-main);
    }}

    /* ── 섹션 ── */
    .section {{ display: none; padding: 16px; }}
    .section.active {{ display: block; }}

    /* ── 기간 배지 ── */
    .period-badge {{
      display: inline-block;
      background: var(--green-light);
      color: var(--green-dark);
      font-size: 0.75rem;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 20px;
      margin-bottom: 12px;
    }}

    /* ── 그리드 ── */
    .grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 14px;
    }}
    @media (min-width: 720px) {{
      .grid {{ grid-template-columns: 1fr 1fr; }}
    }}

    /* ── 카드 ── */
    .card {{
      background: var(--card-bg);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      overflow: hidden;
    }}
    .card-header {{
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 13px 16px;
      border-bottom: 1px solid var(--border);
      background: var(--green-light);
    }}
    .card-icon {{ font-size: 1.1rem; }}
    .card-title {{
      font-size: 0.92rem;
      font-weight: 700;
      color: var(--green-dark);
    }}

    /* ── 테이블 ── */
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    thead th {{
      font-size: 0.7rem;
      color: var(--text-muted);
      font-weight: 500;
      padding: 8px 10px;
      text-align: left;
      border-bottom: 1px solid var(--border);
      text-transform: uppercase;
      letter-spacing: .4px;
    }}
    tbody tr {{
      transition: background .15s;
    }}
    tbody tr:hover {{ background: #f9fbf9; }}
    tbody tr:not(:last-child) td {{ border-bottom: 1px solid var(--border); }}

    td {{ padding: 11px 10px; vertical-align: middle; }}

    .td-rank {{ text-align: center; font-size: 1.15rem; }}
    .rank-badge {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 24px; height: 24px;
      border-radius: 50%;
      background: var(--border);
      font-size: 0.75rem;
      font-weight: 700;
      color: var(--text-muted);
    }}

    .td-name {{ line-height: 1.35; }}
    .player-name  {{ display: block; font-weight: 600; font-size: 0.9rem; }}
    .player-course {{
      display: block;
      font-size: 0.72rem;
      color: var(--text-muted);
      margin-top: 2px;
    }}

    .td-date {{
      font-size: 0.75rem;
      color: var(--text-muted);
      white-space: nowrap;
    }}

    .td-score {{
      text-align: right;
      font-weight: 700;
      font-size: 1rem;
      white-space: nowrap;
    }}
    .score-under {{ color: #dc2626; }}   /* 언더파  */
    .score-even  {{ color: var(--green-main); }}  /* 이븐파  */
    .score-over  {{ color: var(--text-muted); }}  /* 오버파  */

    .empty-row {{
      text-align: center;
      color: var(--text-muted);
      font-size: 0.85rem;
      padding: 28px;
    }}

    /* ── 푸터 ── */
    footer {{
      text-align: center;
      padding: 24px 16px;
      font-size: 0.73rem;
      color: var(--text-muted);
    }}
  </style>
</head>
<body>

<header>
  <h1>⛳ 베스트 스코어 TOP 5</h1>
  <p class="header-sub">전 구장 통합 랭킹 &nbsp;|&nbsp; 업데이트: {d['updated_at']}</p>
</header>

<div class="tab-bar">
  <button class="tab-btn active" onclick="show('weekly', this)">🗓 주간 TOP 5</button>
  <button class="tab-btn"        onclick="show('monthly', this)">📅 월간 TOP 5</button>
</div>

<!-- ── 주간 ── -->
<div id="weekly" class="section active">
  <div class="period-badge">📌 {week_label} ({d['period']['week_start']} ~)</div>
  <div class="grid">
    {render_card("남자 주간 베스트", "🏌️", d['weekly']['M'], "weekly-m")}
    {render_card("여자 주간 베스트", "🏌️‍♀️", d['weekly']['F'], "weekly-f")}
  </div>
</div>

<!-- ── 월간 ── -->
<div id="monthly" class="section">
  <div class="period-badge">📌 {month_label} 월간 ({d['period']['month_start']} ~)</div>
  <div class="grid">
    {render_card("남자 월간 베스트", "🏌️", d['monthly']['M'], "monthly-m")}
    {render_card("여자 월간 베스트", "🏌️‍♀️", d['monthly']['F'], "monthly-f")}
  </div>
</div>

<footer>
  멀리건 사용 라운드 제외 &nbsp;·&nbsp; 동일 선수 최고 기록 1개 반영<br>
  &copy; {d['updated_at'][:4]} Golf Best Score
</footer>

<script>
  function show(id, el) {{
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    el.classList.add('active');
  }}
</script>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ index.html 생성 완료")
