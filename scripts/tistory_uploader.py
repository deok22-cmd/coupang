import os
import glob
import time
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

# ★ 블로그 설정 및 한국 표준시(KST) 시간 설정
BLOG_NAME = "tentme"
kst = timezone(timedelta(hours=9))
today = datetime.now(kst).strftime("%y%m%d")

def go():
    # 1. Playwright 시작 및 브라우저 실행
    p = sync_playwright().start()
    b = p.chromium.launch(headless=True) # 화면을 보고 싶으면 False로 설정
    c = b.new_context()

    # 쿠키 연동 (TSSESSION 기반)
    raw_cookie = os.environ.get("TISTORY_COOKIE", "").strip()
    if not raw_cookie:
        print("⚠️ TISTORY_COOKIE 환경변수가 비어있습니니다.")
        b.close()
        p.stop()
        return

    # 쿠키 값 파싱 로직
    val = raw_cookie.split("TSSESSION=")[1].split(";")[0] if "TSSESSION=" in raw_cookie else raw_cookie
    
    c.add_cookies([
        {"name": "TSSESSION", "value": val, "domain": ".tistory.com", "path": "/"},
        {"name": "TSSESSION", "value": val, "domain": f"{BLOG_NAME}.tistory.com", "path": "/"}
    ])

    page = c.new_page()
    
    # 2. 업로드할 원고 리스트 확보
    md_list = glob.glob(f"blog_drafts/{today}/tistory/*.md")
    md_list.sort() # 순서대로 발행하기 위해 정렬

    if not md_list:
        print(f"🏕️ [{today}] 업로드할 원고가 없습니다.")
        b.close()
        p.stop()
        return

    # 3. 원고별 반복 업로드 및 비공개 발행
    for f in md_list:
        with open(f, 'r', encoding='utf-8') as fp:
            raw_text = fp.read() # 파일을 통째로 한 번에 읽기
        
        if not raw_text:
            continue

        # 🚨 [수정 1] 첫 번째 '엔터(\n)'를 기준으로 제목과 본문을 확실하게 분리 (1회만 분리)
        split_text = raw_text.split('\n', 1)

        # 첫 번째 라인은 제목 (불필요한 꼬리표 및 마크다운 표시 제거)
        raw_title = split_text[0].strip()
        title = raw_title.replace("[티스토리 SEO 원고 A] ", "").replace("[티스토리 SEO 원고 B] ", "").replace("[티스토리 SEO 원고 C] ", "").replace("[티스토리 SEO 원고 D] ", "")
        title = title.replace("# ", "")

        # 두 번째 라인이 있으면 본문, 없으면 빈칸 (내용 추출)
        content = split_text[1].strip() if len(split_text) > 1 else ""

        try:
            # 관리자 글쓰기 페이지 진입
            page.goto(f"https://{BLOG_NAME}.tistory.com/manage/post")
            page.wait_for_load_state('networkidle')
            time.sleep(3)

            # 제목 입력 필드 찾기 및 입력
            page.locator('textarea[placeholder="제목을 입력하세요"], textarea.textarea_tit').first.fill(title)
            time.sleep(1)

            # 에디터 모드를 마크다운으로 변경
            page.locator('#editor-mode-layer-btn-open').click(force=True)
            page.locator('#editor-mode-markdown').click(force=True)
            time.sleep(1)
            
            # 마크다운 텍스트 영역에 본문 채우기
            page.locator('.CodeMirror textarea').first.fill(content, force=True)

            # 4. 이미지 자동 매칭 및 업로드
            file_basename = os.path.basename(f)
            try:
                item_symbol = file_basename.split('_')[2] 
            except IndexError:
                item_symbol = "A"

            imgs = glob.glob(f"images/{today}/{item_symbol}_{today}_tistory_*.png")
            if imgs:
                # 파일 업로드 컨트롤러에 이미지 경로 전달
                page.locator('input[type="file"]').set_input_files(imgs)
                print(f"📸 {item_symbol} 상품 이미지 {len(imgs)}장 첨부 완료!")
                time.sleep(3)

            # 🚨 [수정 2] 사이드바 레이어가 열릴 때까지 충분히 대기 후 비공개 설정
            # 1단계: 하단 '완료' 버튼 클릭
            page.locator('#publish-layer-btn').click(force=True)
            time.sleep(2) # 사이드바 애니메이션(스르륵 열리는 시간) 절대 대기!

            # 2단계: '비공개' 라디오 버튼의 라벨(Label)을 더 확실하게 클릭
            page.locator('label[for="open20"]').click(force=True)
            time.sleep(1)

            # 3단계: 최종 '발행' 버튼 클릭!
            page.locator('button#publish-btn').click(force=True)

            print(f"✅ 완료: {title} (비공개 발행 완료)")
            
            # 다음 파일 작업을 위한 안정적인 대기 시간
            time.sleep(5)

        except Exception as e:
            print(f"❌ '{file_basename}' 프로젝트 처리 중 오류 발생: {e}")

    # 4. 프로세스 종료
    b.close()
    p.stop()
    print("🚀 모든 티스토리 자동 업로드 작업을 완료했습니다.")

if __name__ == "__main__":
    go()
