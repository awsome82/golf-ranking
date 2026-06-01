import json

try:
    with open("data.json", encoding="utf-8") as f:
        d = json.load(f)
except FileNotFoundError:
    print("data.json 파일이 없습니다."); exit(1)

period = d.get("period", {})

def render_table(items):
    if not items: return "<tr><td colspan='4' class='empty-row'>이번 기간 기록이 없습니다.</td></tr>"
    table_html = ""
    for item in items:
        medal = {1:"🥇", 2:"🥈", 3:"🥉"}.get(item['rank'], f"<span class='rank-badge'>{item['rank']}</span>")
        sc = item['score']
        score_class = "score-under" if sc < 0 else ("score-even" if sc == 0 else "score-over")
        date_display = item['date'][5:] # MM-DD 만 표시
        table_html += f"""
        <tr>
            <td class="td-rank">{medal}</td>
            <td class="td-name"><span class="player-name">{item['name']}</span><span class="player-course">{item['course']}</span></td>
            <td class="td-date">{date_display}</td>
            <td class="td-score {score_class}">{sc:+d}</td>
        </tr>"""
    return table_html

def render_card(title: str, icon: str, items: list, card_id: str) -> str:
    return f"""
    <div class="card" id="{card_id}">
      <div class="card-header"><span class="card-icon">{icon}</span><span class="card-title">{title}</span></div>
      <table>
        <thead><tr><th style="width:40px; text-align:center;">순위</th><th>이름 / 구장</th><th style="width:55px">날짜</th><th style="width:55px; text-align:right;">스코어</th></tr></thead>
        <tbody>{render_table(items)}</tbody>
      </table>
    </div>"""

# 기간 레이블 생성 (예: 06.01 ~ 06.07)
week_range = f"{period['week_start'][5:].replace('-', '.')} ~ {period['week_end'][5:].replace('-', '.')}"
month_range = f"{period['month_start'][:7].replace('-', '.')}"

html_template = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>⛳ 벽동회 스크린 골프 베스트 스코어</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root { --green-dark: #1a5c38; --green-main: #217a4b; --green-light: #e8f5ee; --text-muted: #6b7280; --border: #e5e7eb; --bg: #f3f7f4; --card-bg: #ffffff; }
    body { font-family: -apple-system, sans-serif; background: var(--bg); color: #1a1a1a; line-height: 1.5; }
    header { background: linear-gradient(135deg, var(--green-dark), var(--green-main)); color: #fff; padding: 25px 20px; text-align: center; }
    .tab-bar { display: flex; background: var(--card-bg); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 100; }
    .tab-btn { flex: 1; padding: 15px 0; font-size: 0.85rem; font-weight: 600; color: var(--text-muted); cursor: pointer; border: none; background: none; border-bottom: 3px solid transparent; }
    .tab-btn.active { color: var(--green-main); border-bottom-color: var(--green-main); }
    .section { display: none; padding: 16px; }
    .section.active { display: block; }
    .period-badge { display: inline-block; background: var(--green-light); color: var(--green-dark); font-size: 0.75rem; font-weight: 700; padding: 5px 12px; border-radius: 20px; margin-bottom: 15px; }
    .grid { display: grid; grid-template-columns: 1fr; gap: 16px; }
    @media (min-width: 720px) { .grid { grid-template-columns: 1fr 1fr; } }
    .card { background: var(--card-bg); border-radius: 14px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); overflow: hidden; }
    .card-header { display: flex; align-items: center; gap: 8px; padding: 12px 16px; background: var(--green-light); border-bottom: 1px solid var(--border); }
    .card-title { font-size: 0.9rem; font-weight: 700; color: var(--green-dark); }
    table { width: 100%; border-collapse: collapse; }
    thead th { font-size: 0.65rem; color: var(--text-muted); padding: 10px 12px; border-bottom: 1px solid var(--border); text-align: left; }
    td { padding: 12px; border-bottom: 1px solid #f9f9f9; }
    .td-rank { text-align: center; width: 45px; }
    .rank-badge { display: inline-block; width: 22px; height: 22px; background: #eee; border-radius: 50%; font-size: 0.7rem; line-height: 22px; font-weight: 700; color: #777; }
    .player-name { display: block; font-weight: 600; font-size: 0.9rem; }
    .player-course { display: block; font-size: 0.75rem; color: var(--text-muted); }
    .td-date { font-size: 0.75rem; color: var(--text-muted); }
    .td-score { text-align: right; font-weight: 700; font-size: 1rem; }
    .score-under { color: #dc2626; }
    .score-even { color: var(--green-main); }
    .empty-row { text-align: center; color: var(--text-muted); padding: 40px; font-size: 0.85rem; }
    footer { text-align: center; padding: 40px 20px; font-size: 0.75rem; color: var(--text-muted); }
  </style>
</head>
<body>
<header>
  <h1 style="font-size:1.4rem;">⛳ 벽동회 스크린 골프 베스트 스코어</h1>
  <p style="font-size:0.75rem; opacity:0.8; margin-top:5px;">전 구장 통합 랭킹 &nbsp;|&nbsp; 업데이트: __UPDATED_AT__</p>
</header>
<div class="tab-bar">
  <button class="tab-btn active" onclick="show('weekly', this)">🗓 주간 TOP 5</button>
  <button class="tab-btn"         onclick="show('monthly', this)">📅 월간 TOP 5</button>
</div>
<div id="weekly" class="section active">
  <div class="period-badge">📌 주간: __WEEK_RANGE__</div>
  <div class="grid">__WEEKLY_M_CARD____WEEKLY_F_CARD__</div>
</div>
<div id="monthly" class="section">
  <div class="period-badge">📌 월간: __MONTH_RANGE__</div>
  <div class="grid">__MONTHLY_M_CARD____MONTHLY_F_CARD__</div>
</div>
<footer>
  &copy; __YEAR__ Golf Best Score  ·  동일인 최고기록 1개만 반영
</footer>
<script>
  function show(id, el) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    el.classList.add('active');
  }
</script>
</body></html>"""

html = html_template.replace("__UPDATED_AT__", d['updated_at'])
html = html.replace("__WEEK_RANGE__", week_range)
html = html.replace("__MONTH_RANGE__", month_range)
html = html.replace("__YEAR__", d['updated_at'][:4])
html = html.replace("__WEEKLY_M_CARD__", render_card("남자 주간 베스트", "🏌️", d['weekly']['M'], "weekly-m"))
html = html.replace("__WEEKLY_F_CARD__", render_card("여자 주간 베스트", "🏌️‍♀️", d['weekly']['F'], "weekly-f"))
html = html.replace("__MONTHLY_M_CARD__", render_card("남자 월간 베스트", "🏌️", d['monthly']['M'], "monthly-m"))
html = html.replace("__MONTHLY_F_CARD__", render_card("여자 월간 베스트", "🏌️‍♀️", d['monthly']['F'], "monthly-f"))

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
print("✅ index.html 생성 완료")
