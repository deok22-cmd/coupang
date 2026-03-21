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
    print(f"🚀 [시스템] 티스토리 자동 업로더 '풀 패키지+로그' 버전을 시작합니다. ({today})")
    
    try:
        p = sync_playwright().start()
        b = p.chromium.launch(headless=True)
        c = b.new_context()
        print("🌐 [시스템] 브라우저 엔진이 정상적으로 가동되었습니다.")
    except Exception as e:
        print(f"❌ [에러] 브라우저 실행 중 치명적 오류: {e}")
        return

    # 쿠키 연동
    raw_cookie = os.environ.get("TISTORY_COOKIE", "").strip()
    if not raw_cookie:
        print("⚠️ [주의] TISTORY_COOKIE 환경변수가 비어있습니다.")
    else:
        print("✅ [성공] 쿠키(TISTORY_COOKIE) 로드 완료")
        val = raw_cookie.split("TSSESSION=")[1].split(";")[0] if "TSSESSION=" in raw_cookie else raw_cookie
        c.add_cookies([{"name": "TSSESSION", "value": val, "domain": ".tistory.com", "path": "/"}])

    page = c.new_page()
    
    # 원고 리스트 확보
    search_path = f"blog_drafts/{today}/tistory/*.md"
    print(f"🔍 [시스템] 원고를 찾는 중: {search_path}")
    md_list = glob.glob(search_path)
    md_list.sort()

    if not md_list:
        print(f"🏕️ [{today}] 업로드할 티토리 원고를 찾지 못했습니다. (경로 확인 요망)")
        b.close()
        p.stop()
        return

    print(f"📝 [시스템] 총 {len(md_list)}개의 원고 발견. 작업을 시작합니다.")

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

            print(f"📤 [진행] '{title[:15]}...' 로딩 중")
            page.goto(f"https://{BLOG_NAME}.tistory.com/manage/post", wait_until="networkidle")
            time.sleep(10)

            if "login" in page.url:
                print(f"❌ '{title[:15]}' 실패: 쿠키 만료")
                break

            # 제목 입력
            page.locator('textarea[placeholder="제목을 입력하세요"], textarea.textarea_tit').first.wait_for(timeout=30000)
            page.locator('textarea[placeholder="제목을 입력하세요"], textarea.textarea_tit').first.fill(title)
            
            # 📸 이미지 자동 첨부 (상품별 2장씩 매칭)
            try:
                symbol = "A"
                if "_post_B_" in f: symbol = "B"
                elif "_post_C_" in f: symbol = "C"
                elif "_post_D_" in f: symbol = "D"
                
                img_path = f"images/{today}/{symbol}_{today}_tistory_*.png"
                imgs = glob.glob(img_path)
                if imgs:
                    imgs.sort()
                    # 2장까지 첨부
                    page.locator('input[type="file"]').set_input_files(imgs[:2])
                    print(f"   📸 {symbol} 상품 전용 이미지 {len(imgs[:2])}장 첨부 완료")
                    time.sleep(5)
            except Exception as img_e:
                print(f"   ⚠️ 이미지 첨부 중 경미한 오류: {img_e}")

            # 모드 전환 및 본문 주입
            try:
                page.evaluate("""() => {
                    const b = Array.from(document.querySelectorAll('button')).find(el => el.innerText.includes('모드'));
                    if (b) b.click();
                }""")
                time.sleep(1)
                page.evaluate("""() => {
                    const i = Array.from(document.querySelectorAll('li, button')).find(el => el.innerText.includes('마크다운'));
                    if (i) i.click();
                }""")
                time.sleep(5)
            except: pass

            # 본문 3중 주입
            safe_content = content.replace('`', '\\`').replace('$', '\\$').replace('\\', '\\\\')
            injected = page.evaluate(f"""() => {{
                // 1) CodeMirror
                const cm = document.querySelector('.CodeMirror')?.CodeMirror;
                if (cm) {{ cm.setValue(`{safe_content}`); return "CODEMIRROR"; }}
                // 2) Textarea
                const ta = document.querySelector('textarea.textarea_input') || document.querySelector('#editor-markdown');
                if (ta) {{ ta.value = `{safe_content}`; return "TEXTAREA"; }}
                // 3) ContentEditable
                const ce = document.querySelector('.tt_article_content [contenteditable="true"]');
                if (ce) {{ ce.innerText = `{safe_content}`; return "CONTENTEDITABLE"; }}
                return "FAIL";
            }}""")
            print(f"🎯 [에디터] 본문 주입 방식: {injected}")
            time.sleep(3)

            # 저장/발행
            res = page.evaluate("""() => {
                const b_list = Array.from(document.querySelectorAll('button'));
                let target = b_list.find(b => b.innerText.includes('임시저장') || b.innerText.includes('저장'));
                if (!target) target = b_list.find(b => b.innerText.includes('완료') || b.innerText.includes('발행'));
                if (target) { target.click(); return { ok: true, msg: target.innerText }; }
                return { ok: false };
            }""")

            if res.get('ok'):
                time.sleep(3)
                if "완료" in res['msg'] or "발행" in res['msg']:
                    page.evaluate("if(document.getElementById('open20')) document.getElementById('open20').click();")
                    page.locator('button#publish-btn, button:has-text("발행")').first.click(force=True)
                    print(f"✅ [성공] 비공개 발행 완료: {title[:15]}")
                else:
                    print(f"✅ [성공] 임시저장 완료: {title[:15]}")
            else:
                page.keyboard.press("Enter")
                print("⌨️ [긴급] 저장 버튼 미발견으로 엔터 시도")

            time.sleep(5) 

        except Exception as e:
            print(f"❌ '{f}' 개별 오류 상세: {e}")

    b.close()
    p.stop()
    print("🏁 [종료] 모든 티스토리 업로드 작업을 완료했습니다.")

if __name__ == "__main__":
    try:
        go()
    except Exception as e:
        print(f"🔥 [치명적 오류] 실행 실패: {e}")
