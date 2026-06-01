import json

try:
    with open("data.json", encoding="utf-8") as f:
        d = json.load(f)
except FileNotFoundError:
    print("data.json 파일이 없습니다.")
    exit(1)

period = d.get("period", {})
week_start = period.get("week_start", "2026-01-01")
month_start = period.get("month_start", "2026-01-01")

def render_table(items):
    if not items: 
        return "<tr><td colspan='4' class='empty-row'>기록이 없습니다.</td></tr>"
    
    table_html = ""
    for item in items:
        # 순위 메달 설정
        medal = {1:"🥇", 2:"🥈", 3:"🥉"}.get(item['rank'], f"<span class='rank-badge'>{item['rank']}</span>")
        
        # 스코어 색상 클래스 결정
        sc = item['score']
        score_class = "score-under" if sc < 0 else ("score-even" if sc == 0 else "score-over")
        
        # 날짜 포맷팅 (YYYY-MM-DD -> MM-DD)
        date_display = item['date'][5:] if len(item['date']) >= 10 else item['date']

        table_html += f"""
        <tr>
            <td class="td-rank">{medal}</td>
            <td class="td-name">
                <span class="player-name">{item['name']}</span>
                <span class="player-course">{item['course']}</span>
            </td>
            <td class="td-date">{date_display}</td>
            <td class="td-score {score_class}">{sc:+d}</td>
        </tr>"""
    return table_html

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
            <th style="width:40px; text-align:center;">순위</th>
            <th>이름 / 구장</th>
            <th style="width:55px">날짜</th>
            <th style="width:55px; text-align:right;">스코어</th>
          </tr>
        </thead>
        <tbody>
          {render_table(items)}
        </tbody>
      </table>
    </div>"""

# 레이블 설정
week_label  = week_start[5:] + " 주"
month_label = month_start[:7]

# 💡 f-string 대신 일반 문자열을 사용하여 CSS/JS 중괄호({}) 충돌을 원천 차단합니다.
html_template = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>⛳ 벽동회 스크린 베스트 스코어 TOP 5</title>
  <style>
    /* ── 기본 리셋 ── */
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --green-dark:  #1a5c38;
      --green-main:  #217a4b;
      --green-light: #e8f5ee;
      --text-primary: #1a1a1a;
      --text-muted:   #6b7280;
      --border:       #e5e7eb;
      --bg:           #f3f7f4;
      --card-bg:      #ffffff;
      --radius:       14px;
      --shadow:       0 2px 12px rgba(0,0,0,0.07);
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text-primary);
      line-height: 1.5;
    }

    header {
      background: linear-gradient(135deg, var(--green-dark) 0%, var(--green-main) 100%);
      color: #fff;
      padding: 24px 20px;
      text-align: center;
    }
    header h1 { font-size: 1.4rem; font-weight: 700; }
    .header-sub { margin-top: 6px; font-size: 0.75rem; opacity: 0.8; }

    .tab-bar {
      display: flex;
      background: var(--card-bg);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .tab-btn {
      flex: 1;
      padding: 14px 0;
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--text-muted);
      cursor: pointer;
      border: none;
      background: none;
      border-bottom: 3px solid transparent;
    }
    .tab-btn.active {
      color: var(--green-main);
      border-bottom-color: var(--green-main);
    }

    .section { display: none; padding: 16px; }
    .section.active { display: block; }

    .period-badge {
      display: inline-block;
      background: var(--green-light);
      color: var(--green-dark);
      font-size: 0.7rem;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 20px;
      margin-bottom: 12px;
    }

    .grid { display: grid; grid-template-columns: 1fr; gap: 16px; }
    @media (min-width: 720px) { .grid { grid-template-columns: 1fr 1fr; } }

    .card { background: var(--card-bg); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; }
    .card-header { display: flex; align-items: center; gap: 8px; padding: 12px 16px; background: var(--green-light); border-bottom: 1px solid var(--border); }
    .card-title { font-size: 0.9rem; font-weight: 700; color: var(--green-dark); }

    table { width: 100%; border-collapse: collapse; }
    thead th { font-size: 0.65rem; color: var(--text-muted); padding: 8px 12px; border-bottom: 1px solid var(--border); text-align: left; }
    td { padding: 10px 12px; border-bottom: 1px solid #f9f9f9; }

    .td-rank { text-align: center; width: 45px; }
    .rank-badge { display: inline-block; width: 20px; height: 20px; background: #eee; border-radius: 50%; font-size: 0.7rem; line-height: 20px; font-weight: 700; color: #777; }

    .player-name { display: block; font-weight: 600; font-size: 0.88rem; }
    .player-course { display: block; font-size: 0.7rem; color: var(--text-muted); }

    .td-date { font-size: 0.75rem; color: var(--text-muted); }
    .td-score { text-align: right; font-weight: 700; font-size: 0.95rem; }
    .score-under { color: #dc2626; }
    .score-even  { color: var(--green-main); }
    .score-over  { color: var(--text-muted); }

    .empty-row { text-align: center; color: var(--text-muted); padding: 30px; font-size: 0.85rem; }

    footer { text-align: center; padding: 30px 20px; font-size: 0.7rem; color: var(--text-muted); line-height: 1.6; }
  </style>
</head>
<body>

<header>
  <h1>⛳ 벽동회 스크린 베스트 스코어 TOP 5</h1>
  <p class="header-sub">전 구장 통합 랭킹 &nbsp;|&nbsp; 업데이트: __UPDATED_AT__</p>
</header>

<div class="tab-bar">
  <button class="tab-btn active" onclick="show('weekly', this)">🗓 주간 TOP 5</button>
  <button class="tab-btn"         onclick="show('monthly', this)">📅 월간 TOP 5</button>
</div>

<div id="weekly" class="section active">
  <div class="period-badge">📌 __WEEK_LABEL__ (__WEEK_START__ ~)</div>
  <div class="grid">
    __WEEKLY_M_CARD__
    __WEEKLY_F_CARD__
  </div>
</div>

<div id="monthly" class="section">
  <div class="period-badge">📌 __MONTH_LABEL__ 월간 (__MONTH_START__ ~)</div>
  <div class="grid">
    __MONTHLY_M_CARD__
    __MONTHLY_F_CARD__
  </div>
</div>

<footer>
  멀리건 사용 라운드 제외 &nbsp;·&nbsp; 동일 선수 최고 기록 1개만 반영<br>
  &copy; __YEAR__ Golf Best Score
</footer>

<script>
  function show(id, el) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    el.classList.add('active');
  }
</script>
</body>
</html>"""

# ── 안전한 치환(Replace) 작업 ──
html = html_template.replace("__UPDATED_AT__", d['updated_at'])
html = html.replace("__WEEK_LABEL__", week_label)
html = html.replace("__WEEK_START__", week_start)
html = html.replace("__MONTH_LABEL__", month_label)
html = html.replace("__MONTH_START__", month_start)
html = html.replace("__YEAR__", d['updated_at'][:4])

html = html.replace("__WEEKLY_M_CARD__", render_card("남자 주간 베스트", "🏌️", d['weekly']['M'], "weekly-m"))
html = html.replace("__WEEKLY_F_CARD__", render_card("여자 주간 베스트", "🏌️‍♀️", d['weekly']['F'], "weekly-f"))
html = html.replace("__MONTHLY_M_CARD__", render_card("남자 월간 베스트", "🏌️", d['monthly']['M'], "monthly-m"))
html = html.replace("__MONTHLY_F_CARD__", render_card("여자 월간 베스트", "🏌️‍♀️", d['monthly']['F'], "monthly-f"))

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ index.html 생성 완료")
