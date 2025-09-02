import os
import logging
import sys
from DrissionPage import Chromium, ChromiumOptions

from utils.global_functions import carregar_configuracao

class Driver():
    """Classe para gerenciar o WebDriver e as opções do navegador."""

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

        profile_path = os.path.expandvars(r"%USERPROFILE%\AppData\Local\Google\Chrome\User Data\Default")
        co = ChromiumOptions().set_user_data_path(profile_path)
        co.set_pref('credentials_enable_service', False)
        co.set_pref('profile.password_manager_enabled', False)

        if usar_proxy:
            proxy_host = config.get("proxy_host")
            proxy_port = int(config.get("proxy_port", 0) or 0)
            co.set_proxy(f"http://{proxy_host}:{proxy_port}")

        self.driver = Chromium(addr_or_opts=co)

        if not salvar_login:
            self.driver.clear_cache()

