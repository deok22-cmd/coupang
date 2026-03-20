import os, glob, time
from datetime import datetime
from playwright.sync_api import sync_playwright
today = datetime.now().strftime("%y%m%d")
def go():
    p = sync_playwright().start()
    b = p.chromium.launch(headless=True)
    c = b.new_context()
    c.add_cookies([{"name":"TSSESSION","value":os.environ.get("TISTORY_COOKIE","").replace("TSSESSION=","").replace(";","").strip(),"domain":".tistory.com","path":"/"}])
    page = c.new_page()
    for f in glob.glob(f"blog_drafts/{today}/tistory/*.md"):
        with open(f, 'r', encoding='utf-8') as fp: lines = fp.readlines()
        if not lines: continue
        title = lines[0].strip().split("] ")[-1] if "] " in lines[0] else lines[0].strip()
        content = "".join(lines[1:]).strip()
        page.goto("https://tentme.tistory.com/manage/post")
        page.wait_for_load_state('networkidle')
        time.sleep(3)
        page.get_by_placeholder("제목을 입력하세요").fill(title)
        page.locator('#editor-mode-layer-btn-open').click()
        page.locator('#editor-mode-markdown').click()
        page.locator('.CodeMirror textarea').fill(content)
        imgs = glob.glob(f"images/{today}/{os.path.basename(f).split('_')[2]}_{today}_tistory_*.png")
        if imgs: page.locator('input[type="file"]').set_input_files(imgs)
        time.sleep(3)
        page.locator('button.btn-draft').click()
        time.sleep(15)
    b.close()
    p.stop()
go()
