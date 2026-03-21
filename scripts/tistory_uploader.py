import os
import glob
import time
import re
import sys
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

# ★ 블로그 설정 및 한국 표준시(KST) 기반 오늘 날짜 설정
BLOG_NAME = "tentme"
kst = timezone(timedelta(hours=9))
today = datetime.now(kst).strftime("%y%m%d")

def go():
    print(f"🚀 [시스템] 티스토리 자동 업로더를 시작합니다. (오늘 날짜: {today})")
    print(f"📂 [시스템] 현재 작업 디렉토리: {os.getcwd()}")
    
    try:
        p = sync_playwright().start()
        print("🌐 [시스템] Playwright 엔진 구동 완료")
        
        b = p.chromium.launch(headless=True)
        print("🌐 [시스템] 브라우저(Chromium) 실행 완료")
        
        c = b.new_context()
    except Exception as e:
        print(f"❌ [에러] 브라우저 실행 중 치명적 오류: {e}")
        return

    # 쿠키 연동
    raw_cookie = os.environ.get("TISTORY_COOKIE", "").strip()
    if not raw_cookie:
        print("⚠️ [주의] TISTORY_COOKIE 환경변수가 비어있습니다. 로그인이 불가능할 수 있습니다.")
    else:
        print("✅ [성공] 쿠키(TISTORY_COOKIE) 데이터 로드 완료")
        val = raw_cookie.split("TSSESSION=")[1].split(";")[0] if "TSSESSION=" in raw_cookie else raw_cookie
        c.add_cookies([{"name": "TSSESSION", "value": val, "domain": ".tistory.com", "path": "/"}])

    page = c.new_page()
    
    # 🔍 원고 리스트 확보
    search_path = f"blog_drafts/{today}/tistory/*.md"
    print(f"🔍 [시스템] 원고를 찾는 중: {search_path}")
    md_list = glob.glob(search_path)
    md_list.sort()

    if not md_list:
        print(f"🏕️ [{today}] 업로드할 티토리 원고를 찾지 못했습니다. 폴더 경로를 확인해 주세요.")
        b.close()
        p.stop()
        return

    print(f"📝 [시스템] 총 {len(md_list)}개의 원고를 발견했습니다. 업로드를 시작합니다.")

    for f in md_list:
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                raw_text = fp.read()
            
            if not raw_text: continue

            # [레이저 파싱]
            title_match = re.search(r'"\[제목\]"\s*:(.*?)"\[본문\]"\s*:', raw_text, re.DOTALL)
            content_match = re.search(r'"\[본문\]"\s*:(.*)', raw_text, re.DOTALL)

            if title_match and content_match:
                title = title_match.group(1).strip()
                content = content_match.group(1).strip()
            else:
                title = os.path.basename(f)
                content = raw_text

            print(f"📤 [전송] '{title[:15]}...' 로딩 중 (30초 대기 모드)")

            # 글쓰기 페이지 진입
            page.goto(f"https://{BLOG_NAME}.tistory.com/manage/post", wait_until="networkidle")
            time.sleep(5)

            if "login" in page.url:
                print(f"❌ '{title[:15]}' 실패: 쿠키가 만료되었습니다. (로그인 페이지로 리다이렉트됨)")
                break

            # 제목 및 본문 주입
            page.locator('textarea[placeholder="제목을 입력하세요"], textarea.textarea_tit').first.wait_for(timeout=30000)
            page.locator('textarea[placeholder="제목을 입력하세요"], textarea.textarea_tit').first.fill(title)
            
            page.locator('#editor-mode-layer-btn-open').click(force=True)
            page.locator('#editor-mode-markdown').click(force=True)
            time.sleep(3)

            safe_content = content.replace('`', '\\`').replace('$', '\\$').replace('\\', '\\\\')
            page.evaluate(f"if(document.querySelector('.CodeMirror')) document.querySelector('.CodeMirror').CodeMirror.setValue(`{safe_content}`);")
            time.sleep(2)

            # 저장 버튼 클릭 (JS 방식)
            clicked = page.evaluate("""() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const saveBtn = buttons.find(b => b.innerText.includes('저장') || b.classList.contains('btn_save') || b.id.includes('save'));
                if (saveBtn) { saveBtn.click(); return true; }
                return false;
            }""")

            if not clicked:
                page.locator('button:has-text("저장"), button.btn_save').first.click(force=True)
            
            print(f"✅ [완료] 임시저장 성공: {title[:20]}...")
            time.sleep(5)

        except Exception as e:
            print(f"❌ '{f}' 처리 중 개별 오류 발생: {e}")

    b.close()
    p.stop()
    print("🏁 [종료] 모든 티스토리 업로드 작업을 완료했습니다.")

if __name__ == "__main__":
    try:
        go()
    except Exception as main_e:
        print(f"🔥 [치명적 에러] 메인 함수 실행 중단: {main_e}")
