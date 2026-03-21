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
    print(f"🚀 [시스템] 티스토리 자동 업로더 '무력 돌파' 모드를 시작합니다. ({today})")
    
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

            print(f"📤 [준비] '{title[:15]}...' 로딩 시작")
            # 글쓰기 페이지 진입
            page.goto(f"https://{BLOG_NAME}.tistory.com/manage/post", wait_until="networkidle")
            time.sleep(10)

            if "login" in page.url:
                print(f"❌ '{title[:15]}' 실패: 쿠키가 만료되었습니다.")
                break

            # 제목 입력
            title_area = page.locator('textarea[placeholder="제목을 입력하세요"], textarea.textarea_tit').first
            title_area.wait_for(timeout=30000)
            title_area.fill(title)
            
            # 마크다운 모드 전환
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
            # 1. '완료' 혹은 '발행' 버튼을 눌러서 레이어를 띄웁니다.
            print("🔍 [필살기] 모든 버튼 명칭을 검색하여 강제 클릭 시도 중...")
            clicked = page.evaluate("""() => {
                const b_list = Array.from(document.querySelectorAll('button'));
                // 1순위: 임시저장
                let target = b_list.find(b => b.innerText.includes('임시저장') || b.innerText.includes('저장'));
                if (!target) {
                    // 2순위: 완료/발행 (레이어 진입)
                    target = b_list.find(b => b.innerText.includes('완료') || b.innerText.includes('발행') || b.innerText.includes('등록'));
                }
                
                if (target) {
                    target.click();
                    return { success: true, text: target.innerText };
                }
                return { success: false, list: b_list.map(b => b.innerText).join(', ') };
            }""")

            if clicked['success']:
                print(f"✅ {clicked['text']} 버튼 클릭됨. 레이어 대기 중...")
                time.sleep(3)
                # 만약 '완료' 버튼을 눌렀다면, '비공개' 설정을 확인하고 '발행' 클릭
                if "완료" in clicked['text'] or "발행" in clicked['text']:
                    # 비공개 라디오 버튼(open20) 조작 (만약 있다면)
                    page.evaluate("if(document.getElementById('open20')) document.getElementById('open20').click();")
                    # '발행' 버튼 최종 타격
                    page.locator('button#publish-btn, button:has-text("발행"), button:has-text("등록")').first.click(force=True)
                    print(f"✅ [성공] 비공개 발행으로 저장 완료: {title[:15]}...")
                else:
                    print(f"✅ [성공] 임시저장 완료: {title[:15]}...")
            else:
                print(f"⚠️ 버튼 발견 실패. 탐지된 텍스트들: [{clicked['list']}]")
                # 최후의 수단: 엔터키
                page.keyboard.press("Enter")
                print("⌨️ 긴급 조치: 엔터키 연타 시도 완료")

            time.sleep(10) # 전송 완료 대기

        except Exception as e:
            print(f"❌ '{title[:15]}' 실패 상세: {e}")

    b.close()
    p.stop()
    print("🏁 모든 작업을 마쳤습니다.")
