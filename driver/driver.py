import os
import logging
import sys
import subprocess
import shutil
import signal
import atexit
import time
from DrissionPage import Chromium, ChromiumOptions
from utils.global_functions import carregar_configuracao

class Driver():
    """Classe para gerenciar o WebDriver e as opções do navegador."""
    _mitm_proc = None

    def __init__(self, browser='chrome', headless=False, incognito=False, download_path='', remote=False, desabilitar_carregamento_imagem=False):
        """
        Inicializa um objeto Driver.

        Args:
            browser (str): O navegador a ser utilizado (padrão: 'chrome').
            headless (bool): Define se o navegador será executado em modo headless (padrão: False).
            incognito (bool): Define se o navegador será iniciado no modo incognito (padrão: False).
            download_path (str): O caminho para o diretório de downloads (padrão: '').
            remote (bool): Define se a execução será remota (padrão: False).
            desabilitar_carregamento_imagem (bool): Define se o carregamento de imagens será desabilitado (padrão: False).
        """
        if download_path == '':
            download_path = self.get_download_dir()

        if remote:
            if browser == 'chrome':
                self.make_chrome(headless, incognito, download_path, desabilitar_carregamento_imagem, remote)
            else:
                logging.error(f'{browser} não suportado para acesso remoto.')
                sys.exit(1)
        else:
            if browser == 'chrome':
                self.make_chrome(headless, incognito, download_path, desabilitar_carregamento_imagem, remote)

    def _start_mitmdump(self, upstream_host, upstream_port, user, pwd,
                        listen_host="127.0.0.1", listen_port=8787):
        """Sobe um mitmdump local sem autenticação e faz upstream para o proxy com user:pass."""

        exe = shutil.which("mitmdump")
        if not exe:
            # Windows: tenta na pasta Scripts do Python atual
            cand = os.path.join(os.path.dirname(sys.executable), "Scripts", "mitmdump.exe")
            if os.path.exists(cand):
                exe = cand
        if not exe:
            raise RuntimeError("mitmdump não encontrado mesmo após instalação.")

        cmd = [
            exe,
            "--listen-host", listen_host,
            "--listen-port", str(listen_port),
            "--mode", f"upstream:http://{upstream_host}:{upstream_port}",
            "--upstream-auth", f"{user}:{pwd}",
            "-q",
        ]
        # CREATE_NEW_PROCESS_GROUP para facilitar terminar no Windows
        creationflags = 0x00000200 if os.name == "nt" else 0
        self._mitm_proc = subprocess.Popen(cmd, creationflags=creationflags)

        # encerra no final do processo Python
        atexit.register(self._stop_mitmproxy)

        # (opcional) espera 1s para estar pronto
        time.sleep(1)

    def _stop_mitmproxy(self):
        """Desliga o mitmdump se estiver rodando."""
        p = getattr(self, "_mitm_proc", None)
        if p and p.poll() is None:
            try:
                if os.name == "nt":
                    p.send_signal(signal.CTRL_BREAK_EVENT)
                    time.sleep(1)
                p.terminate()
            except Exception:
                pass
            self._mitm_proc = None
    
    def get_download_dir(self):
        """
        Retorna o diretório padrão de downloads do sistema operacional.

        Returns:
            str: O diretório de downloads padrão.
        """
        if os.name == 'nt':
            return os.path.join(os.environ.get('USERPROFILE'), 'Downloads')
        elif os.name == 'posix':
            return os.path.join(os.path.expanduser('~'), 'Downloads')
        else:
            return None

    
    def make_chrome(self, headless, incognito, download_path, desabilitar_carregamento_imagem, remote):
        """
        Configura o navegador Chrome.

        Args:
            headless (bool): Define se o navegador será executado em modo headless.
            incognito (bool): Define se o navegador será iniciado no modo incognito.
            download_path (str): O caminho para o diretório de downloads.
            desabilitar_carregamento_imagem (bool): Define se o carregamento de imagens será desabilitado.
            remote (bool): Define se a execução será remota.
        """
        config = carregar_configuracao('config.yaml')
        salvar_login = config.get('salvar_login', False)
        usar_proxy = config.get('usar_proxy', False)

        if usar_proxy:
            proxy_host = config.get("proxy_host")
            proxy_port = int(config.get("proxy_port", 0) or 0)
            proxy_user = config.get("proxy_user")
            proxy_pass = config.get("proxy_pass")
            if not (proxy_host and proxy_port and proxy_user and proxy_pass):
                raise ValueError("Configuração de proxy inválida no config.yaml (proxy_host/port/user/pass).")

            self._start_mitmdump(proxy_host, proxy_port, proxy_user, proxy_pass, listen_host="127.0.0.1", listen_port=8787)

            co = ChromiumOptions()
            co.set_pref('credentials_enable_service', False)
            co.set_proxy("http://127.0.0.1:8787")
            self.driver = Chromium(addr_or_opts=co)
        else:
            self.driver = Chromium()

        if not salvar_login:
            self.driver.clear_cache()
    
    def __del__(self):
        self._stop_mitmproxy()

