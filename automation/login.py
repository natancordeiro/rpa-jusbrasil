from DrissionPage import ChromiumPage
import time, os, random, string, re
from utils.logger import logger
from utils.config import load_config
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

def try_login(page: ChromiumPage, email: str, senha: str) -> bool:
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
    if _logado(page):
        return True

    cfg = load_config("config.yaml")
    mail_user = os.getenv('MAIL_USER_EMAIL') or cfg.get('mail_user_email', '')
    mail_pass = os.getenv('MAIL_APP_PASSWORD') or cfg.get('mail_app_password', '')
    imap_server = os.getenv('MAIL_IMAP_SERVER') or cfg.get('imap_server', 'imap.gmail.com')
    if not mail_user or not mail_pass:
        logger.error('[login] Configure MAIL_USER_EMAIL e MAIL_APP_PASSWORD (ou mail_user_email/mail_app_password em config.yaml).')
        return False

    # 1) Abre página de login/cadastro
    page.get(LOGIN_URL)
    page.wait.doc_loaded()

    # 2) Gera alias e envia no input
    client = MailClient(user_email=mail_user, app_password=mail_pass, imap_server=imap_server)
    client.connect()
    alias = client.gerar_alias_gmail()

    e_email = page.ele('css=input[type="email"], input[name*="email" i], input#email', timeout=8)
    if not e_email:
        logger.error('[login] Campo de e-mail não encontrado.')
        return False
    e_email.clear(); e_email.input(alias)

    btn_continuar = page.ele('xpath://button[.//text()[contains(., "Continuar") or contains(., "Login") or contains(., "Entrar")]] | //input[@type="submit"]', timeout=5)
    if btn_continuar:
        btn_continuar.click()
    page.wait.doc_loaded()

    # Aguarda a URL de confirmação enviada (método oficial)
    try:
        page.wait.url_change('cadastro/confirmacao-por-email-enviada', timeout=30)
    except Exception:
        time.sleep(2)

    # 3) Aguarda e-mail de confirmação e obtém link
    msg = client.wait_for_new_message(
        'concluir-cadastro@jusbrasil.com.br',
        subject_prefix='',
        check_interval=3,
        on_match='delete'
    )
    if not msg or not msg.get('body'):
        logger.error('[login] E-mail de confirmação não recebido.')
        return False

    body_text = msg['body']
    m = re.search(r'https://www\.jusbrasil\.com\.br/cadastro/email/\S+', body_text)
    if not m:
        logger.error('[login] Link de confirmação não encontrado no e-mail.')
        return False
    confirm_url = m.group(0)
    page.get(confirm_url)

    # 4) Aguardar e tentar bypass Cloudflare se aparecer "Just a moment..."
    time.sleep(1.0)
    try:
        title = (page.title or '').lower()
    except Exception:
        title = ''
    if 'moment' in title:
        CloudflareBypasser(page, max_retries=3).bypass()

    # 5) Aguarda até chegar em /cadastro/email (boa prática)
    try:
        page.wait.url_change('/cadastro/email', timeout=30)
    except Exception:
        pass

    # 6) Checa status 4xx do request de confirmação
    formulario = page.ele('text:Complete seus dados', timeout=30)
    if not formulario:
        logger.error('[login] Formulário de criação de conta nao encontrado.')
        return False

    # 7) Preenche formulário de criação da conta
    nome = gerar_nome_brasileiro()
    senha_final = gerar_senha(10)

    e_nome = page.ele('#FormFieldset-name', timeout=10)
    if not e_nome:
        logger.error('[login] Campo nome não encontrado.')
        return False
    e_nome.clear(); e_nome.input(nome)

    e_senha = page.ele('#FormFieldset-password', timeout=10)
    if not e_senha:
        logger.error('[login] Campo senha não encontrado.')
        return False
    e_senha.clear(); e_senha.input(senha_final)

    e_ocup = page.ele('#FormFieldset-mainOccupation', timeout=10)
    if e_ocup and getattr(e_ocup, 'select', None):
        try:
            options = e_ocup.select.options
            total = len(options) if options else 0
            if total > 1:
                idx = random.randint(1, total - 1)
                e_ocup.select(idx)
            else:
                e_ocup.select('Outra profissão')
        except Exception:
            pass

    btn_submit = page.ele('css=button[data-testid="submit-button"], button.SubmitButton[type="submit"], button[type="submit"]', timeout=8)
    if btn_submit:
        btn_submit.click()
        try:
            page.wait.url_change('acompanhamentos/processos', timeout=30)
        except Exception:
            time.sleep(5)

    # 8) Verifica sessão ativa
    return _logado(page)
