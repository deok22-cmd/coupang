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
    print(f"🚀 [시스템] 티스토리 자동 업로더 정밀 모드를 시작합니다. ({today})")
    
    try:
        p = sync_playwright().start()
        b = p.chromium.launch(headless=True)
        c = b.new_context()
    except Exception as e:
        print(f"❌ [에러] 브라우저 실행 문제: {e}")
        return

    # 쿠키 연동
    raw_cookie = os.environ.get("TISTORY_COOKIE", "").strip()
    if not raw_cookie:
        print("⚠️ [주의] 쿠키 데이터 없음")
    else:
        val = raw_cookie.split("TSSESSION=")[1].split(";")[0] if "TSSESSION=" in raw_cookie else raw_cookie
        c.add_cookies([{"name": "TSSESSION", "value": val, "domain": ".tistory.com", "path": "/"}])

    page = c.new_page()
    
    # 원고 리스트 확보
    md_list = glob.glob(f"blog_drafts/{today}/tistory/*.md")
    md_list.sort()

    if not md_list:
        print(f"🏕️ [{today}] 업로드할 티토리 원고가 없습니다.")
        b.close()
        p.stop()
        return

    for f in md_list:
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                raw_text = fp.read()
            
            if not raw_text: continue

            # [레이저 파싱]
            title_match = re.search(r'"\[제목\]"\s*:(.*?)"\[본문\]"\s*:', raw_text, re.DOTALL)
            content_match = re.search(r'"\[본문\]"\s*:(.*)', raw_text, re.DOTALL)

            title = title_match.group(1).strip() if title_match else os.path.basename(f)
            content = content_match.group(1).strip() if content_match else raw_text

            print(f"📤 [준비] '{title[:15]}...' 전송 대기 중")

            # 글쓰기 페이지 진입
            page.goto(f"https://{BLOG_NAME}.tistory.com/manage/post", wait_until="networkidle")
            time.sleep(7) # 로딩 안정화 대기

            if "login" in page.url:
                print(f"❌ '{title[:15]}' 실패: 쿠키가 만료되었습니다.")
                break

            # 제목 입력
            title_area = page.locator('textarea[placeholder="제목을 입력하세요"], textarea.textarea_tit').first
            title_area.wait_for(timeout=30000)
            title_area.fill(title)
            
            # 🛠️ 마크다운 모드 전환
            try:
                page.locator('#editor-mode-layer-btn-open').click(force=True)
                page.locator('#editor-mode-markdown').click(force=True)
                time.sleep(3)
            except:
                print("⚠️ 모드 전환 스킵 (이미 마크다운일 수 있습니다.)")

            # 본문 주입
            safe_content = content.replace('`', '\\`').replace('$', '\\$').replace('\\', '\\\\')
            page.evaluate(f"if(document.querySelector('.CodeMirror')) document.querySelector('.CodeMirror').CodeMirror.setValue(`{safe_content}`);")
            time.sleep(3)

            # 🚨 [임시저장 타격] 가장 강력한 셀렉터 시도
            # 1. 화면 맨 아래로 스크롤 (버튼 활성화 유도)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # 2. 버튼 찾기 및 클릭 (임시저장, 저장 순)
            # 티스토리 에디터 하단 버튼들을 다각도로 탐색
            save_selectors = [
                'button:has-text("임시저장")', 
                'button.btn_save', 
                'button:has-text("저장")',
                'button.btn_item.btn_save',
                'button.btn-draft'
            ]
            
            clicked = False
            for selector in save_selectors:
                try:
                    btn = page.locator(selector).first
                    if btn.is_visible():
                        btn.click(force=True)
                        clicked = True
                        print(f"✅ [성공] 임시저장 완료 (방식: {selector})")
                        break
                except:
                    continue

            if not clicked:
                # 마지막 필살기: 모든 'button' 중 '저장' 글자가 포함된 것 클릭
                result = page.evaluate("""() => {
                    const b = Array.from(document.querySelectorAll('button')).find(el => el.innerText.includes('저장'));
                    if (b) { b.click(); return true; }
                    return false;
                }""")
                if result:
                    print("✅ [성공] 임시저장 완료 (Javascript 강제 클릭)")
                else:
                    print(f"❌ '{title[:15]}' 실패: 저장 버튼을 도저히 찾을 수 없습니다.")

            time.sleep(10) # 서버 저장 완료 대기

        except Exception as e:
            print(f"❌ '{f}' 개별 오류: {e}")

    b.close()
    p.stop()
    print("🏁 [종료] 모든 작업을 완료했습니다.")

if __name__ == "__main__":
    go()
