from DrissionPage import Chromium, ChromiumPage
import time, random, string, re
from utils.logger import logger
from utils.cf_bypass import CloudflareBypasser
from utils.mail_client import MailClient

LOGIN_URL = "https://www.jusbrasil.com.br/login"

def gerar_nome_brasileiro():
    """Gera um nome completo com padrões simples do Brasil (nome + sobrenome)."""
    primeiro = random.choice([
        'Ana','Maria','João','Pedro','Lucas','Mateus','Juliana','Carla','Paulo','Rafael',
        'Bruna','Camila','Gabriel','Felipe','Rodrigo','Beatriz','Bianca','Carolina','Larissa','Mariana'
    ])
    sobrenome = random.choice([
        'Silva','Santos','Oliveira','Souza','Rodrigues','Almeida','Lima','Gomes','Ribeiro','Alves',
        'Carvalho','Araújo','Pereira','Ferreira','Costa','Martins','Barbosa','Rocha','Dias','Teixeira'
    ])
    return f"{primeiro} {sobrenome}"

def gerar_senha(tamanho=8):
    if tamanho < 6:
        tamanho = 6  # Garante mínimo
    caracteres = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choices(caracteres, k=tamanho))

def _logado(page: ChromiumPage) -> bool:
    el = page.ele('css=div.topbar-profile, img[class*="avatar_image"], span[class*="avatar_fallback"]', timeout=3)
    if el:
        return True
    html = (page.html or "").lower()
    return ("sair" in html) or ("minha conta" in html) or ("perfil" in html)

def _pause(a=0.6, b=1.6):
    time.sleep(random.uniform(a, b))

def try_login(browser: Chromium) -> bool:
    """Agora realiza CADASTRO por e-mail (alias) em vez de login. Mantém assinatura e retorno booleano.
    Passos:
    - Acessa /login
    - Preenche e envia o e-mail com um alias Gmail
    - Aguarda /cadastro/confirmacao-por-email-enviada
    - Lê e-mail de 'concluir-cadastro@jusbrasil.com.br', extrai link de confirmação e acessa
    - Bypass Cloudflare se necessário e aguarda /cadastro/email
    - Preenche nome, senha e ocupação; envia o formulário
    - Retorna True se sessão estiver ativa no final
    """
    # Se já estiver logado, não faz nada
    login_tab = browser.latest_tab

    if _logado(login_tab):
        return True

    # 1) Abre página de login/cadastro
    login_tab.get(LOGIN_URL)
    login_tab.wait.doc_loaded()

    # 2) Gera alias e envia no input
    mails = MailClient(browser)
    email_gerado = mails.wait_email_generated(timeout=30)
    browser._mail_client = email_gerado

    _pause()
    browser.activate_tab(login_tab)
    e_email = login_tab.ele('css=input[type="email"], input[name*="email" i], input#email', timeout=8)
    if not e_email:
        logger.error('[login] Campo de e-mail não encontrado.')
        return False
    _pause()
    e_email.clear()
    _pause(5.6, 8.6)
    e_email.input(email_gerado)
    _pause(3.6, 6.6)

    btn_continuar = login_tab.ele('xpath://button[.//text()[contains(., "Continuar") or contains(., "Login") or contains(., "Entrar")]] | //input[@type="submit"]', timeout=5)
    if btn_continuar:
        btn_continuar.click()
        login_tab.wait(5)
    login_tab.wait.doc_loaded()
    _pause()

    # Aguarda a URL de confirmação enviada (método oficial)
    try:
        login_tab.wait.url_change('cadastro/confirmacao-por-email-enviada', timeout=30)
    except Exception:
        time.sleep(2)

    # 3) Aguarda e-mail de confirmação e obtém link
    browser.activate_tab(mails.tab)
    msg = mails.wait_verification_message(
        sender_contains='concluir-cadastro@jusbrasil.com.br',
        subject_prefix='Confirme seu endereço',
        timeout=240
    )
    browser.activate_tab(login_tab)
    browser._close_tab(mails.tab)
    if not msg or not msg.get('body'):
        logger.error('[login] E-mail de confirmação não recebido.')
        return False

    body_text = msg['body']
    m = re.search(r'https://www\.jusbrasil\.com\.br/cadastro/email/\S+', body_text)
    if not m:
        logger.error('[login] Link de confirmação não encontrado no e-mail.')
        return False
    confirm_url = m.group(0)
    _pause(5.6, 8.6)
    login_tab.get(confirm_url)

    # 4) Aguardar e tentar bypass Cloudflare se aparecer "Just a moment..."
    time.sleep(1.0)
    try:
        title = (login_tab.title or '').lower()
    except Exception:
        title = ''
    if 'moment' in title:
        CloudflareBypasser(login_tab, max_retries=3).bypass()

    # 5) Aguarda até chegar em /cadastro/email (boa prática)
    try:
        login_tab.wait.url_change('/cadastro/email', timeout=30)
    except Exception:
        pass

    # 6) Checa status 4xx do request de confirmação
    formulario = login_tab.ele('text:Complete seus dados', timeout=30)
    if not formulario:
        logger.error('[login] Formulário de criação de conta nao encontrado.')
        return False

    # 7) Preenche formulário de criação da conta
    nome = gerar_nome_brasileiro()
    senha_final = gerar_senha(10)

    e_nome = login_tab.ele('#FormFieldset-name', timeout=10)
    if not e_nome:
        logger.error('[login] Campo nome não encontrado.')
        return False
    _pause()
    e_nome.clear() 
    _pause()
    e_nome.input(nome)
    _pause(2.6, 5.6)

    e_senha = login_tab.ele('#FormFieldset-password', timeout=10)
    if not e_senha:
        logger.error('[login] Campo senha não encontrado.')
        return False
    _pause()
    e_senha.clear()
    _pause()
    e_senha.input(senha_final)
    _pause(2.6, 5.6)

    e_ocup = login_tab.ele('#FormFieldset-mainOccupation', timeout=10)
    if e_ocup and getattr(e_ocup, 'select', None):
        try:
            _pause()
            options = e_ocup.select.options
            total = len(options) if options else 0
            if total > 1:
                idx = random.randint(1, total - 1)
                e_ocup.select(idx)
            else:
                e_ocup.select('Outra profissão')
        except Exception:
            pass

    _pause()
    btn_submit = login_tab.ele('css=button[data-testid="submit-button"], button.SubmitButton[type="submit"], button[type="submit"]', timeout=8)
    if btn_submit:
        btn_submit.click()
        try:
            login_tab.wait.url_change('acompanhamentos/processos', timeout=30)
        except Exception:
            time.sleep(5)

    # 8) Verifica sessão ativa
    return _logado(login_tab)
