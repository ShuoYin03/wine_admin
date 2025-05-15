#!/usr/bin/env python3
import asyncio
import json
import re
import sys
from playwright.async_api import async_playwright

URL = "https://www.sothebys.com/en/buy/auction/2025/distilled-whisky-moutai-2"
COOKIES_FILE = "../../wine_spider/wine_spider/login_state/sothebys_cookies.json"

async def get_access_token(url, cookies):
    token_holder = {"token": None}
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context()
        if cookies:
            await context.add_cookies(cookies)
        page = await context.new_page()

        async def handle_response(response):
            if response.url.startswith("https://accounts.sothebys.com/authorize"):
                try:
                    text = await response.text()
                    m = re.search(r'"access_token"\s*:\s*"([^"\\]+)"', text)
                    if m:
                        token_holder["token"] = m.group(1)
                        print(f"Extracted token from response: {token_holder['token']}")
                except Exception:
                    pass

        page.on("response", handle_response)

        # 导航到目标页面
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # 等待 token 提取（最多 15 秒）
        start = asyncio.get_event_loop().time()
        while token_holder["token"] is None and asyncio.get_event_loop().time() - start < 15:
            await asyncio.sleep(0.5)

        await context.close()
        await browser.close()

    return token_holder.get("token")


def main():
    try:
        with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            cookies = data.get('cookies', data) if isinstance(data, dict) else data
    except Exception as e:
        print(f"无法加载 cookies 文件 '{COOKIES_FILE}': {e}", file=sys.stderr)
        sys.exit(1)

    token = asyncio.run(get_access_token(URL, cookies))
    if token:
        print(token)
    else:
        print("未能提取到 access_token", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
