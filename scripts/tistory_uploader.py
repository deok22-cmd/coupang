import os
import glob
import time
import re
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

# ★ 블로그 설정 및 한국 표준시(KST) 기반 오늘 날짜 설정
BLOG_NAME = "tentme"
kst = timezone(timedelta(hours=9))
today = datetime.now(kst).strftime("%y%m%d")

def go():
    # 1. Playwright 시작 및 브라우저 실행
    p = sync_playwright().start()
    b = p.chromium.launch(headless=True) # 창을 직접 확인하려면 False로 변경
    c = b.new_context()

    # 쿠키 연동 (TSSESSION 기반)
    raw_cookie = os.environ.get("TISTORY_COOKIE", "").strip()
    if not raw_cookie:
        print("⚠️ TISTORY_COOKIE 환경변수가 비어있습니다.")
        b.close()
        p.stop()
        return

    # 쿠키 값 파싱 (TSSESSION= 뒷부분 추출)
    val = raw_cookie.split("TSSESSION=")[1].split(";")[0] if "TSSESSION=" in raw_cookie else raw_cookie
    
    # 세션 쿠키 수동 주입 (도메인 범위 설정)
    c.add_cookies([
        {"name": "TSSESSION", "value": val, "domain": ".tistory.com", "path": "/"}
    ])

    page = c.new_page()
    
    # 2. 업로드할 원고 리스트 확보 (Markdown 파일)
    md_list = glob.glob(f"blog_drafts/{today}/tistory/*.md")
    md_list.sort() # 순서대로 발행하기 위해 정렬

    if not md_list:
        print(f"🏕️ [{today}] 업로드할 원고가 없습니다.")
        b.close()
        p.stop()
        return

    # 3. 원고 파일별 반복 업로드 및 비공개 발행
    for f in md_list:
        with open(f, 'r', encoding='utf-8') as fp:
            raw_text = fp.read() # 파일 전체 내용 읽기
        
        if not raw_text:
            continue

        # 정규식(Regex)으로 안전하게 제목과 본문 분리
        title = ""
        content = ""
        title_match = re.search(r'"\[제목\]"\s*:(.*?)"\[본문\]"\s*:', raw_text, re.DOTALL)
        content_match = re.search(r'"\[본문\]"\s*:(.*)', raw_text, re.DOTALL)

        if title_match and content_match:
            title = title_match.group(1).strip()
            content = content_match.group(1).strip()
        else:
            title = "⚠️ 정규식 매칭 실패"
            content = raw_text

        # 디버깅용 콘솔 출력
        print(f"\n=========================================")
        print(f"📄 파일명: {os.path.basename(f)}")
        print(f"🎯 추출된 제목: {title}")
        print(f"=========================================\n")

        file_basename = os.path.basename(f)
        try:
            # 관리자 글쓰기 페이지 진입
            page.goto(f"https://{BLOG_NAME}.tistory.com/manage/post")
            page.wait_for_load_state('networkidle')
            time.sleep(3)

            # 🚨 [수정됨] 마우스로 제목 칸을 먼저 클릭하고 천천히 입력하기
            title_box = page.locator('textarea[placeholder="제목을 입력하세요"], textarea.textarea_tit').first
            title_box.click()
            time.sleep(1)
            title_box.fill(title)
            time.sleep(2)

            # 에디터 모드를 마크다운으로 변경 버튼 클릭
            page.locator('#editor-mode-layer-btn-open').click(force=True)
            page.locator('#editor-mode-markdown').click(force=True)
            time.sleep(2)

            # 🚨 [수정됨] 본칙 칸 클릭 후, 자바스크립트로 강제 욱여넣기 로직
            content_box = page.locator('.CodeMirror textarea').first
            content_box.click(force=True)
            time.sleep(1)

            # 파이썬 레벨에서 에디터 내부 변수값(value)을 백틱(`)을 사용해 강제로 교체함 (문자열 충돌 방지)
            safe_content = content.replace('`', '\\`').replace('$', '\\$') # 템플릿 리터럴 충돌 방지
            page.evaluate(f"document.querySelector('.CodeMirror textarea').value = `{safe_content}`;")
            time.sleep(1)

            # 에디터가 텍스트 유입을 즉각 인지하도록 가상 스페이스바 입력
            content_box.press("Space")
            time.sleep(2)

            # 4. 이미지 자동 매칭 및 첨부
            try:
                item_symbol = file_basename.split('_')[2] 
            except IndexError:
                item_symbol = "A"

            imgs = glob.glob(f"images/{today}/{item_symbol}_{today}_tistory_*.png")
            if imgs:
                # 파일 입력 요소에 이미지 경로 목록 주입
                page.locator('input[type="file"]').set_input_files(imgs)
                print(f"📸 {item_symbol} 상품 이미지 {len(imgs)}장 첨부 완료!")
                time.sleep(3)

            # 🚨 최종 발행 프로세스 (자바스크립트 해킹 클릭 방식 고도화)
            # 1단계: 우측 하단 완료 레이어 오픈
            page.locator('#publish-layer-btn').click(force=True)
            time.sleep(2)

            # 2단계: 비공개 라디오 버튼의 HTML ID(open20)를 직접 찾아 JS 클릭 강제 실행
            page.evaluate("document.getElementById('open20').click()")
            time.sleep(1)

            # 3단계: 최종 발행 버튼에서 엔터키(Enter) 전송으로 발행 확정
            page.locator('button#publish-btn').press("Enter")

            # 진행 상황 요약 로그
            print(f"✅ 발행 완료: {title[:15]}... (비공개 성과)")
            
            # 발행 후 시스템 안정화를 위한 휴식
            time.sleep(5)

        except Exception as e:
            print(f"❌ '{file_basename}' 프로젝트 처리 중 예상치 못한 오류 발생: {e}")

    # 4. 브라우저 자원 반납 및 Playwright 중단 (메모리 정리)
    b.close()
    p.stop()
    print("🚀 모든 티스토리 자동 업로드 및 비공개 발행 작업을 완료했습니다.")

if __name__ == "__main__":
    go()
