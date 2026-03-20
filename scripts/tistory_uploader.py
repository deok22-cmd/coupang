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
    b = p.chromium.launch(headless=True) # 화면을 직접 확인하려면 False로 변경
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

        # 정규식(Regex)으로 안전하게 제목과 본문 데이터 추출
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

        # 디버깅용 콘솔 출력 (업로드 전 확인용)
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

            # 제목 칸 클릭 및 텍스트 채우기
            title_box = page.locator('textarea[placeholder="제목을 입력하세요"], textarea.textarea_tit').first
            title_box.click()
            time.sleep(1)
            title_box.fill(title)
            time.sleep(2)

            # 에디터 모드를 마크다운으로 전환
            page.locator('#editor-mode-layer-btn-open').click(force=True)
            page.locator('#editor-mode-markdown').click(force=True)
            time.sleep(2)

            # 🚨 [최종 수술 완료] 티스토리 에디터(CodeMirror)의 내부 API를 직접 호출하여 텍스트를 뇌에 직접 꽂아 넣음!
            # 자바스크립트 템플릿 리터럴 충돌을 방지하기 위해 특수문자 이스케이프 처리
            safe_content = content.replace('`', '\\`').replace('$', '\\$').replace('\\', '\\\\')
            
            # CodeMirror 객체의 .setValue() 메소드를 사용하여 가장 안정적으로 데이터를 주입함
            page.evaluate(f"document.querySelector('.CodeMirror').CodeMirror.setValue(`{safe_content}`);")
            time.sleep(2)

            # 4. 이미지 자동 매칭 및 첨부
            # 파일 이름 규칙 (예: tistory_post_A_260320.md)에서 기호(A~D) 추출
            try:
                item_symbol = file_basename.split('_')[2] 
            except IndexError:
                item_symbol = "A"

            imgs = glob.glob(f"images/{today}/{item_symbol}_{today}_tistory_*.png")
            if imgs:
                # 파일 입력 요소에 이미지 경로 전달 (Playwright 내장 기능)
                page.locator('input[type="file"]').set_input_files(imgs)
                print(f"📸 {item_symbol} 상품 이미지 {len(imgs)}장 첨부 완료!")
                time.sleep(3)

            # 🚨 최종 발행 프로세스 (JS 클릭 및 키보드 엔터 조합)
            # 1단계: 하단 완료 레이어 열기
            page.locator('#publish-layer-btn').click(force=True)
            time.sleep(2)

            # 2단계: 비공개 라디오 버튼(open20)을 JS로 직접 강제 클릭
            page.evaluate("document.getElementById('open20').click()")
            time.sleep(1)

            # 3단계: 최종 발행 버튼에 엔터키(Enter) 전송으로 발행 확정
            page.locator('button#publish-btn').press("Enter")

            # 상태 로그 출력 (상태바 제목 앞부분)
            print(f"✅ 발행 완료: {title[:15]}... (비공개 성과)")
            
            # 발행 후 시스템 휴식을 위한 안정기 부여
            time.sleep(5)

        except Exception as e:
            # 개 개별 파일 작업 중 오류 발생 시 로깅 후 다음 파일로 진행
            print(f"❌ '{file_basename}' 프로젝트 처리 중 예상치 못한 오류 발생: {e}")

    # 4. 브라우저 자원 반납 및 Playwright 중단 (메모리 정리)
    b.close()
    p.stop()
    print("🚀 모든 티스토리 자동 업로드 및 비공개 발행 작업을 완료했습니다.")

if __name__ == "__main__":
    go()
