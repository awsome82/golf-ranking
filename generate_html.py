import json

with open("data.json", encoding="utf-8") as f:
    d = json.load(f)

def render_table(items):
    if not items: return "<tr><td colspan='3' style='text-align:center; padding:20px; color:#999;'>기록이 없습니다.</td></tr>"
    html = ""
    for item in items:
        medal = {1:"🥇", 2:"🥈", 3:"🥉"}.get(item['rank'], f"<span class='rank-num'>{item['rank']}</span>")
        score_style = "color:red; font-weight:bold;" if item['score'] < 0 else "color:#1a7f4b;"
        html += f"""
        <tr>
            <td class="rank-cell">{medal}</td>
            <td class="name-cell">{item['name']}<br><small style='color:#888; font-weight:normal;'>{item['course']}</small></td>
            <td class="score-cell" style="{score_style}">{item['score']:+d}</td>
        </tr>"""
    return html

html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>⛳ 골프 통합 TOP 5 랭킹</title>
<style>
    body {{ font-family: -apple-system, sans-serif; background: #f0f4f0; margin: 0; padding-bottom: 50px; }}
    header {{ background: linear-gradient(135deg, #1a7f4b, #2ecc71); color: white; padding: 20px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
    .tabs {{ display: flex; background: white; position: sticky; top: 0; z-index: 10; border-bottom: 1px solid #ddd; }}
    .tab {{ flex: 1; padding: 15px; text-align: center; font-weight: bold; color: #888; cursor: pointer; }}
    .tab.active {{ color: #1a7f4b; border-bottom: 3px solid #1a7f4b; }}
    .section {{ display: none; padding: 15px; }}
    .section.active {{ display: block; }}
    .grid {{ display: grid; grid-template-columns: 1fr; gap: 15px; }}
    @media (min-width: 768px) {{ .grid {{ grid-template-columns: 1fr 1fr; }} }}
    .card {{ background: white; border-radius: 12px; padding: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
    .card-title {{ font-weight: bold; color: #1a7f4b; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    td {{ padding: 10px 5px; border-bottom: 1px solid #f9f9f9; }}
    .rank-cell {{ width: 40px; text-align: center; }}
    .name-cell {{ font-weight: 600; line-height: 1.2; }}
    .score-cell {{ text-align: right; width: 60px; }}
    .rank-num {{ background: #eee; border-radius: 50%; width: 24px; height: 24px; display: inline-block; line-height: 24px; font-size: 12px; }}
</style>
</head>
<body>

<header>
    <h1 style="margin:0; font-size:1.5rem;">⛳ 통합 베스트 스코어</h1>
    <p style="margin:5px 0 0; font-size:0.8rem; opacity:0.8;">업데이트: {d['updated_at']}</p>
</header>

<div class="tabs">
    <div class="tab active" onclick="show('weekly', this)">주간 TOP 5</div>
    <div class="tab" onclick="show('monthly', this)">월간 TOP 5</div>
</div>

<div id="weekly" class="section active">
    <div class="grid">
        <div class="card">
            <div class="card-title">♂️ 남자 주간 베스트</div>
            <table>{render_table(d['weekly']['M'])}</table>
        </div>
        <div class="card">
            <div class="card-title">♀️ 여자 주간 베스트</div>
            <table>{render_table(d['weekly']['F'])}</table>
        </div>
    </div>
</div>

<div id="monthly" class="section">
    <div class="grid">
        <div class="card">
            <div class="card-title">♂️ 남자 월간 베스트</div>
            <table>{render_table(d['monthly']['M'])}</table>
        </div>
        <div class="card">
            <div class="card-title">♀️ 여자 월간 베스트</div>
            <table>{render_table(d['monthly']['F'])}</table>
        </div>
    </div>
</div>

<script>
    function show(id, el) {{
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.getElementById(id).classList.add('active');
        el.classList.add('active');
    }}
</script>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
