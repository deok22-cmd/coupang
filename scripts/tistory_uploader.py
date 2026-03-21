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
    print(f"🚀 [시스템] 티스토리 자동 업로더 '본문 완벽 주입' 모드를 시작합니다. ({today})")
    
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
    md_list = glob.glob(search_path)
    md_list.sort()

    if not md_list:
        print(f"🏕️ [{today}] 원고를 찾지 못했습니다.")
        b.close()
        p.stop()
        return

    for f in md_list:
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                raw_text = fp.read()
            if not raw_text: continue

            # [정규식 파싱]
            title_match = re.search(r'"\[제목\]"\s*:(.*?)"\[본문\]"\s*:', raw_text, re.DOTALL)
            content_match = re.search(r'"\[본문\]"\s*:(.*)', raw_text, re.DOTALL)
            title = title_match.group(1).strip() if title_match else os.path.basename(f)
            content = content_match.group(1).strip() if content_match else raw_text

            print(f"📤 [작업 중] '{title[:15]}...' 본문 주입 중")
            page.goto(f"https://{BLOG_NAME}.tistory.com/manage/post", wait_until="networkidle")
            time.sleep(10)

            if "login" in page.url:
                print(f"❌ '{title[:15]}' 실패: 쿠키 만료")
                break

            # 1. 제목 입력
            page.locator('textarea[placeholder="제목을 입력하세요"], textarea.textarea_tit').first.wait_for(timeout=30000)
            page.locator('textarea[placeholder="제목을 입력하세요"], textarea.textarea_tit').first.fill(title)
            
            # 2. 마크다운 모드 전환 (강화된 방식)
            try:
                # 상단 모드 메뉴 클릭
                page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('button'));
                    const modeBtn = btns.find(b => b.innerText.includes('모드') || b.id.includes('editor-mode'));
                    if (modeBtn) modeBtn.click();
                }""")
                time.sleep(1)
                # 마크다운 항목 클릭
                page.evaluate("""() => {
                    const items = Array.from(document.querySelectorAll('li, a, button'));
                    const mdItem = items.find(i => i.innerText.includes('마크다운') || i.innerText.includes('Markdown'));
                    if (mdItem) mdItem.click();
                }""")
                time.sleep(5)
            except: pass

            # 3. 본문 주입 (강력한 3단계 주입)
            safe_content = content.replace('`', '\\`').replace('$', '\\$').replace('\\', '\\\\')
            injected = page.evaluate(f"""() => {{
                // 방법 1: CodeMirror (마크다운 에디터)
                const cmNode = document.querySelector('.CodeMirror');
                if (cmNode && cmNode.CodeMirror) {{
                    cmNode.CodeMirror.setValue(`{safe_content}`);
                    return "CODEMIRROR";
                }}
                // 방법 2: 표준 Textarea
                const ta = document.querySelector('textarea.textarea_input') || document.querySelector('#editor-markdown');
                if (ta) {{
                    ta.value = `{safe_content}`;
                    return "TEXTAREA";
                }}
                // 방법 3: ContentEditable (기본 모드)
                const ce = document.querySelector('.tt_article_content [contenteditable="true"]') || document.querySelector('#ke_editor_get_content');
                if (ce) {{
                    ce.innerText = `{safe_content}`;
                    return "CONTENTEDITABLE";
                }}
                return "FAIL";
            }}""")
            
            print(f"🎯 [에디터] 본문 주입 방식: {injected}")
            time.sleep(3)

            # 4. 저장/발행 무력 돌파
            result_data = page.evaluate("""() => {
                const b_list = Array.from(document.querySelectorAll('button'));
                let target = b_list.find(b => b.innerText.includes('임시저장') || b.innerText.includes('저장'));
                if (!target) target = b_list.find(b => b.innerText.includes('완료') || b.innerText.includes('발행'));
                
                if (target) { target.click(); return { ok: true, msg: target.innerText }; }
                return { ok: false };
            }""")

            if result_data.get('ok'):
                time.sleep(3)
                if "완료" in result_data['msg'] or "발행" in result_data['msg']:
                    page.evaluate("if(document.getElementById('open20')) document.getElementById('open20').click();")
                    page.locator('button#publish-btn, button:has-text("발행"), button:has-text("등록")').first.click(force=True)
                    print(f"✅ [성공] 비공개 발행 완료: {title[:15]}")
                else:
                    print(f"✅ [성공] 임시저장 완료: {title[:15]}")
            else:
                print(f"⚠️ 저장 버튼 실패. 엔터키 시도")
                page.keyboard.press("Enter")

            time.sleep(1) 

        except Exception as e:
            print(f"❌ '{f}' 개별 오류: {e}")

    b.close()
    p.stop()
    print("🏁 [종료] 모든 작업을 마쳤습니다.")
