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

    # 쿠키 연동 (TSSESSION 기반)
    raw_cookie = os.environ.get("TISTORY_COOKIE", "").strip()
    if not raw_cookie:
        print("⚠️ TISTORY_COOKIE 환경변수가 비어있습니다.")
        b.close()
        p.stop()
        return

    val = raw_cookie.split("TSSESSION=")[1].split(";")[0] if "TSSESSION=" in raw_cookie else raw_cookie
    c.add_cookies([{"name": "TSSESSION", "value": val, "domain": ".tistory.com", "path": "/"}])

    page = c.new_page()
    
    # 2. 업로드할 원고 리스트 확보 (Markdown 파일)
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

        # 🚨 [레이저 파싱] 제목과 본문 섹션 분리
        title_match = re.search(r'"\[제목\]"\s*:(.*?)"\[본문\]"\s*:', raw_text, re.DOTALL)
        content_match = re.search(r'"\[본문\]"\s*:(.*)', raw_text, re.DOTALL)

        if title_match and content_match:
            title = title_match.group(1).strip()
            content = content_match.group(1).strip()
        else:
            print(f"⚠️ '{f}' 태그 파싱 실패. 원고 구조를 확인하세요.")
            continue

        print(f"🚀 '{title[:15]}...' 서버 직송 시작!")

        try:
            # 1단계: 티스토리 관리자 페이지 진입 (CSRF 토큰 확보용)
            page.goto(f"https://{BLOG_NAME}.tistory.com/manage/post", wait_until="networkidle")
            
            if "login" in page.url:
                print(f"❌ '{title[:15]}' 실패: 쿠키가 만료되었습니다.")
                break

            time.sleep(2)

            # 2단계: 자바스크립트 직접 전송 (에디터 UI 영향 없음)
            safe_title = title.replace('`', '\\`').replace('$', '\\$').replace('\\', '\\\\')
            safe_content = content.replace('`', '\\`').replace('$', '\\$').replace('\\', '\\\\')

            # visibility '0'은 임시저장/비공개 상태
            save_js = f"""
            (async () => {{
                try {{
                    const formData = new FormData();
                    formData.append('title', `{safe_title}`);
                    formData.append('content', `{safe_content}`);
                    formData.append('visibility', '0'); 
                    formData.append('categoryId', '0');

                    const tokenInput = document.querySelector('input[name="access_token"]');
                    if (!tokenInput) return "NO_TOKEN";

                    formData.append('access_token', tokenInput.value);

                    const res = await fetch('/manage/post/save', {{
                        method: 'POST',
                        body: formData
                    }});
                    return res.ok ? "SUCCESS" : "FAIL";
                }} catch (e) {{
                    return e.toString();
                }}
            }})();
            """

            result = page.evaluate(save_js)
            
            if result == "SUCCESS":
                print(f"✅ 저장 성공: {title[:20]}...")
            elif result == "NO_TOKEN":
                print(f"❌ 전송 실패: 보안 토큰을 찾을 수 없습니다.")
            else:
                print(f"❌ 서버 응답 오류: {result}")

            time.sleep(5)

        except Exception as e:
            print(f"❌ 시스템 통신 오류: {e}")

    b.close()
    p.stop()
    print("🏁 티스토리 업로드 작업을 모두 마쳤습니다.")

if __name__ == "__main__":
    go()
