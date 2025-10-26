from DrissionPage import ChromiumPage
import time

LOGIN_URL = "https://www.jusbrasil.com.br/login"

def try_login(page: ChromiumPage, email: str, senha: str) -> bool:
    if not email or not senha:
        return False
    
    logado = page.ele('css=div.topbar-profile, img[class*="avatar_image"], span[class*="avatar_fallback"]', timeout=3)
    if logado:
        return True
    
    page.get(LOGIN_URL)
    page.wait.doc_loaded()
    logado = page.ele('css=div.topbar-profile, img[class*="avatar_image"], span[class*="avatar_fallback"]', timeout=3)
    if logado:
        return True
    
    e_email = page.ele('xpath://input[@type="email" or @name="email" or contains(@placeholder, "e-mail") or contains(@placeholder, "email")][1]', timeout=5)
    if e_email:
        e_email.clear(); e_email.input(email)
        btn = page.ele('xpath://button[.//text()[contains(., "Entrar") or contains(., "Continuar") or contains(., "Login")]] | //input[@type="submit"]', timeout=3)
        if btn: btn.click()
        page.wait.doc_loaded()
        time.sleep(1.5)
    e_senha = page.ele('xpath://input[@type="password" or @name="password" or contains(@placeholder, "senha")][1]', timeout=5)
    if e_senha:
        e_senha.clear(); e_senha.input(senha)
        btn = page.ele('xpath://button[.//text()[contains(., "Entrar") or contains(., "Continuar") or contains(., "Login")]] | //input[@type="submit"]', timeout=3)
        if btn: btn.click()
        page.wait.doc_loaded()
        time.sleep(5)
    html = (page.html or "").lower()
    return ("sair" in html) or ("minha conta" in html) or ("perfil" in html)
