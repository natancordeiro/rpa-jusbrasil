from DrissionPage import Chromium, ChromiumOptions, ChromiumPage
import os
from typing import Optional

class BrowserFactory:
    """Cria e recria navegadores isolados (um por thread) com auto_port() e extensão de proxy (opcional)."""

    @staticmethod
    def new_browser(cfg: dict, user_data_dir: Optional[str] = None) -> Chromium:
        co = ChromiumOptions()
        co.auto_port()

        if cfg.get("headless", False):
            co.headless(True)

        if user_data_dir:
            co.set_user_data_path(user_data_dir)

        if cfg.get("usar_proxy") and cfg.get("proxy_extension_path"):
            p = cfg["proxy_extension_path"]
            if os.path.exists(p):
                co.add_extension(p)

        browser = Chromium(addr_or_opts=co)
        return browser.latest_tab

    @staticmethod
    def recreate(prev_page: ChromiumPage, use_proxy: bool, proxy_extension_path: str | None) -> ChromiumPage:
        try:
            prev_page.browser.quit()
        except Exception:
            pass
        return BrowserFactory.new_browser(use_proxy, proxy_extension_path)