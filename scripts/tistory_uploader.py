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
    b = p.chromium.launch(headless=True) 
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
            print(f"⚠️ '{f}' 태그 파셔 실패. 원문 그대로 시도합니다.")
            title = os.path.basename(f)
            content = raw_text

        print(f"🚀 '{title[:15]}...' 서버 직송 시작!")

        try:
            # 1단계: 티스토리 글쓰기 페이지 진입 (확실한 주소 사용)
            page.goto(f"https://{BLOG_NAME}.tistory.com/manage/post?category=0", wait_until="networkidle")
            
            # 로그인 여부 체크 (한 번 더)
            if "login" in page.url:
                print("❌ 실패: 쿠키가 만료되었습니다.")
                break

            # 🚨 [중요] 토큰이 로딩될 때까지 기다림 + 다양한 셀렉터 시도
            token = None
            for _ in range(10): # 최대 10초 대기
                # 1. input 요소 찾기
                token_input = page.locator('input[name="access_token"]').first
                if token_input.count() > 0:
                    token = token_input.get_attribute('value')
                
                # 2. 혹은 자바스크립트 변수에서 직접 긁기
                if not token:
                    token = page.evaluate("window.TISTORY_VARS?.access_token || ''")
                
                if token: break
                time.sleep(1)

            if not token:
                print("❌ 실패: 보안 토큰(CSRF)을 찾을 수 없습니다. (로딩 지연)")
                # 디버깅을 위해 현재 URL 출력
                print(f"   현재 페이지: {page.url}")
                continue

            # 2단계: 서버로 직접 쏘기
            safe_title = title.replace('`', '\\`').replace('$', '\\$').replace('\\', '\\\\')
            safe_content = content.replace('`', '\\`').replace('$', '\\$').replace('\\', '\\\\')

            save_js = f"""
            (async () => {{
                try {{
                    const formData = new FormData();
                    formData.append('title', `{safe_title}`);
                    formData.append('content', `{safe_content}`);
                    formData.append('visibility', '0'); 
                    formData.append('categoryId', '0');
                    formData.append('access_token', '{token}');

                    const res = await fetch('/manage/post/save', {{
                        method: 'POST',
                        body: formData
                    }});
                    const text = await res.text();
                    return res.ok ? "SUCCESS" : "FAIL:" + text;
                }} catch (e) {{
                    return e.toString();
                }}
            }})();
            """

            result = page.evaluate(save_js)
            
            if result == "SUCCESS":
                print(f"✅ 저장 성공: {title[:20]}...")
            else:
                print(f"❌ 오류: {result}")

            time.sleep(5)

        except Exception as e:
            print(f"❌ 시스템 통신 오류: {e}")

    b.close()
    p.stop()
    print("🏁 티스토리 업로드 작업을 모두 마쳤습니다.")

if __name__ == "__main__":
    go()
