import os
import glob
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

# ★ 블로그 설정
BLOG_NAME = "tentme"

# 🚨 한국 시간(KST)으로 세팅!
kst = timezone(timedelta(hours=9))
today = datetime.now(kst).strftime("%y%m%d")

def go():
    # 1. Playwright 시작 및 브라우저 실행
    p = sync_playwright().start()
    b = p.chromium.launch(headless=True) # 창을 보고 싶으면 headless=False로 변경
    c = b.new_context()

    # 🚨 가장 중요한 쿠키 장착 부분 수정!
    raw_cookie = os.environ.get("TISTORY_COOKIE", "").strip()
    if not raw_cookie:
        print("⚠️ TISTORY_COOKIE 환경변수가 비어있습니다.")
        b.close()
        p.stop()
        return

    # 쿠키 값에서 TSSESSION 부분만 정밀 추출
    if "TSSESSION=" in raw_cookie:
        val = raw_cookie.split("TSSESSION=")[1].split(";")[0]
    else:
        val = raw_cookie

    # 도메인별 쿠키 수동 할당 (전역 도메인 + 특정 블로그 도메인)
    c.add_cookies([
        {"name": "TSSESSION", "value": val, "domain": ".tistory.com", "path": "/"},
        {"name": "TSSESSION", "value": val, "domain": f"{BLOG_NAME}.tistory.com", "path": "/"}
    ])

    page = c.new_page()
    
    # 2. 업로드할 원고 리스트 확보
    md_list = glob.glob(f"blog_drafts/{today}/tistory/*.md")
    md_list.sort() # 순서대로 업로드하기 위해 정렬

    if not md_list:
        print("🏕️ 업로드할 원고가 없습니다.")
        b.close()
        p.stop()
        return

    # 3. 원고 파일별 반복 업로드
    for f in md_list:
        # 파일 읽기
        with open(f, 'r', encoding='utf-8') as fp:
            lines = fp.readlines()
        
        if not lines:
            continue

        # 첫 번째 라인에서 제목 추출 (마크다운 제목 기호 # 제거)
        title = lines[0].strip().split("] ")[-1] if "] " in lines[0] else lines[0].strip().replace("# ", "")
        content = "".join(lines[1:]).strip()

        try:
            # 관리자 글쓰기 페이지 진입
            page.goto(f"https://{BLOG_NAME}.tistory.com/manage/post")
            page.wait_for_load_state('networkidle')
            time.sleep(3)

            # 제목 스크립트 - 다양한 셀렉터 대응
            title_input = page.locator('textarea[placeholder="제목을 입력하세요"], textarea.textarea_tit').first
            title_input.fill(title)
            time.sleep(1)

            # 에디터 모드 레이어 열기 및 마크다운 선택
            page.locator('#editor-mode-layer-btn-open').click()
            page.locator('#editor-mode-markdown').click()
            time.sleep(1)

            # 마크다운 텍스트 영역에 본문 채우기 (CodeMirror 입력)
            page.locator('.CodeMirror textarea').fill(content)

            # 4. 이미지 자동 매칭 및 첨부
            # 파일 이름 규칙 (예: tistory_post_A_260320.md)에서 기호(A,B,C,D) 추출
            try:
                item_symbol = os.path.basename(f).split('_')[2] 
            except IndexError:
                item_symbol = "A"

            imgs = glob.glob(f"images/{today}/{item_symbol}_{today}_tistory_*.png")
            
            if imgs:
                # 파일 입력 요소에 이미지 경로 전달
                page.locator('input[type="file"]').set_input_files(imgs)
                print(f"📸 {item_symbol} 상품 이미지 {len(imgs)}장 첨부 완료!")
                time.sleep(3)

            # 5. 임시저장 (Draft) 버튼 클릭
            page.locator('button.btn-draft').click()
            print(f"✅ 완료: {title} (임시저장 됨)")
            
            # 티스토리 부하 방지를 위해 충분한 대기 시간 부여
            time.sleep(15)

        except Exception as e:
            print(f"❌ '{f}' 작업 중 에러 발생: {e}")

    # 6. 브라우저 및 Playwright 종료
    b.close()
    p.stop()
    print("🚀 모든 작업을 마쳤습니다.")

if __name__ == "__main__":
    go()
