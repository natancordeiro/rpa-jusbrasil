import time
from DrissionPage import ChromiumPage
from utils.logger_config import logger

class CloudflareBypasser:
    def __init__(self, driver: ChromiumPage, max_retries=-1, log=True):
        self.driver = driver
        self.max_retries = max_retries
        self.log = log

    def search_recursively_shadow_root_with_iframe(self,ele):
        if ele.shadow_root:
            if ele.shadow_root.child().tag == "iframe":
                return ele.shadow_root.child()
        else:
            for child in ele.children():
                result = self.search_recursively_shadow_root_with_iframe(child)
                if result:
                    return result
        return None

    def search_recursively_shadow_root_with_cf_input(self,ele):
        if ele.shadow_root:
            if ele.shadow_root.ele("tag:input"):
                return ele.shadow_root.ele("tag:input")
        else:
            for child in ele.children():
                result = self.search_recursively_shadow_root_with_cf_input(child)
                if result:
                    return result
        return None
    
    def locate_cf_button(self):
        button = None
        self.driver.ele("tag:input", timeout=20)
        eles = self.driver.eles("tag:input")
        for ele in eles:
            if "name" in ele.attrs.keys() and "type" in ele.attrs.keys():
                if "turnstile" in ele.attrs["name"] and ele.attrs["type"] == "hidden":
                    button = ele.parent(timeout=20).shadow_root.child()("tag:body").shadow_root("tag:input")
                    break
            
        if button:
            return button
        else:
            return None

    def log_message(self, message):
        if self.log:
            print(message)

    def click_verification_button(self):
        try:
            button = self.locate_cf_button()
            if button:
                # self.log_message("Verification button found. Attempting to click.")
                button.click()

        except Exception as e:
            logger.error(f"Error clicking verification button: {e}")

    def is_bypassed(self):
        try:
            title = self.driver.title.lower()
            return "just a moment" not in title or "Um momento" not in title
        except Exception as e:
            # self.log_message(f"Error checking page title: {e}")
            return False

    def bypass(self):
        
        try_count = 0

        while not self.is_bypassed():
            if 0 < self.max_retries + 1 <= try_count:
                logger.error("Exceeded maximum retries. Bypass failed.")
                break

            # self.log_message(f"Attempt {try_count + 1}: Verification page detected. Trying to bypass...")
            self.click_verification_button()

            try_count += 1
            time.sleep(2)

        if self.is_bypassed():
            logger.info("Bypass successful.")
        else:
            logger.error("Bypass failed.")
