import requests
import re
import os
import json
from datetime import datetime
from collections import defaultdict, Counter

TARGET_COURSE = "베어리버 리버"
START_DATE    = "2026-04-08"
USER_ID       = os.environ.get("SG_ID", "")
PASSWORD      = os.environ.get("SG_PW", "")

EXCLUDED_PLAYERS = set()

FEMALE_PLAYERS = {
    "안은영", "제둘림", "박기례", "정순이", "김명희", "이매실", "김현애",
    "김경숙", "강미경", "이미경", "박경희", "황애정", "김은하", "서경숙",
    "안소영", "임혜정", "김진희", "김선희", "김필례", "장해영", "김승혜",
}

SINPERIO_EXCLUDED = [3, 4, 8]
SINPERIO_INCLUDED = [i for i in range(9) if i not in SINPERIO_EXCLUDED]

BASE_URL  = "https://smanager.sggolf.com/gameInfo/gameDayState"
LOGIN_URL = "https://screen.sggolf.com/login/checkProcess"
SCORE_URL = "https://smanager.sggolf.com/gameInfo/popup/scoreCardPp.json"
HEADERS   = {"User-Agent": "Mozilla/5.0"}

session = requests.Session()

def login():
    data = {"retUrl": "/main", "userId": USER_ID, "passwd": PASSWORD}
    r = session.post(LOGIN_URL, data=data, headers=HEADERS, timeout=15)
    return r.status_code == 200 and "isLogin = true" in r.text

def get_total_pages(html):
    nums = re.findall(r'onclick="moveList\((\d+)\);', html)
    return max(map(int, nums)) if nums else 1

def fetch_score_card(gserial, ccid):
    params = {"gserial": gserial, "game_id": "0", "iindex": "0", "ccid": ccid}
    r = session.get(SCORE_URL, params=params, timeout=15)
    return r.json() if r.status_code == 200 else None

def calc_sinperio(diff_list):
    return sum(diff_list[i] for i in SINPERIO_INCLUDED) * 1.5

def check_mulligan_value(val):
    if val is None:
        return False
    numbers = re.findall(r'\d+', str(val).strip())
    return sum(int(n) for n in numbers) > 0 if numbers else False

def backcount_key(rec):
    return (rec["score"], *rec["diffs"][::-1])

def best_record(records):
    return min(records, key=backcount_key)

def get_top(table, top_n=12):
    candidates = [(p, best_record(recs)) for p, recs in table.items()]
    ranked = sorted(candidates, key=lambda x: backcount_key(x[1]))[:top_n]
    return [{"rank": r, "name": p} for r, (p, _) in enumerate(ranked, 1)]

def get_most_played(counter, top_n=10):
    return [{"rank": r, "name": p, "count": c}
            for r, (p, c) in enumerate(counter.most_common(top_n), 1)]

# ---------------------------
# 수집
# ---------------------------
assert login(), "로그인 실패"

resp = session.get(
    BASE_URL,
    params={"menuId": "57", "parentId": "33", "time_start1": START_DATE},
    headers=HEADERS
)
resp.raise_for_status()

total_pages = get_total_pages(resp.text)
all_rounds = []

for page in range(1, total_pages + 1):
    page_html = resp.text if page == 1 else session.get(
        BASE_URL,
        params={"menuId": "57", "parentId": "33",
                "time_start1": START_DATE, "pageIndex": page},
        headers=HEADERS
    ).text
    rows = re.findall(r"<tr.*?>(.*?)</tr>", page_html, re.DOTALL)
    for row in rows:
        date_match = re.search(r"([0-9]{4}-[0-9]{2}-[0-9]{2})", row)
        game_match = re.search(
            r"go_scoreCardPp_stat\('0',\s*'([^']+)'\s*,\s*'0',\s*'([^']+)'\s*\);", row
        )
        if date_match and game_match:
            all_rounds.append((game_match.group(1), game_match.group(2), date_match.group(1)))

# ---------------------------
# 집계
# ---------------------------
par_cache = {}
general_scores  = {"M": defaultdict(list), "F": defaultdict(list)}
handicap_scores = {"M": defaultdict(list), "F": defaultdict(list)}
play_counts     = {"M": Counter(), "F": Counter()}
valid_rounds    = 0

for gserial, ccid, game_date in all_rounds:
    data = fetch_score_card(gserial, ccid)
    if not data:
        continue

    members = data.get("GamePlayerMember", {})
    if not members or members.get("cc", "").strip() != TARGET_COURSE:
        continue

    score_list_all = data.get("GameInfoListScoreList", [])
    if len(score_list_all) < 9:
        continue
    holes = score_list_all[:9]

    if ccid not in par_cache:
        hole_info = data.get("GameInfoListCCHoleInfo", [{}])[0]
        par_cache[ccid] = [int(hole_info.get(f"par{str(h).zfill(2)}", 0)) for h in range(1, 10)]

    par_list = par_cache[ccid]
    valid_flag = False

    for i in range(1, 5):
        player_name = members.get(f"player{i}", "").strip()
        if not player_name:
            continue

        clean_name = re.sub(r'\(.*?\)', '', player_name).strip()
        if clean_name in EXCLUDED_PLAYERS:
            continue

        is_mulligan = check_mulligan_value(members.get(f"mulligan{i}", "0"))
        if not is_mulligan:
            for hole in holes:
                if check_mulligan_value(hole.get(f"mul_cnt{i}", "0")) or \
                   check_mulligan_value(hole.get(f"mulligan{i}", "0")):
                    is_mulligan = True
                    break
        if is_mulligan:
            continue

        diffs, invalid_flag = [], False
        for hole_idx, score_obj in enumerate(holes):
            shot_val = score_obj.get(f"shot{i}", "-")
            if isinstance(shot_val, str):
                shot_val = shot_val.strip()
            if shot_val in ("-", "", "&nbsp;", None):
                invalid_flag = True
                break
            try:
                diffs.append(int(shot_val) - par_list[hole_idx])
            except (ValueError, TypeError):
                invalid_flag = True
                break

        if invalid_flag or len(diffs) < 9:
            continue

        total_diff = sum(diffs)
        if total_diff == -36:
            continue

        sex = "F" if clean_name in FEMALE_PLAYERS else "M"
        rec = {"score": float(total_diff), "diffs": diffs}

        general_scores[sex][clean_name].append(rec)
        handicap_scores[sex][clean_name].append(
            {"score": total_diff - calc_sinperio(diffs), "diffs": diffs}
        )
        play_counts[sex][clean_name] += 1
        valid_flag = True

    if valid_flag:
        valid_rounds += 1

# ---------------------------
# JSON 저장
# ---------------------------
result = {
    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "course": TARGET_COURSE,
    "valid_rounds": valid_rounds,
    "unique_players": len(play_counts["M"]) + len(play_counts["F"]),
    "general_M":   get_top(general_scores["M"]),
    "general_F":   get_top(general_scores["F"]),
    "handicap_M":  get_top(handicap_scores["M"]),
    "handicap_F":  get_top(handicap_scores["F"]),
    "played_M":    get_most_played(play_counts["M"]),
    "played_F":    get_most_played(play_counts["F"]),
}

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"완료: {result['updated_at']} / {valid_rounds}라운드 / {result['unique_players']}명")
