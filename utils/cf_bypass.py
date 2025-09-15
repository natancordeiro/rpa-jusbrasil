import time
from DrissionPage import ChromiumPage
from utils.logger import logger

class CloudflareBypasser:
    def __init__(self, driver: ChromiumPage, max_retries: int = -1, log: bool = True):
        self.driver = driver
        self.max_retries = max_retries
        self.log = log

    def search_recursively_shadow_root_with_iframe(self, ele):
        if not ele:
            return None
        try:
            if ele.shadow_root:
                if ele.shadow_root.child().tag == 'iframe':
                    return ele.shadow_root.child()
            else:
                for child in ele.children():
                    result = self.search_recursively_shadow_root_with_iframe(child)
                    if result:
                        return result
        except Exception:
            pass
        return None

    def search_recursively_shadow_root_with_cf_input(self, ele):
        if not ele:
            return None
        try:
            if ele.shadow_root:
                if ele.shadow_root.ele('tag:input'):
                    return ele.shadow_root.ele('tag:input')
            else:
                for child in ele.children():
                    result = self.search_recursively_shadow_root_with_cf_input(child)
                    if result:
                        return result
        except Exception:
            pass
        return None

    def locate_cf_button(self):
        button = None
        try:
            eles = self.driver.eles('tag:input')
            for ele in eles:
                try:
                    attrs = ele.attrs
                    if attrs and ('name' in attrs.keys()) and ('type' in attrs.keys()):
                        if 'turnstile' in attrs.get('name','') and attrs.get('type','') == 'hidden':
                            button = ele.parent(timeout=20).shadow_root.child()('tag:body').shadow_root('tag:input')
                            break
                except Exception:
                    continue
        except Exception:
            pass
        return button

    def log_message(self, message):
        if self.log:
            print(message)

    def click_verification_button(self):
        try:
            button = self.locate_cf_button()
            if button:
                button.click()
        except Exception as e:
            logger.error(f'Erro ao clicar no botão de verificação do Captcha: {e}')

    def is_bypassed(self):
        try:
            title = (self.driver.title or '').lower()
            return 'moment' not in title
        except Exception:
            return False

    def bypass(self):
        try_count = 0
        while not self.is_bypassed():
            if 0 < self.max_retries + 1 <= try_count:
                logger.error('Excedeu o número máximo de tentativas no captcha.')
                return False
            self.click_verification_button()
            try_count += 1
            time.sleep(2)
        if self.is_bypassed():
            logger.info('Bypass do Cloudflare bem-sucedido.')
            return True
        else:
            logger.error('Falha ao contornar o Cloudflare.')
            return False
