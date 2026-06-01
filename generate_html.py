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
    
    html = ""
    for item in items:
        # 순위 메달 설정
        medal = {1:"🥇", 2:"🥈", 3:"🥉"}.get(item['rank'], f"<span class='rank-badge'>{item['rank']}</span>")
        
        # 스코어 색상 클래스 결정
        sc = item['score']
        score_class = "score-under" if sc < 0 else ("score-even" if sc == 0 else "score-over")
        
        # 날짜 포맷팅 (YYYY-MM-DD -> MM-DD)
        date_display = item['date'][5:] if len(item['date']) >= 10 else item['date']

        html += f"""
        <tr>
            <td class="td-rank">{medal}</td>
            <td class="td-name">
                <span class="player-name">{item['name']}</span>
                <span class="player-course">{item['course']}</span>
            </td>
            <td class="td-date">{date_display}</td>
            <td class="td-score {score_class}">{sc:+d}</td>
        </tr>"""
    return html

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
      line-height: 1.5;
    }}

    header {{
      background: linear-gradient(135deg, var(--green-dark) 0%, var(--green-main) 100%);
      color: #fff;
      padding: 24px 20px;
      text-align: center;
    }}
    header h1 {{ font-size: 1.4rem; font-weight: 700; }}
    .header-sub {{ margin-top: 6px; font-size: 0.75rem; opacity: 0.8; }}

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
      padding: 14px 0;
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--text-muted);
      cursor: pointer;
      border: none;
      background: none;
      border-bottom: 3px solid transparent;
    }}
    .tab-btn.active {{
      color: var(--green-main);
      border-bottom-color: var(--green-main);
    }}

    .section {{ display: none; padding: 16px; }}
    .section.active {{ display: block; }}

    .period-badge {{
      display: inline-block;
      background: var(--green-light);
      color: var(--green-dark);
      font-size: 0.7rem;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 20px;
      margin-bottom: 12px;
    }}

    .grid {{ display: grid; grid-template-columns: 1fr; gap: 16px; }}
    @media (min-width: 720px) {{ .grid {{ grid-template-columns: 1fr 1fr; }} }}

    .card {{ background: var(--card-bg); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; }}
    .card-header {{ display: flex; align-items: center; gap: 8px; padding: 12px 16px; background: var(--green-light); border-bottom: 1px solid var(--border); }}
    .card-title {{ font-size: 0.9rem; font-weight: 700; color: var(--green-dark); }}

    table {{ width: 100%; border-collapse: collapse; }}
    thead th {{ font-size: 0.65rem; color: var(--text-muted); padding: 8px 12px; border-bottom: 1px solid var(--border); text-align: left; }}
    td {{ padding: 10px 12px; border-bottom: 1pximport json

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
    
    html = ""
    for item in items:
        # 순위 메달 설정
        medal = {1:"🥇", 2:"🥈", 3:"🥉"}.get(item['rank'], f"<span class='rank-badge'>{item['rank']}</span>")
        
        # 스코어 색상 클래스 결정
        sc = item['score']
        score_class = "score-under" if sc < 0 else ("score-even" if sc == 0 else "score-over")
        
        # 날짜 포맷팅 (YYYY-MM-DD -> MM-DD)
        date_display = item['date'][5:] if len(item['date']) >= 10 else item['date']

        html += f"""
        <tr>
            <td class="td-rank">{medal}</td>
            <td class="td-name">
                <span class="player-name">{item['name']}</span>
                <span class="player-course">{item['course']}</span>
            </td>
            <td class="td-date">{date_display}</td>
            <td class="td-score {score_class}">{sc:+d}</td>
        </tr>"""
    return html

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
      line-height: 1.5;
    }}

    header {{
      background: linear-gradient(135deg, var(--green-dark) 0%, var(--green-main) 100%);
      color: #fff;
      padding: 24px 20px;
      text-align: center;
    }}
    header h1 {{ font-size: 1.4rem; font-weight: 700; }}
    .header-sub {{ margin-top: 6px; font-size: 0.75rem; opacity: 0.8; }}

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
      padding: 14px 0;
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--text-muted);
      cursor: pointer;
      border: none;
      background: none;
      border-bottom: 3px solid transparent;
    }}
    .tab-btn.active {{
      color: var(--green-main);
      border-bottom-color: var(--green-main);
    }}

    .section {{ display: none; padding: 16px; }}
    .section.active {{ display: block; }}

    .period-badge {{
      display: inline-block;
      background: var(--green-light);
      color: var(--green-dark);
      font-size: 0.7rem;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 20px;
      margin-bottom: 12px;
    }}

    .grid {{ display: grid; grid-template-columns: 1fr; gap: 16px; }}
    @media (min-width: 720px) {{ .grid {{ grid-template-columns: 1fr 1fr; }} }}

    .card {{ background: var(--card-bg); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; }}
    .card-header {{ display: flex; align-items: center; gap: 8px; padding: 12px 16px; background: var(--green-light); border-bottom: 1px solid var(--border); }}
    .card-title {{ font-size: 0.9rem; font-weight: 700; color: var(--green-dark); }}

    table {{ width: 100%; border-collapse: collapse; }}
    thead th {{ font-size: 0.65rem; color: var(--text-muted); padding: 8px 12px; border-bottom: 1px solid var(--border); text-align: left; }}
    td {{ padding: 10px 12px; border-bottom: 1px
