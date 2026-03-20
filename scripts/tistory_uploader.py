import os
import glob
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

BLOG_NAME = "tentme" # ★ 성덕님 블로그 이름 확인!
today = datetime.now().strftime("%y%m%d")

DRAFTS_DIR = f"blog_drafts/{today}/tistory"
IMAGE_DIR = f"images/{today}"

def upload_to_tistory():
    md_files = glob.glob(os.path.join(DRAFTS_DIR, "*.md"))
    md_files.sort()

    if not md_files:
    print(f"🏕️ [{today}] 업로드할 티스토리 원고가 없습니다.")
    return

    with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()

    cookie_string = os.environ.get("TISTORY_COOKIE", "")
    cookie_value = cookie_string.replace("TSSESSION=", "").replace(";", "").strip()

    context.add_cookies([{
    "name": "TSSESSION",
    "value": cookie_value,
    "domain": ".tistory.com",
    "path": "/"
    }])

    page = context.new_page()

    for file_path in md_files:
    file_name = os.path.basename(file_path)
    prefix_letter = file_name.split('_')[2]

    print(f"🔥 작업 시작: {file_name}")

    with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

    if not lines:
    continue

    raw_title = lines[0].strip()
    title = raw_title.split("] ")[-1] if "] " in raw_title else raw_title
    content = "".join(lines[1:]).strip()

    try:
    page.goto(f"https://{BLOG_NAME}.tistory.com/manage/post")
    page.wait_for_load_state('networkidle')
    time.sleep(2)

    page.locator('textarea.textarea_tit').fill(title)
    time.sleep(1)

    page.locator('#editor-mode-layer-btn-open').click()
    page.locator('#editor-mode-markdown').click()
    time.sleep(1)

    page.locator('.CodeMirror textarea').fill(content)
    time.sleep(1)

    img_pattern = os.path.join(IMAGE_DIR, f"{prefix_letter}_{today}_tistory_*.png")
    images = glob.glob(img_pattern)

    if images:
    page.locator('input[type="file"]').set_input_files(images)
    print(f"📸 이미지 첨부 완료!")
    time.sleep(3)

    page.locator('button.btn-draft').click()
    print(f"✅ 완료: {title} (임시저장 됨)")
    time.sleep(15)

    except Exception as e:
    print(f"❌ 에러 발생 ({file_name}): {e}")

    browser.close()

if __name__ == "__main__":
upload_to_tistory()
