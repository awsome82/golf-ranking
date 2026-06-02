import json

try:
    with open("data.json", encoding="utf-8") as f:
        d = json.load(f)
except FileNotFoundError:
    print("data.json 없음"); exit(1)

def render_table(items):
    if not items: return "<tr><td colspan='4' class='empty-row'>기록이 없습니다.</td></tr>"
    html = ""
    for item in items:
        medal = {1:"🥇", 2:"🥈", 3:"🥉"}.get(item['rank'], f"<span class='rank-badge'>{item['rank']}</span>")
        sc = int(item['score'])
        score_class = "score-under" if sc < 0 else ("score-even" if sc == 0 else "score-over")
        score_display = f"{sc:+d}" if sc != 0 else "E"
        html += f"""
        <tr>
            <td class="td-rank">{medal}</td>
            <td class="td-name"><span class="player-name">{item['name']}</span><span class="player-course">{item['course']}</span></td>
            <td class="td-date">{item['date'][5:]}</td>
            <td class="td-score {score_class}">{score_display}</td>
        </tr>"""
    return html

def render_card(title, icon, items, card_id):
    return f"""
    <div class="card" id="{card_id}">
      <div class="card-header"><span class="card-icon">{icon}</span><span class="card-title">{title}</span></div>
      <table>
        <thead><tr><th style="width:45px;text-align:center">순위</th><th>이름/구장</th><th style="width:55px">날짜</th><th style="width:55px;text-align:right">스코어</th></tr></thead>
        <tbody>{render_table(items)}</tbody>
      </table>
    </div>"""

html_template = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>⛳ 골프 랭킹</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, sans-serif; background: #f3f7f4; color: #1a1a1a; padding-bottom: 40px; }
    header { background: linear-gradient(135deg, #1a5c38, #217a4b); color: #fff; padding: 25px 20px; text-align: center; }
    .tab-bar { display: flex; background: #fff; border-bottom: 1px solid #e5e7eb; position: sticky; top: 0; z-index: 100; }
    .tab-btn { flex: 1; padding: 15px 0; font-size: 0.85rem; font-weight: 600; color: #6b7280; cursor: pointer; border: none; background: none; border-bottom: 3px solid transparent; }
    .tab-btn.active { color: #217a4b; border-bottom-color: #217a4b; }
    .section { display: none; padding: 16px; }
    .section.active { display: block; }
    .grid { display: grid; grid-template-columns: 1fr; gap: 16px; }
    @media (min-width: 720px) { .grid { grid-template-columns: 1fr 1fr; } }
    .card { background: #fff; border-radius: 14px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); overflow: hidden; }
    .card-header { padding: 12px 16px; background: #e8f5ee; border-bottom: 1px solid #e5e7eb; font-weight: 700; color: #1a5c38; }
    table { width: 100%; border-collapse: collapse; }
    th { font-size: 0.65rem; color: #6b7280; padding: 10px 12px; border-bottom: 1px solid #e5e7eb; text-align: left; }
    td { padding: 12px; border-bottom: 1px solid #f9f9f9; font-size: 0.9rem; }
    .td-rank { text-align: center; width: 45px; }
    .rank-badge { display: inline-block; width: 22px; height: 22px; background: #eee; border-radius: 50%; font-size: 0.7rem; line-height: 22px; font-weight: 700; color: #777; }
    .player-course { display: block; font-size: 0.75rem; color: #6b7280; }
    .td-date { font-size: 0.75rem; color: #6b7280; }
    .td-score { text-align: right; font-weight: 700; }
    .score-under { color: #dc2626; }
    .score-even { color: #217a4b; }
    .empty-row { text-align: center; color: #6b7280; padding: 40px; }
  </style>
</head>
<body>
<header><h1>⛳ 골프 베스트 스코어</h1><p style="font-size:0.75rem;opacity:0.8;margin-top:5px;">업데이트: __UPDATED_AT__</p></header>
<div class="tab-bar">
  <button class="tab-btn active" onclick="show('weekly', this)">🗓 주간 TOP 5</button>
  <button class="tab-btn" onclick="show('monthly', this)">📅 월간 TOP 5</button>
</div>
<div id="weekly" class="section active">
  <div style="font-size:0.75rem;padding:10px;font-weight:700">📌 기간: __WEEK_RANGE__</div>
  <div class="grid">__WEEKLY_M____WEEKLY_F__</div>
</div>
<div id="monthly" class="section">
  <div style="font-size:0.75rem;padding:10px;font-weight:700">📌 기간: __MONTH_RANGE__</div>
  <div class="grid">__MONTHLY_M____MONTHLY_F__</div>
</div>
<script>
  function show(id, el) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(id).classList.add('active'); el.classList.add('active');
  }
</script>
</body></html>"""

p = d['period']
html = html_template.replace("__UPDATED_AT__", d['updated_at'])\
    .replace("__WEEK_RANGE__", f"{p['week_start']} ~ {p['week_end']}")\
    .replace("__MONTH_RANGE__", f"{p['month_start'][:7]}")\
    .replace("__WEEKLY_M__", render_card("남자 주간", "🏌️", d['weekly']['M'], "wm"))\
    .replace("__WEEKLY_F__", render_card("여자 주간", "🏌️‍♀️", d['weekly']['F'], "wf"))\
    .replace("__MONTHLY_M__", render_card("남자 월간", "🏌️", d['monthly']['M'], "mm"))\
    .replace("__MONTHLY_F__", render_card("여자 월간", "🏌️‍♀️", d['monthly']['F'], "mf"))

with open("index.html", "w", encoding="utf-8") as f: f.write(html)
