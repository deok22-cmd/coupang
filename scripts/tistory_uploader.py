import os
import glob
import time
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

# ★ 블로그 설정 및 한국 표준시(KST) 기반 오늘 날짜 설정
BLOG_NAME = "tentme"
kst = timezone(timedelta(hours=9))
today = datetime.now(kst).strftime("%y%m%d")

def go():
    # 1. Playwright 시작 및 브라우저 실행
    p = sync_playwright().start()
    b = p.chromium.launch(headless=True) # 화면을 보고 싶으면 False로 변경
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
    
    # 2. 업로드할 원고 리스트 확보 (Markdown 파일)
    md_list = glob.glob(f"blog_drafts/{today}/tistory/*.md")
    md_list.sort() # 순무서대로 처리를 위해 알파벳순 정렬

    if not md_list:
        print(f"🏕️ [{today}] 업로드할 원고가 없습니다.")
        b.close()
        p.stop()
        return

    # 3. 원고 파일별 반복 업로드 및 비공개 발행
    for f in md_list:
        with open(f, 'r', encoding='utf-8') as fp:
            raw_text = fp.read() # 파일 전체 내용 읽기
        
        if not raw_text:
            continue

        # 🚨 [해결 1] 제목과 본문의 경계가 모호할 때 '공정위 문구'를 기준으로 자르기
        if "제공받습니다." in raw_text:
            # '제공받습니다.' 글자가 끝나는 지점까지를 제목 영역으로 간주
            split_text = raw_text.split("제공받습니다.", 1)
            raw_title = split_text[0] + "제공받습니다." # 잘린 텍스트 복원
            content = split_text[1].strip() # 이후 전체 내용을 본문으로 처리
        else:
            # 문구가 없을 경우 첫 번째 엔터(\n)를 기준으로 자르기
            split_text = raw_text.split('\n', 1)
            raw_title = split_text[0]
            content = split_text[1].strip() if len(split_text) > 1 else ""

        # 제목에서 불필요한 라벨 및 마크다운 표시 제거
        title = raw_title.replace("[티스토리 SEO 원고 A]", "").replace("[티스토리 SEO 원고 B]", "")
        title = title.replace("[티스토리 SEO 원고 C]", "").replace("[티스토리 SEO 원고 D]", "").strip()
        title = title.replace("# ", "")

        try:
            # 관리자 글쓰기 페이지 진입
            page.goto(f"https://{BLOG_NAME}.tistory.com/manage/post")
            page.wait_for_load_state('networkidle')
            time.sleep(3)

            # 제목 입력 필드에 데이터 채우기
            page.locator('textarea[placeholder="제목을 입력하세요"], textarea.textarea_tit').first.fill(title)
            time.sleep(1)

            # 에디터 모드를 마크다운으로 변경
            page.locator('#editor-mode-layer-btn-open').click(force=True)
            page.locator('#editor-mode-markdown').click(force=True)
            time.sleep(1)
            
            # 마크다운 텍스트 영역에 본문 입력
            page.locator('.CodeMirror textarea').first.fill(content, force=True)

            # 4. 이미지 자동 매칭 및 첨부
            # 파일 이름 규칙 (예: tistory_post_A_260320.md)에서 상품 기호 추출
            file_basename = os.path.basename(f)
            try:
                item_symbol = file_basename.split('_')[2] 
            except IndexError:
                item_symbol = "A"

            imgs = glob.glob(f"images/{today}/{item_symbol}_{today}_tistory_*.png")
            if imgs:
                # 파일 입력 요소에 이미지 파일 경로(목록) 주입
                page.locator('input[type="file"]').set_input_files(imgs)
                print(f"📸 {item_symbol} 상품 이미지 {len(imgs)}장 첨부 완료!")
                time.sleep(3)

            # 🚨 [해결 2] 발행 레이어를 열고 '비공개'를 직접 찾아 클릭하는 로직
            # 1단계: 우측 하단 '완료' 버튼 클릭 (레이어 오픈)
            page.locator('#publish-layer-btn').click(force=True)
            time.sleep(3) # 레이어가 완전히 뜨는 시간을 3초로 넉넉히 부여

            # 2단계: '비공개'라는 글자가 포함된 Label을 강제 클릭 (텍스트 매칭 기반)
            page.locator('label:has-text("비공개")').click(force=True)
            time.sleep(1)

            # 3단계: 최종 '발행' 버튼 클릭!
            page.locator('button#publish-btn').click(force=True)

            # 진행 상황 요약 로그 (상태바에 제목 20자만 출력)
            print(f"✅ 발행 완료: {title[:20]}...")
            
            # 발행 후 시스템 안정화를 위한 일시 정지 (5초)
            time.sleep(5)

        except Exception as e:
            print(f"❌ '{file_basename}' 처리 중 에러 발생: {e}")

    # 4. 프로세스 완전 종료
    b.close()
    p.stop()
    print("🚀 모든 작업을 무사히 마쳤습니다.")

if __name__ == "__main__":
    go()
