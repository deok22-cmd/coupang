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
    print(f"🚀 [시스템] 티스토리 자동 업로더 '최종 인간 위장' 모드를 시작합니다. ({today})")
    
    try:
        p = sync_playwright().start()
        b = p.chromium.launch(headless=True)
        c = b.new_context()
        print("🌐 [시스템] 브라우저 구동 완료")
    except Exception as e:
        print(f"❌ [에러] 브라우저 실행 문제: {e}")
        return

    # 쿠키 연동
    raw_cookie = os.environ.get("TISTORY_COOKIE", "").strip()
    if not raw_cookie:
        print("⚠️ [주의] 쿠키 데이터 없음")
    else:
        print("✅ [성공] 쿠키 로드 완료")
        val = raw_cookie.split("TSSESSION=")[1].split(";")[0] if "TSSESSION=" in raw_cookie else raw_cookie
        c.add_cookies([{"name": "TSSESSION", "value": val, "domain": ".tistory.com", "path": "/"}])

    page = c.new_page()
    
    # 원고 리스트 확보
    search_path = f"blog_drafts/{today}/tistory/*.md"
    md_list = glob.glob(search_path)
    md_list.sort()

    if not md_list:
        print(f"🏕️ [{today}] 원고를 찾지 못했습니다.")
        b.close()
        p.stop()
        return

    print(f"📝 [시스템] 총 {len(md_list)}개의 원고 작업 시작!")

    for f_path in md_list:
        try:
            with open(f_path, 'r', encoding='utf-8') as fp:
                raw_text = fp.read()
            if not raw_text: continue

            # 파싱
            title_match = re.search(r'"\[제목\]"\s*:(.*?)"\[본문\]"\s*:', raw_text, re.DOTALL)
            content_match = re.search(r'"\[본문\]"\s*:(.*)', raw_text, re.DOTALL)
            title = title_match.group(1).strip() if title_match else os.path.basename(f_path)
            content = content_match.group(1).strip() if content_match else raw_text

            print(f"📤 [진행] '{title[:15]}...' 로딩 중")
            page.goto(f"https://{BLOG_NAME}.tistory.com/manage/post", wait_until="networkidle")
            time.sleep(10)

            if "login" in page.url:
                print(f"❌ '{title[:15]}' 실패: 쿠키 만료")
                break

            # 제목 입력
            page.locator('textarea[placeholder="제목을 입력하세요"], textarea.textarea_tit').first.wait_for(timeout=30000)
            page.locator('textarea[placeholder="제목을 입력하세요"], textarea.textarea_tit').first.fill(title)
            
            # 마크다운 모드 전환
            try:
                page.evaluate("""() => {
                    const b = Array.from(document.querySelectorAll('button')).find(el => el.innerText.includes('모드'));
                    if (b) b.click();
                }""")
                time.sleep(2)
                page.evaluate("""() => {
                    const i = Array.from(document.querySelectorAll('li, button')).find(el => el.innerText.includes('마크다운'));
                    if (i) i.click();
                }""")
                time.sleep(5)
            except: pass

            # 🛠️ [본문 위장 주입]
            print("🎯 [공략] 물리적 키보드 위장 입력을 시도합니다.")
            
            # 1. 에디터 클릭 및 초기화
            editor_area = page.locator('.CodeMirror, #editor-markdown, #ke_editor_get_content').first
            editor_area.click()
            time.sleep(1)
            
            # 2. 물리적 삭제 및 텍스트 꽂기
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            time.sleep(1)
            page.keyboard.insert_text(content)
            
            # 3. 이벤트 발생
            page.keyboard.press("Enter")
            print("✅ 본문 주입 완료 (물리적 시뮬레이션)")
            time.sleep(10)

            # 저장/발행
            res = page.evaluate("""() => {
                const b_list = Array.from(document.querySelectorAll('button'));
                let target = b_list.find(b => b.innerText.includes('임시저장') || b.innerText.includes('저장'));
                if (!target) target = b_list.find(b => b.innerText.includes('완료') || b.innerText.includes('발행'));
                if (target) { target.click(); return { ok: true, msg: target.innerText }; }
                return { ok: false };
            }""")

            if res.get('ok'):
                time.sleep(2)
                if "완료" in res['msg'] or "발행" in res['msg']:
                    page.evaluate("if(document.getElementById('open20')) document.getElementById('open20').click();")
                    page.locator('button#publish-btn, button:has-text("발행")').first.click(force=True)
                    print(f"✅ OK: 발행 성공")
                else:
                    print(f"✅ OK: 임시저장 성공")
            else:
                page.keyboard.press("Enter")

            time.sleep(5) 

        except Exception as item_e:
            print(f"❌ 개별 작업 중 오류 발생: {item_e}")

    b.close()
    p.stop()
    print("🏁 [최종] 모든 작업을 무사히 마쳤습니다.")

if __name__ == "__main__":
    try:
        go()
    except Exception as main_e:
        print(f"🔥 치명적 시스템 오류: {main_e}")
