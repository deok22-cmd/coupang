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
    p = sync_playwright().start()
    b = p.chromium.launch(headless=True) # 서버는 headless=True 필수
    c = b.new_context()

    # 쿠키 연동 (TSSESSION)
    raw_cookie = os.environ.get("TISTORY_COOKIE", "").strip()
    if not raw_cookie:
        print("⚠️ TISTORY_COOKIE 환경변수가 비어있습니다.")
        b.close()
        p.stop()
        return

    val = raw_cookie.split("TSSESSION=")[1].split(";")[0] if "TSSESSION=" in raw_cookie else raw_cookie
    c.add_cookies([{"name": "TSSESSION", "value": val, "domain": ".tistory.com", "path": "/"}])

    page = c.new_page()
    
    md_list = glob.glob(f"blog_drafts/{today}/tistory/*.md")
    md_list.sort()

    if not md_list:
        print(f"🏕️ [{today}] 업로드할 티토리 원고가 없습니다.")
        b.close()
        p.stop()
        return

    for f in md_list:
        with open(f, 'r', encoding='utf-8') as fp:
            raw_text = fp.read()
        
        if not raw_text:
            continue

        # [레이저 파싱]
        title_match = re.search(r'"\[제목\]"\s*:(.*?)"\[본문\]"\s*:', raw_text, re.DOTALL)
        content_match = re.search(r'"\[본문\]"\s*:(.*)', raw_text, re.DOTALL)

        if title_match and content_match:
            title = title_match.group(1).strip()
            content = content_match.group(1).strip()
        else:
            title = os.path.basename(f)
            content = raw_text

        print(f"🔥 '{title[:15]}...' 로딩 시작 (초장기 대기 모드)")

        try:
            # 1단계: 글쓰기 페이지 진입 및 넉넉한 대기 (네트워크 유휴 상태까지)
            page.goto(f"https://{BLOG_NAME}.tistory.com/manage/post", wait_until="networkidle")
            time.sleep(10) # 깃허브 서버를 위한 추가 10초 휴식

            if "login" in page.url:
                print("❌ 쿠키 만료: 로그인이 필요함.")
                break

            # 2단계: 제목 및 에디터 로딩 대기
            page.locator('textarea[placeholder="제목을 입력하세요"], textarea.textarea_tit').first.wait_for(timeout=30000)
            page.locator('textarea[placeholder="제목을 입력하세요"], textarea.textarea_tit').first.fill(title)
            
            # 마크다운 모드 전환
            page.locator('#editor-mode-layer-btn-open').click(force=True)
            page.locator('#editor-mode-markdown').click(force=True)
            time.sleep(5)

            # 본문 주입 (에디터 뇌에 꽂기)
            safe_content = content.replace('`', '\\`').replace('$', '\\$').replace('\\', '\\\\')
            page.evaluate(f"if(document.querySelector('.CodeMirror')) document.querySelector('.CodeMirror').CodeMirror.setValue(`{safe_content}`);")
            time.sleep(3)

            # 🚨 [최종 조작] "저장" 혹은 "임시저장" 버튼을 찾을 때까지 끈질기게 시도
            # JavaScript로 직접 버튼 텍스트를 검색하여 클릭 (가장 확실함)
            clicked = page.evaluate("""() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const saveBtn = buttons.find(b => b.innerText.includes('저장') || b.classList.contains('btn_save') || b.id.includes('save'));
                if (saveBtn) {
                    saveBtn.click();
                    return true;
                }
                return false;
            }""")

            if not clicked:
                # 위 방식 실패 시 전통적인 Playwright 방식으로 한 번 더 시도
                page.locator('button:has-text("저장"), button.btn_save, button.btn-draft').first.click(force=True)
            
            print(f"✅ 임시저장 클릭 성공: {title[:20]}...")
            time.sleep(10) # 서버 전송 대기

        except Exception as e:
            print(f"❌ '{title[:15]}' 실패 상세: {e}")

    b.close()
    p.stop()
    print("🏁 티스토리 업로드 작업을 모두 마쳤습니다.")
