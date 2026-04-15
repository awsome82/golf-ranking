from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import requests
import os
import time
from datetime import datetime, timedelta
import pytz

# --- 설정 ---
MEAL_URL = 'https://oksu.sen.es.kr/136474/subMenu.do'
BOT_TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
KST = pytz.timezone('Asia/Seoul')


def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    return webdriver.Chrome(options=chrome_options)


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
    try:
        res = requests.post(url, json=payload, timeout=10)
        print(f"텔레그램 메시지 전송: {res.status_code}")
    except Exception as e:
        print(f"텔레그램 메시지 전송 실패: {e}")


def send_telegram_photo(image_url, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    payload = {
        'chat_id': CHAT_ID,
        'photo': image_url,
        'caption': caption[:1000],
        'parse_mode': 'HTML'
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        print(f"텔레그램 사진 전송: {res.status_code}")
        if res.status_code != 200:
            send_telegram_message(caption + f"\n\n🖼 사진: {image_url}")
    except Exception as e:
        print(f"텔레그램 사진 전송 실패: {e}")
        send_telegram_message(caption)


def get_target_date():
    """
    내일 날짜 KST 기준 반환.
    금요일 실행 → 월요일 메뉴 반환 (주말 건너뜀)
    """
    now = datetime.now(KST)
    tomorrow = now + timedelta(days=1)
    if tomorrow.weekday() == 5:    # 토요일 → 월요일
        tomorrow += timedelta(days=2)
    elif tomorrow.weekday() == 6:  # 일요일 → 월요일
        tomorrow += timedelta(days=1)
    return tomorrow


def click_lunch_link(driver, target_date):
    """
    확인된 달력 구조:
      <td>
        14                          ← td 직접 텍스트에 날짜 숫자
        <ul>
          <li>
            <a href="javascript:void(0);"
               onclick="fnDetail('3160371', this);"
               title="클릭하면 내용을 보실 수 있습니다.">점심</a>
          </li>
        </ul>
      </td>

    전략: td 중 직접 텍스트(날짜 숫자)가 일치하는 것을 찾고,
          그 안의 "점심" 링크를 클릭.
    """
    day = str(target_date.day)
    print(f"달력에서 {day}일 '점심' 링크 탐색...")

    try:
        # td 전체 순회 → 날짜 숫자 텍스트 매칭 → 점심 링크 클릭
        # XPath: td 안의 직접 텍스트(normalize)가 day와 같고, 하위에 "점심" a 태그가 있는 것
        xpath = (
            f'//td['
            f'normalize-space(text())="{day}" '
            f'and .//a[normalize-space(text())="점심"]'
            f']//a[normalize-space(text())="점심"]'
        )
        lunch_link = driver.find_element(By.XPATH, xpath)
        driver.execute_script("arguments[0].click();", lunch_link)
        print(f"✅ {day}일 점심 클릭 성공")
        time.sleep(2)
        return True
    except Exception as e:
        print(f"XPath 탐색 실패: {e}")
        return False


def parse_meal(driver):
    """
    확인된 HTML 구조:
      메뉴:  <td class="ta_l">보리밥 경상도소고기국 ...</td>
      이미지: <img src="/dggb/module/file/selectImageView.do?atchFileId=...&fileSn=0" alt="식단">
    """
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # ── 메뉴 텍스트 ──
    menu_text = ""
    tds = soup.select('td.ta_l')
    if tds:
        td = max(tds, key=lambda x: len(x.get_text(strip=True)))
        menu_text = td.get_text(' ', strip=True)
        print(f"메뉴: {menu_text[:100]}")
    else:
        print("⚠️ td.ta_l 없음 — 메뉴 파싱 실패")

    # ── 이미지 URL ──
    image_url = None
    img = soup.select_one('img[alt="식단"]')
    if img:
        src = img.get('src', '')
        image_url = src if src.startswith('http') else f"https://oksu.sen.es.kr{src}"
        print(f"이미지: {image_url}")
    else:
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if 'atchFileId' in src:
                image_url = src if src.startswith('http') else f"https://oksu.sen.es.kr{src}"
                print(f"이미지(백업): {image_url}")
                break

    return menu_text, image_url


def format_menu(menu_text):
    """'보리밥 소고기국 ...' → 줄바꿈 bullet 형태"""
    items = [item.strip() for item in menu_text.split() if item.strip()]
    return '\n'.join(f"• {item}" for item in items)


def main():
    target = get_target_date()
    weekday_names = ['월', '화', '수', '목', '금', '토', '일']
    date_str = f"{target.month}월 {target.day}일({weekday_names[target.weekday()]})"

    print(f"=== 옥수초 급식 알림 ===")
    print(f"대상 날짜: {date_str}")

    driver = setup_driver()
    try:
        print("급식 사이트 접속...")
        driver.get(MEAL_URL)
        time.sleep(3)

        clicked = click_lunch_link(driver, target)
        if not clicked:
            print("⚠️ 클릭 실패 — 현재 페이지 그대로 파싱 시도")

        menu_text, image_url = parse_meal(driver)
    finally:
        driver.quit()

    if not menu_text:
        send_telegram_message(
            f"🍱 <b>옥수초 {date_str} 급식</b>\n\n"
            f"❌ 메뉴 정보를 가져오지 못했어요.\n"
            f"🔗 직접 확인: {MEAL_URL}"
        )
        return

    caption = (
        f"🍱 <b>내일({date_str}) 점심 급식</b>\n\n"
        f"{format_menu(menu_text)}\n\n"
        f"🏫 옥수초등학교"
    )

    if image_url:
        send_telegram_photo(image_url, caption)
    else:
        send_telegram_message(caption)

    print("✅ 전송 완료!")


if __name__ == "__main__":
    main()
