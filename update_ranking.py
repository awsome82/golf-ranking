import requests, re, os, json, urllib3, sys
from datetime import datetime, timezone, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
KST = timezone(timedelta(hours=9))

USER_ID = os.environ.get("SG_ID", "")
PASSWORD = os.environ.get("SG_PW", "")

# 💡 가상 환경에서 즉시 로그를 확인할 수 있도록 출력 버퍼링을 강제 플러시 처리합니다.
print("⛳ [시스템] update_ranking.py 스크립트 가동을 시작합니다.", flush=True)

# 여성 플레이어 명단
FEMALE_PLAYERS = {"신영순", "안은영", "제둘림", "박기례", "정순이", "김명희", "이매실", "김현애", "김경숙", "강미경", "이미경", "박경희", "황애정", "김은하", "서경숙", "안소영", "임혜정", "김진희", "김선희", "김필례", "장해영", "김승혜", "매실", "정진희"}

def check_mulligan_value(val) -> bool:
    if val is None:
        return False
    numbers = re.findall(r'\d+', str(val).strip())
    return sum(int(n) for n in numbers) > 0 if numbers else False

def get_total_pages(html: str) -> int:
    nums = re.findall(r'onclick="moveList\((\d+)\);', html)
    return max(map(int, nums)) if nums else 1

def get_rank_data(records, top_n=5):
    if not records: return []
    best_per_player = {}
    for r in records:
        p = r['name']
        score_val = int(r['score'])
        
        if p not in best_per_player:
            best_per_player[p] = r
        else:
            current_best = best_per_player[p]
            new_key = (r['score'], -r['albatross_cnt'], -r['eagle_cnt'], -r['birdie_cnt'], -r['par_cnt'], r['date'])
            old_key = (current_best['score'], -current_best['albatross_cnt'], -current_best['eagle_cnt'], -current_best['birdie_cnt'], -current_best['par_cnt'], current_best['date'])
            if new_key < old_key:
                best_per_player[p] = r
            
    sorted_list = sorted(
        best_per_player.values(), 
        key=lambda x: (x['score'], -x['albatross_cnt'], -x['eagle_cnt'], -x['birdie_cnt'], -x['par_cnt'], x['date'])
    )
    return [{"rank": i+1, **item} for i, item in enumerate(sorted_list[:top_n])]

session = requests.Session()
def login():
    data = {"retUrl": "/main", "userId": USER_ID, "passwd": PASSWORD}
    try:
        r = session.post("https://screen.sggolf.com/login/checkProcess", data=data, verify=False, timeout=15)
        return "isLogin = true" in r.text
    except Exception as e:
        print(f"❌ [네트워크 오류] SG골프 서버 접속 실패: {e}", flush=True)
        return False

now = datetime.now(KST)
start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
end_of_week = start_of_week + timedelta(days=6)

event_start_dt = datetime(2026, 6, 22, tzinfo=KST)
START_DATE = min(start_of_month, start_of_week, event_start_dt).strftime("%Y-%m-%d")

# 💡 기본 exit을 명확한 sys.exit(1)로 변경하여 실패 시 워크플로우를 즉시 차단합니다.
if not login():
    print("❌ [인증 오류] SG골프 로그인에 실패했습니다. ID/PW 설정을 검토하세요.", flush=True)
    sys.exit(1)

print("🔑 [인증 완료] SG골프 매니저 세션 확보 성공.", flush=True)

try:
    first_resp = session.get("https://smanager.sggolf.com/gameInfo/gameDayState", params={"time_start1": START_DATE}, verify=False, timeout=15)
    total_pages = get_total_pages(first_resp.text)
    print(f"📊 [동적 페이징] 연산 완료: 총 {total_pages}개 페이지 전수 조사 착수", flush=True)
except Exception as e:
    print(f"❌ [데이터 수집 실패] 메인 리스트 획득 중 크래시: {e}", flush=True)
    total_pages = 0
    first_resp = None

raw_candidates = []
if first_resp and total_pages > 0:
    for page in range(1, total_pages + 1):
        try:
            page_html = first_resp.text if page == 1 else session.get(
                "https://smanager.sggolf.com/gameInfo/gameDayState", 
                params={"time_start1": START_DATE, "pageIndex": page}, verify=False, timeout=15
            ).text
            
            rows = re.findall(r"<tr.*?>(.*?)</tr>", page_html, re.DOTALL)
            for row in rows:
                d_m = re.search(r"(\d{4}-\d{2}-\d{2})", row)
                g_m = re.search(r"go_scoreCardPp_stat\s*\(\s*'[^']*'\s*,\s*'([^']*)'\s*,\s*'[^']*'\s*,\s*'([^']*)'\s*\)", row)
                if d_m and g_m:
                    raw_candidates.append((g_m.group(1).strip(), g_m.group(2).strip(), d_m.group(1)))
        except Exception as e:
            print(f"❌ [페이지 스킵] {page}페이지 읽기 실패: {e}", flush=True)

weekly_M, weekly_F, monthly_M, monthly_F = [], [], [], []
tournament_M, tournament_F = [], []

print(f"🔎 [매칭 개시] 총 {len(raw_candidates)}개의 매치 후보 카드 전수 검증 진행", flush=True)

for gserial, ccid, d_str in raw_candidates:
    dt = datetime.strptime(d_str, "%Y-%m-%d").replace(tzinfo=KST)
    try:
        params = {"gserial": gserial, "game_id": "0", "iindex": "0", "ccid": ccid}
        r_json = session.get("https://smanager.sggolf.com/gameInfo/popup/scoreCardPp.json", params=params, verify=False, timeout=15).json()
        
        members = r_json.get("GamePlayerMember", {})
        score_list = r_json.get("GameInfoListScoreList", [])
        hole_info_list = r_json.get("GameInfoListCCHoleInfo", [{}])
        hole_info = hole_info_list[0] if hole_info_list else {}
        if not score_list: continue

        for i in range(1, 5):
            raw_player_name = members.get(f"player{i}") or members.get(f"player{i:02d}")
            if not raw_player_name: continue
            
            player_name = str(raw_player_name).strip()
            clean_name = re.sub(r'\(.*?\)', '', player_name).strip()

            played_holes = []
            for idx, s in enumerate(score_list):
                shot_val = None
                for k in [f"shot{i}", f"shot{i:02d}"]:
                    if k in s and s[k] not in (None, "-", "", "&nbsp;"):
                        shot_val = s[k]
                        break
                if shot_val is not None:
                    try:
                        if int(str(shot_val).strip()) > 0:
                            played_holes.append((s, int(str(shot_val).strip()), idx + 1))
                    except (ValueError, TypeError):
                        continue

            if len(played_holes) < 9: continue
            valid_holes = played_holes[:9]

            is_mulligan = check_mulligan_value(members.get(f"mulligan{i}", "0")) or \
                          check_mulligan_value(members.get(f"mulligan{i:02d}", "0"))
            if not is_mulligan:
                for hole, _, _ in valid_holes:
                    if check_mulligan_value(hole.get(f"mul_cnt{i}", "0")) or \
                       check_mulligan_value(hole.get(f"mul_cnt{i:02d}", "0")) or \
                       check_mulligan_value(hole.get(f"mulligan{i}", "0")) or \
                       check_mulligan_value(hole.get(f"mulligan{i:02d}", "0")):
                        is_mulligan = True
                        break
            if is_mulligan:
                continue

            total_shots = 0
            albatross_cnt = 0
            eagle_cnt = 0
            birdie_cnt = 0
            par_cnt = 0

            for hole, shot, hole_num in valid_holes:
                total_shots += shot
                
                par_val = 4
                par_key = f"par{str(hole_num).zfill(2)}"
                if par_key in hole_info and hole_info[par_key] is not None:
                    try:
                        par_val = int(str(hole_info[par_key]).strip())
                    except:
                        par_val = 4
                
                h_diff = shot - par_val
                if h_diff <= -3:
                    albatross_cnt += 1
                elif h_diff == -2:
                    eagle_cnt += 1
                elif h_diff == -1:
                    birdie_cnt += 1
                elif h_diff == 0:
                    par_cnt += 1

            if total_shots == 0: continue
            
            diff = int(total_shots - 36)
            gender = "F" if clean_name in FEMALE_PLAYERS else "M"
            
            record = {
                "name": clean_name, 
                "score": diff, 
                "course": members.get("cc", "알수없음"), 
                "date": d_str,
                "albatross_cnt": albatross_cnt,
                "eagle_cnt": eagle_cnt,
                "birdie_cnt": birdie_cnt,
                "par_cnt": par_cnt
            }
            
            if dt >= start_of_month:
                monthly_M.append(record) if gender == "M" else monthly_F.append(record)
            if start_of_week <= dt <= end_of_week:
                weekly_M.append(record) if gender == "M" else weekly_F.append(record)
                
            if "이스트힐" in members.get("cc", "") and "2026-06-22" <= d_str <= "2026-07-09":
                tournament_M.append(record) if gender == "M" else tournament_F.append(record)
                
            print(f"✅ 수집 성공: {clean_name} ({diff:+d}타, {members.get('cc')} | 이글:{eagle_cnt}, 버디:{birdie_cnt}, 파:{par_cnt})", flush=True)
    except Exception as e:
        print(f"❌ [라운드 해석 에러] 일련번호: {gserial} | 원인: {e}", flush=True)
        continue

# 💡 [구조 방어] 데이터가 비어있어도 최소 구조를 유지하여 다음 빌더가 터지지 않게 보장합니다.
data = {
    "updated_at": now.strftime("%Y-%m-%d %H:%M"),
    "period": {
        "week_start": start_of_week.strftime("%Y-%m-%d"),
        "week_end": (start_of_week + timedelta(days=6)).strftime("%Y-%m-%d"),
        "month_start": start_of_month.strftime("%Y-%m-%d")
    },
    "weekly": {"M": get_rank_data(weekly_M), "F": get_rank_data(weekly_F)},
    "monthly": {"M": get_rank_data(monthly_M), "F": get_rank_data(monthly_F)},
    "tournament": {"M": get_rank_data(tournament_M, top_n=10), "F": get_rank_data(tournament_F, top_n=10)}
}

# 최종 물리 파일 저장 강제화
try:
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("🚀 [완료] data.json 파일이 정상 위치에 세틀링되었습니다.", flush=True)
except Exception as e:
    print(f"❌ [저장 실패] data.json 물리 쓰기 실패: {e}", flush=True)
    sys.exit(1)
