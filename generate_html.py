import json
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

with open("data.json", encoding="utf-8") as f:
    d = json.load(f)

MEDAL = {1: "🥇", 2: "🥈", 3: "🥉"}

def rows(items, show_count=False):
    html = ""
    for item in items:
        r     = item["rank"]
        name  = item["name"]
        medal = MEDAL.get(r, f'<span class="rank-num">{r}</span>')
        extra = f'<span class="count">{item["count"]}회</span>' if show_count else ""
        html += f"""
        <tr>
          <td class="rank-cell">{medal}</td>
          <td class="name-cell">{name}</td>
          <td>{extra}</td>
        </tr>"""
    return html

def table_card(title, items, show_count=False):
    return f"""
    <div class="card">
      <div class="card-title">{title}</div>
      <table>
        <tbody>{rows(items, show_count)}</tbody>
      </table>
    </div>"""

html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#1a7f4b">
<title>⛳ {d['course']} 랭킹</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #f0f4f0;
    color: #1a1a1a;
    padding-bottom: 2rem;
  }}

  header {{
    background: linear-gradient(135deg, #1a7f4b, #2ecc71);
    color: white;
    padding: 1.2rem 1rem 0.8rem;
    text-align: center;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  }}

  header h1 {{ font-size: 1.2rem; font-weight: 700; }}

  .header-sub {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.6rem;
    margin-top: 0.35rem;
    flex-wrap: wrap;
  }}

  .header-sub p {{
    font-size: 0.78rem;
    opacity: 0.9;
  }}

  #update-btn {{
    background: rgba(255,255,255,0.25);
    border: 1px solid rgba(255,255,255,0.6);
    color: white;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.25rem 0.7rem;
    border-radius: 20px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.3rem;
    transition: background 0.2s;
    white-space: nowrap;
  }}

  #update-btn:hover {{ background: rgba(255,255,255,0.35); }}
  #update-btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}

  .spinner {{
    display: inline-block;
    width: 12px; height: 12px;
    border: 2px solid rgba(255,255,255,0.4);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}

  #toast {{
    position: fixed;
    bottom: 1.5rem;
    left: 50%;
    transform: translateX(-50%);
    background: #333;
    color: #fff;
    padding: 0.55rem 1.2rem;
    border-radius: 20px;
    font-size: 0.82rem;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.3s;
    z-index: 999;
    white-space: nowrap;
  }}
  #toast.show {{ opacity: 1; }}

  .tabs {{
    display: flex;
    background: #fff;
    border-bottom: 2px solid #e0e0e0;
    position: sticky;
    top: 70px;
    z-index: 99;
    overflow-x: auto;
    scrollbar-width: none;
  }}
  .tabs::-webkit-scrollbar {{ display: none; }}

  .tab {{
    flex: 1;
    min-width: 80px;
    padding: 0.7rem 0.5rem;
    text-align: center;
    font-size: 0.82rem;
    font-weight: 600;
    color: #888;
    cursor: pointer;
    border-bottom: 3px solid transparent;
    white-space: nowrap;
    transition: all 0.2s;
  }}
  .tab.active {{
    color: #1a7f4b;
    border-bottom-color: #1a7f4b;
  }}

  .section {{ display: none; padding: 0.8rem; }}
  .section.active {{ display: block; }}

  .grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.7rem;
  }}

  .card {{
    background: #fff;
    border-radius: 14px;
    padding: 0.9rem 0.8rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  }}

  .card-title {{
    font-size: 0.82rem;
    font-weight: 700;
    color: #1a7f4b;
    margin-bottom: 0.6rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #e8f5e9;
  }}

  table {{ width: 100%; border-collapse: collapse; }}

  td {{
    padding: 0.35rem 0.2rem;
    font-size: 0.88rem;
    vertical-align: middle;
  }}

  .rank-cell {{ width: 28px; text-align: center; }}
  .rank-num {{
    display: inline-block;
    width: 20px; height: 20px;
    background: #f0f0f0;
    border-radius: 50%;
    font-size: 0.72rem;
    font-weight: 700;
    line-height: 20px;
    text-align: center;
    color: #666;
  }}
  .name-cell {{ font-weight: 600; }}
  .count     {{ font-size: 0.78rem; color: #888; }}

  tr:not(:last-child) td {{ border-bottom: 1px solid #f5f5f5; }}

  .stats {{
    display: flex;
    gap: 0.7rem;
    margin-bottom: 0.8rem;
  }}
  .stat-box {{
    flex: 1;
    background: #fff;
    border-radius: 12px;
    padding: 0.7rem;
    text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  }}
  .stat-val {{ font-size: 1.4rem; font-weight: 700; color: #1a7f4b; }}
  .stat-lbl {{ font-size: 0.72rem; color: #888; margin-top: 0.1rem; }}
</style>
</head>
<body>

<header>
  <h1>⛳ {d['course']} 랭킹</h1>
  <div class="header-sub">
    <p id="updated-text">업데이트: {d['updated_at']} &nbsp;|&nbsp; {d['valid_rounds']}라운드 · {d['unique_players']}명</p>
    <button id="update-btn" onclick="triggerUpdate()">
      <span id="btn-icon">🔄</span> 업데이트
    </button>
  </div>
</header>

<div id="toast"></div>

<div class="tabs">
  <div class="tab active" onclick="show('handicap', this)">핸디캡</div>
  <div class="tab"        onclick="show('general',  this)">일반스코어</div>
  <div class="tab"        onclick="show('played',   this)">최다플레이</div>
</div>

<div id="handicap" class="section active">
  <div class="grid">
    {table_card("🏌️ 남자 핸디캡 TOP12", d['handicap_M'])}
    {table_card("🏌️‍♀️ 여자 핸디캡 TOP12", d['handicap_F'])}
  </div>
</div>

<div id="general" class="section">
  <div class="grid">
    {table_card("🏌️ 남자 일반스코어 TOP12", d['general_M'])}
    {table_card("🏌️‍♀️ 여자 일반스코어 TOP12", d['general_F'])}
  </div>
</div>

<div id="played" class="section">
  <div class="stats">
    <div class="stat-box">
      <div class="stat-val">{d['valid_rounds']}</div>
      <div class="stat-lbl">총 라운드</div>
    </div>
    <div class="stat-box">
      <div class="stat-val">{d['unique_players']}</div>
      <div class="stat-lbl">참여 인원</div>
    </div>
  </div>
  <div class="grid">
    {table_card("🏌️ 남자 최다플레이 TOP10", d['played_M'], show_count=True)}
    {table_card("🏌️‍♀️ 여자 최다플레이 TOP10", d['played_F'], show_count=True)}
  </div>
</div>

<script>
  // ── 탭 전환 ──────────────────────────────────────────
  function show(id, el) {{
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    el.classList.add('active');
  }}

  // ── 토스트 메시지 ──────────────────────────────────
  function toast(msg, duration=3000) {{
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), duration);
  }}

  // ── GitHub Actions 트리거 ──────────────────────────
  // GitHub Personal Access Token (repo scope 필요)
  // 아래 두 값을 본인 것으로 교체하세요
  const GITHUB_OWNER = "YOUR_GITHUB_USERNAME";   // ← 본인 GitHub 아이디
  const GITHUB_REPO  = "golf-ranking";            // ← 레포 이름
  const GITHUB_PAT   = "YOUR_PAT_TOKEN";          // ← 발급받은 PAT

  async function triggerUpdate() {{
    const btn  = document.getElementById('update-btn');
    const icon = document.getElementById('btn-icon');

    btn.disabled = true;
    icon.outerHTML = '<span class="spinner" id="btn-icon"></span>';
    toast("업데이트 요청 중...", 2000);

    try {{
      const res = await fetch(
        `https://api.github.com/repos/${{GITHUB_OWNER}}/${{GITHUB_REPO}}/actions/workflows/update.yml/dispatches`,
        {{
          method: "POST",
          headers: {{
            "Authorization": `Bearer ${{GITHUB_PAT}}`,
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
          }},
          body: JSON.stringify({{ ref: "main" }}),
        }}
      );

      if (res.status === 204) {{
        toast("✅ 업데이트 시작! 약 1~2분 후 새로고침하세요.");
        // 2분 후 자동 새로고침
        setTimeout(() => location.reload(), 120000);
      }} else {{
        const err = await res.json().catch(() => ({{}}));
        toast("❌ 오류: " + (err.message || res.status));
      }}
    }} catch(e) {{
      toast("❌ 네트워크 오류: " + e.message);
    }} finally {{
      setTimeout(() => {{
        const spinner = document.getElementById('btn-icon');
        if (spinner) spinner.outerHTML = '<span id="btn-icon">🔄</span>';
        btn.disabled = false;
      }}, 5000);
    }}
  }}
</script>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("index.html 생성 완료")
