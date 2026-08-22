"""共享的 Playwright 浏览器启动器。

automation.py、harvester/creator_map.py、sender/creator_channel.py
三个模块各自启动浏览器的逻辑完全一样，抽到这里统一维护。
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import sync_playwright

from .config import DATA_DIR

logger = logging.getLogger("douyin-spark")

_STATE_PATH = DATA_DIR / "state.json"

_COMMON_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
]


@contextmanager
def open_browser(state_path: Path | str | None = None, **ctx_kwargs):
    """启动 Chromium 并返回 (playwright, browser, context, page)。

    用法::

        with open_browser() as (p, browser, context, page):
            page.goto(url)
            ...

    退出 with 块时自动关闭浏览器和 playwright。
    state_path 默认用 data/state.json；传 None 也走默认值。
    ctx_kwargs 会传给 browser.new_context()，可覆盖 viewport、locale 等。
    """
    state = str(state_path or _STATE_PATH)
    p = sync_playwright().start()
    browser = None
    try:
        browser = p.chromium.launch(headless=True, args=_COMMON_ARGS)
        defaults = {
            "storage_state": state,
            "viewport": {"width": 1366, "height": 768},
        }
        defaults.update(ctx_kwargs)
        context = browser.new_context(**defaults)
        page = context.new_page()
        yield p, browser, context, page
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        try:
            p.stop()
        except Exception:
            pass
