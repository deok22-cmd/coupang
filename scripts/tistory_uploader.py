import os
import glob
import time
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

# ★ 블로그 설정 및 한국 표준시(KST) 시간 설정
BLOG_NAME = "tentme"
kst = timezone(timedelta(hours=9))
today = datetime.now(kst).strftime("%y%m%d")

def go():
    # 1. Playwright 시작 및 브라우저 실행
    p = sync_playwright().start()
    b = p.chromium.launch(headless=True) # 화면을 보고 싶으면 False로 변경
    c = b.new_context()

    # 쿠키 연동 (TSSESSION 기반)
    raw_cookie = os.environ.get("TISTORY_COOKIE", "").strip()
    if not raw_cookie:
        print("⚠️ TISTORY_COOKIE 환경변수가 비어있습니다.")
        b.close()
        p.stop()
        return

    val = raw_cookie.split("TSSESSION=")[1].split(";")[0] if "TSSESSION=" in raw_cookie else raw_cookie
    
    c.add_cookies([
        {"name": "TSSESSION", "value": val, "domain": ".tistory.com", "path": "/"},
        {"name": "TSSESSION", "value": val, "domain": f"{BLOG_NAME}.tistory.com", "path": "/"}
    ])

    page = c.new_page()
    
    # 2. 원고 리스트 가져오기
    md_list = glob.glob(f"blog_drafts/{today}/tistory/*.md")
    md_list.sort()

    if not md_list:
        print(f"🏕️ [{today}] 업로드할 원고가 없습니다.")
        b.close()
        p.stop()
        return

    # 3. 원고별 반복 업로드 및 발행
    for f in md_list:
        with open(f, 'r', encoding='utf-8') as fp:
            lines = fp.readlines()
        
        if not lines:
            continue

        # 🚨 [수정 1] 제목에서 불필요한 머리말 제거 및 본소 쪼개기
        raw_title = lines[0].strip()
        title = raw_title.replace("[티스토리 SEO 원고 A] ", "").replace("[티스토리 SEO 원고 B] ", "").replace("[티스토리 SEO 원고 C] ", "").replace("[티스토리 SEO 원고 D] ", "")
        title = title.replace("# ", "") # 마크다운 기호 제거
        
        content = "".join(lines[1:]).strip()

        try:
            # 관리자 글쓰기 페이지 진입
            page.goto(f"https://{BLOG_NAME}.tistory.com/manage/post")
            page.wait_for_load_state('networkidle')
            time.sleep(3)

            # 제목 입력 시도
            page.locator('textarea[placeholder="제목을 입력하세요"], textarea.textarea_tit').first.fill(title)
            time.sleep(1)

            # 마크다운 모드 변경 및 본문 입력 (force=True로 강제 실행)
            page.locator('#editor-mode-layer-btn-open').click(force=True)
            page.locator('#editor-mode-markdown').click(force=True)
            time.sleep(1)
            page.locator('.CodeMirror textarea').first.fill(content, force=True)

            # 4. 이미지 자동 첨부
            file_basename = os.path.basename(f)
            try:
                item_symbol = file_basename.split('_')[2] 
            except IndexError:
                item_symbol = "A"

            imgs = glob.glob(f"images/{today}/{item_symbol}_{today}_tistory_*.png")
            if imgs:
                page.locator('input[type="file"]').set_input_files(imgs)
                print(f"📸 {item_symbol} 상품 이미지 {len(imgs)}장 첨부 완료!")
                time.sleep(3)

            # 🚨 [수정 2] 임시저장 대신 "비공개 발행" 프로세스 진행
            # 1단계: '완료' 버튼 클릭 (발행 레이어 오픈)
            page.locator('#publish-layer-btn').click(force=True) 
            time.sleep(1.5)

            # 2단계: '비공개' 라디오 버튼 클릭
            page.locator('input#open20').click(force=True) 
            time.sleep(1)

            # 3단계: 최종 '발행' 버튼 클릭!
            page.locator('button#publish-btn').click(force=True) 

            print(f"✅ 완료: {title} (비공개 발행 완료)")
            
            # 발행 후 안정적인 처리를 위해 5초 대기
            time.sleep(5)

        except Exception as e:
            print(f"❌ '{file_basename}' 작업 중 에러 발생: {e}")

    # 4. 종료 처리
    b.close()
    p.stop()
    print("🚀 모든 작업을 무사히 마쳤습니다.")

if __name__ == "__main__":
    go()
