import os
import glob
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

# 1. 기본 설정
BLOG_NAME = "deok22" # ★ 성덕님의 실제 티스토리 주소 앞부분으로 꼭 바꿔주세요!
today = datetime.now().strftime("%y%m%d")

# 파일 경로 설정 (성덕님이 알려주신 경로)
DRAFTS_DIR = f"blog_drafts/{today}/tistory"
IMAGE_DIR = f"images/{today}"

def upload_to_tistory():
# 오늘 날짜의 마크다운 파일들 찾기
md_files = glob.glob(os.path.join(DRAFTS_DIR, "*.md"))
md_files.sort() # A, B, C, D 순서대로 정렬

if not md_files:
print(f"🏕️ [{today}] 업로드할 티스토리 원고가 없습니다. 푹 쉬세요!")
return

# 플레이라이트(브라우저 자동화) 시작
with sync_playwright() as p:
# headless=True면 화면 없이 백그라운드에서 실행 (깃허브 액션용)
browser = p.chromium.launch(headless=True)
context = browser.new_context()

# 2. 깃허브 시크릿에서 쿠키 가져와서 로그인 상태 만들기
cookie_string = os.environ.get("TISTORY_COOKIE", "")
# TSSESSION=어쩌고; 값을 파싱해서 브라우저에 장착
cookie_value = cookie_string.replace("TSSESSION=", "").replace(";", "").strip()

context.add_cookies([{
"name": "TSSESSION",
"value": cookie_value,
"domain": ".tistory.com",
"path": "/"
}])

page = context.new_page()

# 3. 파일별로 돌면서 업로드 시작
for file_path in md_files:
file_name = os.path.basename(file_path) # 예: tistory_post_A_YYMMDD.md
prefix_letter = file_name.split('_')[2] # A, B, C, D 추출

print(f"🔥 작업 시작: {file_name}")

# 원고 읽기
with open(file_path, 'r', encoding='utf-8') as f:
lines = f.readlines()

if not lines:
continue

# 제목과 본문 분리 ([티스토리 SEO 원고 A] 제거)
raw_title = lines[0].strip()
title = raw_title.split("] ")[-1] if "] " in raw_title else raw_title
content = "".join(lines[1:]).strip()

try:
# 에디터 접속
page.goto(f"https://{BLOG_NAME}.tistory.com/manage/post")
page.wait_for_load_state('networkidle')
time.sleep(2) # 로딩 대기

# 제목 입력
page.locator('textarea.textarea_tit').fill(title)
time.sleep(1)

# 마크다운 모드로 변경 (안전하게 텍스트를 넣기 위해)
page.locator('#editor-mode-layer-btn-open').click()
page.locator('#editor-mode-markdown').click()
time.sleep(1)

# 본문 입력
page.locator('.CodeMirror textarea').fill(content)
time.sleep(1)

# 매칭되는 이미지 찾기 (A_YYMMDD_tistory_seq.png)
# 티스토리는 마크다운 모드에서 이미지를 첨부하면 글 최하단에 자동으로 코드가 들어갑니다.
img_pattern = os.path.join(IMAGE_DIR, f"{prefix_letter}_{today}_tistory_*.png")
images = glob.glob(img_pattern)

if images:
# 파일 업로드 input 태그에 이미지 경로 전달
page.locator('input[type="file"]').set_input_files(images)
print(f"📸 이미지 {len(images)}장 첨부 완료!")
time.sleep(3) # 이미지가 서버에 올라가는 시간 대기

# 임시저장 버튼 클릭 (우측 하단)
page.locator('button.btn-draft').click()
print(f"✅ 완료: {title} (임시저장 됨)")

# 티스토리의 어뷰징 의심을 피하기 위해 다음 글 쓰기 전 15초 휴식
time.sleep(15)

except Exception as e:
print(f"❌ 에러 발생 ({file_name}): {e}")

browser.close()
print("🎉 오늘의 티스토리 임시저장 자동화 임무를 마쳤습니다!")

if __name__ == "__main__":
upload_to_tistory()
