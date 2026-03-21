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
    print(f"🚀 [시스템] 티스토리 자동 업로더 '무적 무력 돌파' 모드를 시작합니다. ({today})")
    
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
        print("✅ [성공] 쿠키 로드 완료")
        val = raw_cookie.split("TSSESSION=")[1].split(";")[0] if "TSSESSION=" in raw_cookie else raw_cookie
        c.add_cookies([{"name": "TSSESSION", "value": val, "domain": ".tistory.com", "path": "/"}])

    page = c.new_page()
    
    # 원고 리스트 확보
    search_path = f"blog_drafts/{today}/tistory/*.md"
    print(f"🔍 [시스템] 원고 찾는 중: {search_path}")
    md_list = glob.glob(search_path)
    md_list.sort()

    if not md_list:
        print(f"🏕️ [{today}] 원고를 찾지 못했습니다. 현재 디렉토리: {os.getcwd()}")
        b.close()
        p.stop()
        return

    print(f"📝 [시스템] 총 {len(md_list)}개의 원고 발견. 작업 시작!")

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

            print(f"📤 [전송 대기] '{title[:15]}...' 로딩 시작")
            # 글쓰기 페이지 진입
            page.goto(f"https://{BLOG_NAME}.tistory.com/manage/post", wait_until="networkidle")
            time.sleep(10)

            if "login" in page.url:
                print(f"❌ '{title[:15]}' 실패: 쿠키 만료")
                break

            # 제목 입력
            page.locator('textarea[placeholder="제목을 입력하세요"], textarea.textarea_tit').first.wait_for(timeout=30000)
            page.locator('textarea[placeholder="제목을 입력하세요"], textarea.textarea_tit').first.fill(title)
            
            # 모드 전환 (마크다운)
            try:
                page.locator('#editor-mode-layer-btn-open').click(force=True)
                page.locator('#editor-mode-markdown').click(force=True)
                time.sleep(3)
            except: pass

            # 본문 주입
            safe_content = content.replace('`', '\\`').replace('$', '\\$').replace('\\', '\\\\')
            page.evaluate(f"if(document.querySelector('.CodeMirror')) document.querySelector('.CodeMirror').CodeMirror.setValue(`{safe_content}`);")
            time.sleep(5)

            # 🚨 [임시저장/발행 무력 돌파] 
            print("🎯 [조준] 모든 저장 버튼을 직접 검색합니다.")
            result_data = page.evaluate("""() => {
                const b_list = Array.from(document.querySelectorAll('button'));
                let target = b_list.find(b => b.innerText.includes('임시저장') || b.innerText.includes('저장'));
                if (!target) {
                    target = b_list.find(b => b.innerText.includes('완료') || b.innerText.includes('발행'));
                }
                
                if (target) {
                    target.click();
                    return { ok: true, msg: target.innerText };
                }
                return { ok: false, msg: b_list.map(b => b.innerText).join(', ') };
            }""")

            if result_data['ok']:
                print(f"✅ {result_data['msg']} 클릭 완료. 레이어 대기 중...")
                time.sleep(3)
                if "완료" in result_data['msg'] or "발행" in result_data['msg']:
                    page.evaluate("if(document.getElementById('open20')) document.getElementById('open20').click();")
                    page.locator('button#publish-btn, button:has-text("발행"), button:has-text("등록")').first.click(force=True)
                    print("✅ [성공] 비공개 발행으로 저장되었습니다.")
                else:
                    print("✅ [성공] 임시저장함에 담겼습니다.")
            else:
                print(f"⚠️ 버튼 발견 실패. (탐지 텍스트: {result_data['msg']})")
                page.keyboard.press("Enter")
                print("⌨️ [긴급] 엔터키 연타 시도")

            time.sleep(10)

        except Exception as e:
            print(f"❌ '{f}' 개별 오류 상세: {e}")

    b.close()
    p.stop()
    print("🏁 [종료] 모든 작업을 안전하게 마쳤습니다.")

if __name__ == "__main__":
    try:
        go()
    except Exception as e:
        print(f"🔥 [치명적 오류] 실행 도중 정지: {e}")
