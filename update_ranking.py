import requests, re, os, json, urllib3
from datetime import datetime, timezone, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
KST = timezone(timedelta(hours=9))

USER_ID = os.environ.get("SG_ID", "")
PASSWORD = os.environ.get("SG_PW", "")

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
        
        # [동점자 처리 핵심]: 한 플레이어의 베스트 스코어를 결정할 때도 이글 > 버디 > 파 순으로 판별
        if p not in best_per_player:
            best_per_player[p] = r
        else:
            current_best = best_per_player[p]
            new_key = (r['score'], -r['albatross_cnt'], -r['eagle_cnt'], -r['birdie_cnt'], -r['par_cnt'], r['date'])
            old_key = (current_best['score'], -current_best['albatross_cnt'], -current_best['eagle_cnt'], -current_best['birdie_cnt'], -current_best['par_cnt'], current_best['date'])
            if new_key < old_key:
                best_per_player[p] = r
            
    # [랭킹 정렬 규칙]: 총타수(낮은 순) -> 알바트로스 -> 이글 -> 버디 -> 파 개수(많은 순) -> 날짜 순
    sorted_list = sorted(
        best_per_player.values(), 
        key=lambda x: (x['score'], -x['albatross_cnt'], -x['eagle_cnt'], -x['birdie_cnt'], -x['par_cnt'], x['date'])
    )
    return [{"rank": i+1, **item} for i, item in enumerate(sorted_list[:top_n])]

session = requests.Session()
def login():
    data = {"retUrl": "/main", "userId": USER_ID, "passwd": PASSWORD}
    r = session.post("https://screen.sggolf.com/login/checkProcess", data=data, verify=False)
    return "isLogin = true" in r.text

now = datetime.now(KST)
start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
end_of_week = start_of_week + timedelta(days=6)

# 💡 [대회 연동 핵심]: 7월로 넘어가도 6월 대회 데이터가 잘리지 않도록 대회 시작일(6/22)을 하한선으로 고정합니다.
event_start_dt = datetime(
