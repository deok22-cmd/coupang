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
    md_list.sort()

    if not md_list:
        print(f"🏕️ [{today}] 업로드할 원고가 없습니다.")
        b.close()
        p.stop()
        return

    # 3. 원고 파일별 반복 업로드 및 임시저장
    for f in md_list:
        with open(f, 'r', encoding='utf-8') as fp:
            raw_text = fp.read()
        
        if not raw_text:
            continue

        # 정규식으로 제목과 본문 데이터 추출
        title_match = re.search(r'"\[제목\]"\s*:(.*?)"\[본문\]"\s*:', raw_text, re.DOTALL)
        content_match = re.search(r'"\[본문\]"\s*:(.*)', raw_text, re.DOTALL)

        if title_match and content_match:
            title = title_match.group(1).strip()
            content = content_match.group(1).strip()
        else:
            print(f"⚠️ '{f}' 파싱 실패. 건너뜁니다.")
            continue

        file_basename = os.path.basename(f)
        try:
            # 관리자 글쓰기 페이지 진입
            page.goto(f"https://{BLOG_NAME}.tistory.com/manage/post")
            page.wait_for_load_state('networkidle')
            time.sleep(3)

            # 🛠️ [방해 요소 제거] 혹시나 떠있을 수 있는 팝업창이나 환영 메시지를 ESC 키로 제거
            page.keyboard.press("Escape")
            time.sleep(1)

            # 제목 입력 필드에 데이터 채우기
            page.locator('textarea[placeholder="제목을 입력하세요"], textarea.textarea_tit').first.fill(title)
            time.sleep(1)

            # 에디터 모드를 마크다운으로 전환
            page.locator('#editor-mode-layer-btn-open').click(force=True)
            page.locator('#editor-mode-markdown').click(force=True)
            time.sleep(2)

            # 뇌(CodeMirror)에 데이터를 직접 주입하여 오류 방지
            safe_content = content.replace('`', '\\`').replace('$', '\\$').replace('\\', '\\\\')
            page.evaluate(f"document.querySelector('.CodeMirror').CodeMirror.setValue(`{safe_content}`);")
            time.sleep(2)

            # 이미지 첨부 생략 (원활한 업로드 우선 정책 반영)

            # 🚨 [임시저장 버튼 타격]
            # 오른쪽 하단의 [완료] 버튼이 아닌, 왼쪽 하단에 상시 노출되는 [임시저장] 버튼 타겟팅
            page.locator('button.btn-draft').first.click(force=True)

            print(f"✅ 임시저장 클릭 완료: {title[:15]}...")

            # 글이 서버로 완전히 전송 및 저장될 때까지 넉넉히 대기
            time.sleep(10)

        except Exception as e:
            # 개별 파일 처리 중 에러 로그 출력
            print(f"❌ '{file_basename}' 프로젝트 처리 중 오류 발생: {e}")

    # 4. 브라우저 및 Playwright 인스턴스 종료
    b.close()
    p.stop()
    print("🚀 모든 티스토리 원고의 임시저장 업로드 작업을 완료했습니다.")

if __name__ == "__main__":
    go()
