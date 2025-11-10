from __future__ import annotations
from DrissionPage import Chromium, ChromiumPage
import time, random, string, re, csv, os, json, threading
from pathlib import Path
from typing import Optional

from utils.logger import logger
from utils.cf_bypass import CloudflareBypasser
from utils.mail_client import MailClient
from utils.config import load_config

LOGIN_URL = "https://www.jusbrasil.com.br/login"

# ------------------------ util geração de cadastro ------------------------

def gerar_nome_brasileiro():
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
        tamanho = 6
    caracteres = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choices(caracteres, k=tamanho))

def _pause(a=0.6, b=1.6):
    time.sleep(random.uniform(a, b))

def _logado(page: ChromiumPage) -> bool:
    el = page.ele('css=div.topbar-profile, img[class*="avatar_image"], span[class*="avatar_fallback"]', timeout=3)
    if el:
        return True
    html = (page.html or '').lower()
    return any(k in html for k in ('minha conta','perfil','sair'))

# ------------------------ Gerenciador de contas CSV ------------------------

class _AccountsPool:
    def __init__(self, csv_path: str, delimiter: str = '', persist_state: bool = True, state_path: str = 'output/accounts_state.json'):
        self.path = Path(csv_path)
        self.delimiter = delimiter
        self.persist = persist_state
        self.state_path = Path(state_path)
        self._rows: list[tuple[str,str]] = []
        self._idx = 0
        self._lock = threading.Lock()
        self._load()
        self._restore_state()

    def _load(self):
        if not self.path.exists():
            raise FileNotFoundError(f"Arquivo CSV de contas não encontrado: {self.path}")
        # detecta delimitador se necessário
        delim = self.delimiter or None
        with open(self.path, 'r', encoding='utf-8', newline='') as f:
            sample = f.read(2048)
            f.seek(0)
            if not self.delimiter:
                try:
                    sniff = csv.Sniffer().sniff(sample, delimiters=',;|\t')
                    delim = sniff.delimiter
                except Exception:
                    delim = ','
            reader = csv.DictReader(f, delimiter=delim)
            cols = [c.lower() for c in (reader.fieldnames or [])]
            # mapeia nomes
            def pick(*names):
                for n in names:
                    if n in cols:
                        return n
                return None
            c_email = pick('email','login','usuario','user')
            c_senha = pick('senha','password','pass')
            if not c_email or not c_senha:
                raise ValueError(f"CSV deve conter colunas 'email' e 'senha' (ou equivalentes). Cabeçalhos detectados: {cols}")
            self._rows.clear()
            for row in reader:
                e = (row.get(c_email) or '').strip()
                s = (row.get(c_senha) or '').strip()
                if e and s:
                    self._rows.append((e,s))
        if not self._rows:
            raise ValueError("Nenhuma conta válida encontrada no CSV.")

    def _restore_state(self):
        if not self.persist:
            return
        try:
            if self.state_path.exists():
                data = json.loads(self.state_path.read_text(encoding='utf-8') or '{}')
                if str(self.path) == data.get('csv_path'):
                    idx = int(data.get('next_index', 0))
                    if 0 <= idx < len(self._rows):
                        self._idx = idx
        except Exception:
            pass

    def _save_state(self):
        if not self.persist:
            return
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(
                json.dumps({'csv_path': str(self.path), 'next_index': self._idx}, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
        except Exception:
            pass

    def current(self) -> tuple[int, tuple[str,str]]:
        with self._lock:
            return self._idx, self._rows[self._idx]

    def next(self) -> tuple[int, tuple[str,str]]:
        with self._lock:
            self._idx = (self._idx + 1) % len(self._rows)
            self._save_state()
            return self._idx, self._rows[self._idx]

# singleton simples em nível de módulo
_ACCOUNTS: Optional[_AccountsPool] = None
def _get_pool(cfg: dict) -> _AccountsPool:
    global _ACCOUNTS
    auth = cfg.get('auth', {}) or {}
    csv_path = auth.get('accounts_csv') or ''
    if not csv_path:
        raise ValueError("Configuração 'auth.accounts_csv' não definida.")
    if _ACCOUNTS is None or (Path(csv_path) != Path(_ACCOUNTS.path)):
        _ACCOUNTS = _AccountsPool(
            csv_path=csv_path,
            delimiter=(auth.get('accounts_csv_delimiter') or ''),
            persist_state=bool(auth.get('persist_rotation_state', True)),
            state_path=auth.get('rotation_state_path', 'output/accounts_state.json')
        )
    return _ACCOUNTS

# ------------------------ Fluxo: login com e-mail/senha ------------------------

def _login_with_credentials(page: ChromiumPage, email: str, senha: str) -> bool:
    if not email or not senha:
        logger.error("[login] Email ou senha vazios.")
        return False

    # Se já está logado, sai
    if _logado(page):
        return True

    page.get(LOGIN_URL)
    page.wait.doc_loaded()
    if _logado(page):
        return True

    # Preenche email
    e_email = page.ele('xpath://input[@type="email" or @name="email" or contains(translate(@placeholder,"EMAIL","email"),"email") or contains(translate(@aria-label,"EMAIL","email"),"email")][1]', timeout=5)
    if e_email:
        e_email.clear()
        e_email.input(email)
        btn = page.ele('xpath://button[.//text()[contains(., "Entrar") or contains(., "Continuar") or contains(., "Login")]] | //input[@type="submit"]', timeout=3)
        if btn: btn.click()
        page.wait.doc_loaded()
        time.sleep(1.2)

    # Preenche senha
    e_senha = page.ele('xpath://input[@type="password" or @name="password" or contains(translate(@placeholder,"SENHA","senha"),"senha")][1]', timeout=7)
    if e_senha:
        e_senha.clear()
        e_senha.input(senha)
        btn = page.ele('xpath://button[.//text()[contains(., "Entrar") or contains(., "Continuar") or contains(., "Login")]] | //input[@type="submit"]', timeout=5)
        if btn: btn.click()
        page.wait.doc_loaded()
        time.sleep(3.0)

    # Decide baseado no HTML
    html = (page.html or "").lower()
    ok = any(k in html for k in ("sair","minha conta","perfil"))
    return ok

# ------------------------ Fluxo: cadastro (já existente) ------------------------

def _register_new_account(browser: Chromium) -> bool:
    """Fluxo atual de cadastro via email alias + confirmação por e-mail."""

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
    e_ocup.select('Outra profissão')
    
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

# ------------------------ API pública ------------------------

def try_login(browser: Chromium, rotate: bool = False, cfg: Optional[dict] = None) -> bool:
    """
    Modo configurável:
    - auth.mode = 'cadastro' => executa o fluxo de criação de conta (com MailClient).
    - auth.mode = 'login'    => lê o CSV e efetua login com e-mail/senha.
    
    Parâmetros:
      browser: instância Chromium (DrissionPage).
      rotate: quando True e em modo 'login', avança para a PRÓXIMA conta do CSV antes de tentar.
      cfg: opcional; se None, carrega de config.yaml.
    """
    if cfg is None:
        cfg = load_config("config.yaml")
    auth = cfg.get('auth', {}) or {}
    mode = str(auth.get('mode', 'cadastro')).strip().lower()

    if mode in ('cadastro','register','signup'):
        return _register_new_account(browser)

    # ----- modo 'login' com CSV -----
    page = browser.latest_tab
    if _logado(page):
        return True

    pool = _get_pool(cfg)

    # define qual conta usar
    if rotate or not hasattr(browser, "_account_index"):
        idx, (email, senha) = pool.next() if rotate else pool.current()
        browser._account_index = idx
    else:
        idx = getattr(browser, "_account_index", None)
        if idx is None:
            idx, (email, senha) = pool.current()
            browser._account_index = idx
        else:
            # alinhar pool ao índice atual, se necessário
            _, (email, senha) = pool.current()
            if idx != pool._idx:
                with pool._lock:
                    pool._idx = idx
                    pool._save_state()
                _, (email, senha) = pool.current()

    logger.info(f"[login] Tentando login com conta #{browser._account_index + 1} do CSV.")
    browser._mail_client = email
    ok = _login_with_credentials(page, email, senha)
    if ok:
        browser._account_email = email
        return True

    # Tenta uma vez a próxima conta automaticamente
    logger.warning("[login] Falhou. Tentando próxima conta do CSV...")
    idx, (email, senha) = pool.next()
    browser._account_index = idx
    ok = _login_with_credentials(page, email, senha)
    if ok:
        browser._account_email = email
        return True

    return False
