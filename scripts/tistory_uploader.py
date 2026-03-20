import os
import glob
import time
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

# ★ 블로그 설정 및 한국 표준시(KST) 기반 오늘 날짜 설정
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

    # 쿠키 값 파싱 (TSSESSION= 뒷부분 추출)
    val = raw_cookie.split("TSSESSION=")[1].split(";")[0] if "TSSESSION=" in raw_cookie else raw_cookie
    
    # 세션 쿠키 수동 주입
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

        # 🚨 [핵심] "[제목]" 과 "[본문]" 태그를 기준으로 전기톱 커팅 로직!
        title = ""
        content = ""

        try:
            # "[제목]" : 과 "[본문]" : 사이의 실제 제목 텍스트만 빼오기
            after_title_tag = raw_text.split('"[제목]" :')[1]
            title = after_title_tag.split('"[본문]" :')[0].strip()

            # "[본문]" : 뒷부분은 전부 다 본문으로 인식!
            content = raw_text.split('"[본문]" :')[1].strip()
        except IndexError:
            # 태그가 누락되었거나 형식이 틀린 경우, 파일명을 제목으로 임시 사용
            print(f"⚠️ '{f}' 파싱 실패: 태그 형식을 확인하세요. 파일명으로 대체합니다.")
            title = os.path.basename(f)
            content = raw_text

        file_basename = os.path.basename(f)
        try:
            # 관리자 글쓰기 페이지 진입
            page.goto(f"https://{BLOG_NAME}.tistory.com/manage/post")
            page.wait_for_load_state('networkidle')
            time.sleep(3)

            # 제목 입력 필드에 키인
            page.locator('textarea[placeholder="제목을 입력하세요"], textarea.textarea_tit').first.fill(title)
            time.sleep(1)

            # 에디터 모드를 마크다운으로 변경 버튼 클릭 (강제 클릭 모드)
            page.locator('#editor-mode-layer-btn-open').click(force=True)
            page.locator('#editor-mode-markdown').click(force=True)
            time.sleep(1)

            # 마크다운 텍스트 영역에 본문 입력 (CodeMirror 텍스트 영역 대상)
            page.locator('.CodeMirror textarea').first.fill(content, force=True)

            # 4. 이미지 자동 매칭 및 첨부
            # 파일 이름 규칙 (예: tistory_post_A_260320.md)에서 상품 기호(A~D) 추출
            try:
                item_symbol = file_basename.split('_')[2] 
            except IndexError:
                item_symbol = "A"

            imgs = glob.glob(f"images/{today}/{item_symbol}_{today}_tistory_*.png")
            if imgs:
                # 파일 업로드 컨트롤러에 다중 이미지 경로 전달
                page.locator('input[type="file"]').set_input_files(imgs)
                print(f"📸 '{item_symbol}' 상품 이미지 {len(imgs)}장 첨부 완료!")
                time.sleep(3)

            # 🚨 [핵심] 최종 발행 레이어 제어 (자바스크립트 직접 조작 방식)
            # 1단계: 우측 하단 레이어 열기 버튼 클릭 (완료 버튼)
            page.locator('#publish-layer-btn').click(force=True)
            time.sleep(2)

            # 2단계: 비공개 라디오 버튼의 HTML ID(open20)를 직접 찾아 자바스크립트로 클릭 강제 수행!
            page.evaluate("document.getElementById('open20').click()")
            time.sleep(1)

            # 3단계: 최종 발행 버튼에 포커스를 맞춘 뒤 엔터키(Enter) 입력으로 동작 확정!
            page.locator('button#publish-btn').press("Enter")

            # 상태 로그 출력 (제목 앞부분 15자)
            print(f"✅ 발행 완료: {title[:15]}... (성공)")
            
            # 발행 후 안정적인 처리를 위한 일시 정지 (5초)
            time.sleep(5)

        except Exception as e:
            print(f"❌ '{file_basename}' 프로젝트 처리 중 오류 발생: {e}")

    # 4. 브라우저 및 Playwright 종료 (메모리 정리)
    b.close()
    p.stop()
    print("🚀 모든 티스토리 자동 업로드 및 비공개 발행 작업을 무사히 마쳤습니다.")

if __name__ == "__main__":
    go()
