"""浏览器冒烟：登录 → 上传自拍 → 选模板 → 生成 → 结果画廊（移动端视口截图）。

前置：后端 :8000 与前端 :5173 已启动。
"""
import os

import httpx
from PIL import Image
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5173"
SHOT = os.path.join(os.path.dirname(__file__), ".smoke")
os.makedirs(SHOT, exist_ok=True)
PHONE = "13600001111"

# 生成一张测试自拍
img_path = os.path.join(SHOT, "selfie.jpg")
Image.new("RGB", (720, 960), (124, 112, 102)).save(img_path, "JPEG")

errors: list[str] = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1.5)
    page.on("console", lambda m: errors.append(f"[console] {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"[pageerror] {e}"))

    # 1. 落地页
    page.goto(BASE, wait_until="networkidle")
    page.screenshot(path=os.path.join(SHOT, "01-landing.png"), full_page=True)
    print("01 landing title ok:", "AI 展示面" in page.title())

    # 2. 登录（dev 模式验证码自动填充）
    page.click("text=登录")
    page.wait_for_selector(".modal", timeout=5000)
    page.fill("input[placeholder=手机号]", PHONE)
    page.click("text=获取验证码")
    code_val = ""
    for _ in range(15):
        page.wait_for_timeout(300)
        code_val = page.input_value("input[placeholder=验证码]")
        if code_val:
            break
    if not code_val:  # 兜底：从 dev-code 接口取
        code_val = httpx.post(BASE + "/api/v1/auth/dev-code", json={"phone": PHONE}).json()["data"]["code"]
        page.fill("input[placeholder=验证码]", code_val)
    assert code_val, "验证码未获取到"
    page.click("text=登录 / 注册")
    page.wait_for_timeout(1000)
    print("02 login chip count:", page.locator(".chip--gold").count())

    # 3. 工作台：上传自拍
    page.goto(BASE + "/workspace", wait_until="networkidle")
    page.locator("input[type=file]").nth(0).set_input_files(img_path)
    page.wait_for_timeout(1800)  # 压缩+直传
    print("03 uploader has preview:", page.locator(".uploader img").count())

    # 4. 选模板
    page.locator(".tpl-card").first.click()
    page.screenshot(path=os.path.join(SHOT, "04-workspace.png"), full_page=True)

    # 5. 生成并等待结果页
    page.locator(".generate-bar .btn").click()
    page.wait_for_url("**/result/**", timeout=15000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(6000)  # 等 mock 生成完成
    page.screenshot(path=os.path.join(SHOT, "05-result.png"), full_page=True)
    print("05 result shots:", page.locator(".shot").count())

    # 6. 定价页
    page.goto(BASE + "/pricing", wait_until="networkidle")
    page.screenshot(path=os.path.join(SHOT, "06-pricing.png"), full_page=True)
    print("06 pricing unlock card:", page.locator(".unlock-card").count())

    browser.close()

print("console/page errors:", errors or "none")