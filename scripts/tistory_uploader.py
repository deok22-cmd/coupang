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
    # 1. Playwright 시작 및 브라우저 실행
    p = sync_playwright().start()
    b = p.chromium.launch(headless=True) # 서버 환경에서는 True 권장
    c = b.new_context()

    # 쿠키 연동 (TSSESSION 기반)
    raw_cookie = os.environ.get("TISTORY_COOKIE", "").strip()
    if not raw_cookie:
        print("⚠️ TISTORY_COOKIE 환경변수가 비어있습니다.")
        b.close()
        p.stop()
        return

    # 쿠키 값 파싱 (TSSESSION= 뒷부분 추출)
    val = raw_cookie.split("TSSESSION=")[1].split(";")[0] if "TSSESSION=" in raw_cookie else raw_cookie
    
    # 세션 쿠키 수동 주입
    c.add_cookies([
        {"name": "TSSESSION", "value": val, "domain": ".tistory.com", "path": "/"}
    ])

    page = c.new_page()
    
    # 2. 업로드할 원고 리스트 확보
    md_list = glob.glob(f"blog_drafts/{today}/tistory/*.md")
    md_list.sort()

    if not md_list:
        print(f"🏕️ [{today}] 업로드할 원고가 없습니다.")
        b.close()
        p.stop()
        return

    # 3. 원고 파일별 반복 처리
    for f in md_list:
        with open(f, 'r', encoding='utf-8') as fp:
            raw_text = fp.read()
        
        if not raw_text:
            continue

        # 정규식으로 제목과 본문 섹션 분리
        title_match = re.search(r'"\[제목\]"\s*:(.*?)"\[본문\]"\s*:', raw_text, re.DOTALL)
        content_match = re.search(r'"\[본문\]"\s*:(.*)', raw_text, re.DOTALL)

        if title_match and content_match:
            title = title_match.group(1).strip()
            content = content_match.group(1).strip()
        else:
            print(f"⚠️ '{f}' 파싱 실패 (태그 없음). 건너뜁니다.")
            continue

        # 🚨 [최종 보스 격파] 에디터 UI 조작 없이 서버로 다이렉트 전송 기술 적용
        try:
            # 관리자 페이지 진입 (세션 및 CSRF 토큰 확보용)
            page.goto(f"https://{BLOG_NAME}.tistory.com/manage/post")
            page.wait_for_load_state('networkidle')
            time.sleep(2)

            # 자바스크립트 내 특수문자 충돌 방지용 처리
            safe_title = title.replace('`', '\\`').replace('$', '\\$')
            safe_content = content.replace('`', '\\`').replace('$', '\\$')

            # 티스토리 내부 API(/manage/post/save)로 폼 데이터를 직접 쏘는 JS 코드
            js_code = f"""
            (async () => {{
                const formData = new FormData();
                formData.append('title', `{safe_title}`);
                formData.append('content', `{safe_content}`);
                formData.append('visibility', '0'); // 비공개/임시저장 상태
                formData.append('categoryId', '0'); // 기본 카테고리 설정

                // 티스토리 페이지 내 숨겨진 CSRF 액세스 토큰 탈취
                const tokenInput = document.querySelector('input[name="access_token"]');
                if (tokenInput) {{
                    formData.append('access_token', tokenInput.value);
                    
                    // 서버로 다이렉트 POST 전송 실행
                    await fetch('/manage/post/save', {{
                        method: 'POST',
                        body: formData
                    }});
                    return true;
                }}
                return false;
            }})();
            """

            # 브라우저 컨텍스트 내에서 전송 실행
            success = page.evaluate(js_code)
            
            if success:
                print(f"✅ 서버 다이렉트 전송 완료: {title[:15]}...")
            else:
                print(f"❌ '{title[:15]}' 전송 실패: 액세스 토큰을 찾을 수 없습니다.")
                
            time.sleep(5) # 전송 간격 유지

        except Exception as e:
            print(f"❌ '{title[:15]}' 처리 중 오류 발생: {e}")

    # 4. 자원 정리 및 종료
    b.close()
    p.stop()
    print("🚀 모든 작업을 무사히 마쳤습니다.")

if __name__ == "__main__":
    go()
