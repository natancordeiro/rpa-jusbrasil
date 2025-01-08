from utilitarios.cloudflare.CloudflareBypasser import CloudflareBypasser
from screeninfo import get_monitors
from twocaptcha import TwoCaptcha
import os

from driver.driver import Driver
from iterator.iteration import Interation
from utils.logger_config import logger
from utils.elements import XPATH, CSS
from utils.global_functions import *

class Bot(Interation):
    """Classe que define um bot para interação automatizada com páginas da web."""

    def __init__(self, qtde_windows: int = 1):
        """
        Inicializa um objeto Bot.

        Args:
            log_file (bool): Define se os registros serão salvos em um arquivo de log (padrão: True).
        """
        
        self.tabs = []
        monitor = get_monitors()[0]
        largura_tela = monitor.width
        altura_tela = monitor.height

        colunas = int(qtde_windows**0.5)
        linhas = (qtde_windows // colunas) + (qtde_windows % colunas > 0)
        largura_janela = largura_tela // colunas
        altura_janela = altura_tela // linhas


        for i in range(qtde_windows):
            coluna = i % colunas
            linha = i // colunas
            pos_x = coluna * largura_janela
            pos_y = linha * altura_janela

            if i == 0:
                self.driver = Driver(
                    browser='chrome',
                    headless=False,
                    incognito=False,
                    download_path='',
                    desabilitar_carregamento_imagem=False
                ).driver

                super().__init__(self.driver)
                self.tab_principal = self.driver.new_tab()
                self.tab_principal.set.window.size(largura_janela, altura_janela)
                self.tab_principal.set.window.location(pos_x, pos_y)
                self.tabs.append(self.tab_principal)
            
            else:

                tab = self.driver.new_tab(new_window=True)
                tab.set.window.size(largura_janela, altura_janela)
                tab.set.window.location(pos_x, pos_y)
                self.tabs.append(tab)

    def load_page(self, urls):
        for tab, url in zip(self.tabs, urls):
            logger.info(f"Acessando: {url['url']} para remover {url['nome']}")
            tab.get(url['url'])

    def wait_for(self, tag, timeout=15, metodo='xpath', element_is='clickable'):
        for tab in self.tabs:
            tab.ele(tag, timeout=timeout)

    def click(self, tag, metodo='xpath', tempo=10):
        for tab in self.tabs:
            tab.ele(tag, timeout=tempo).click()

    def write(self, seletor, valor, tempo=15, metodo='xpath'):
        if metodo == 'name':
            for tab, url in zip(self.tabs, valor):
                tab.ele(seletor, timeout=tempo).input(url['nome'])

        else:
            for tab in self.tabs:
                tab.ele(seletor, timeout=tempo).input(valor)

    def is_loged(self):
        """
        Verifica se o bot está logado na página.

        Returns:
            bool: True se o bot está logado, False caso contrário.
        """
        try:
            logado = self.tab_principal.ele(CSS['logado'], timeout=3)
            if logado:
                return True
            else:
                return False
        except Exception:
            return False

    def login(self, email: str, senha: str) -> bool:
        """
        Faz o login no sistema.

        Args:
            email (str): Email do usuário.
            senha (str): Senha do usuário.
        
        Returns:
            bool: True se o login foi bem-sucedido, False caso contrário.
        """

        try:
            logger.info('Efetuando login..')
            self.wait_for(CSS['login'], metodo='css')
            self.click(CSS['login'], metodo='css')
            self.wait_for(CSS['input_login'], metodo='css')
            self.sleep(0.5)
            self.write(CSS['input_login'], email, metodo='css')
            self.click(CSS['submit'], metodo='css')
            self.wait_for(CSS['input_senha'], metodo='css', timeout=5)
            self.sleep(0.5)
            self.write(CSS['input_senha'], senha, metodo='css')
            self.click(CSS['submit'], metodo='css')
            self.wait_for(CSS['logado'], timeout=3)
            logger.info(f"Login realizado com sucesso nas {len(self.tabs)} abas")
            return True
        except Exception as e:
            logger.error(f"Erro ao fazer login: {str(e)}")
            return False

    def abre_remocao(self):
        """Abre a pagina para remoção do nome."""
        
        logger.info("Solicitando remoção do nome.")

        try:
            # Clica em "Reportar Página"
            self.click(CSS['btn_reportar_pagina'])
            self.sleep(2)

            # Resolve o CAPTCHA
            for i, page in enumerate(self.tabs):
                cf_bypasser = CloudflareBypasser(page)
                cf_bypasser.bypass()
                logger.info(f"Página {i+1}: CAPTCHA resolvido")

            self.click(CSS['close_popup'])
            logger.info('Página "Remoção de informações" carregada com sucesso.')
            return True
        except Exception as e:
            logger.error(f"Erro ao abrir a página para remoção do nome: {str(e)}")
            return False
        
    def preenche_formulario(self, links, api_key: str):
        """
        Preenche o formulário para remoção do nome

        Args:
            links (List[str]): Lista de links dos nomes a serem removidos.
            api_key (str): Chave da API do TwoCaptcha.
        """
        
        logger.info("Preenchendo formulário para remoção do nome.")

        try:
            # Clica em motivo
            self.click(CSS['select_motivo'])

            # Seleciona a opção "OUTROS"
            self.click(CSS['outros'])

            # Preenche o nome a ser removido
            self.write(CSS['input_nome'], links, metodo='name')

            # Preenche telefone
            telefone = gerar_numero_telefone()
            self.write(CSS['telefone'], telefone)

            # Anexa o PDF
            pdf_file = os.path.join(os.getcwd(), 'utilitarios', 'arquivo.pdf')
            self.write(CSS['anexo'], pdf_file)

            # Enviar solicitação
            self.click(CSS['submit'])
            self.sleep(2)

            # Fecha o Pop-up
            self.click(CSS['close_popup'])

            # Marcar a opção do checkbox
            self.click(CSS['checkbox'])

            # Resolve o reCAPTCHA
            self.resolver_recaptcha(api_key)

            # Espera a remoção ter sido solicitada
            try:
                for i, tab in enumerate(self.tabs):
                    try:
                        sucesso = tab.ele(XPATH['sucesso'], timeout=1)
                        if sucesso:
                            logger.info(f"Remoção solicitada com sucesso na {i+1}° página | Nome: {links[i]['nome']}")
                        else:
                            logger.error(f"Remoção não solicitada na {i+1}° página. | Nome: {links[i]['nome']}")
                            erro = tab.ele(CSS['erro'], timeout=1).text
                            logger.error(f"Erro: {erro}")
                    except Exception:
                        logger.error(f"Erro ao verificar remoção na {i+1}° página.")                
            except:
                logger.error("Remoção não solicitada.")
            logger.info("Formulários enviados.")

            return True
        except Exception as e:
            logger.error(f"Erro ao preencher fomrulário: {e}")
            return False
        
    def resolver_recaptcha(self, api_key: str):
        """
        Resolução do reCAPTCHA.

        Args:
            api_key (str): Chave da API do TwoCaptcha.
        """

        logger.info("Resolvendo reCAPTCHA...")
        solver = TwoCaptcha(api_key)

        try:
            # Marca o checkbox
            # for page in self.tabs:
            #     frame_captcha = page.ele('css=iframe[title="reCAPTCHA"]')
            #     frame_captcha.ele(CSS['check_captcha']).click()

            # Obtem as variáveis para enviar na API 2CAPTCHA
            url_recaptcha = self.tab_principal.ele(CSS['frame_recaptcha']).attrs['src']
            sitekey = get_sitekey(url_recaptcha)
            result = solver.recaptcha(sitekey=sitekey, url=self.tab_principal.url)
            captcha_token = result["code"]

            for i, page in enumerate(self.tabs):

                sucesso = page.ele('css=iframe[title="reCAPTCHA"]').ele(CSS['check_captcha']).attrs['aria-checked']
                if sucesso == 'true':
                    logger.info(f"ReCAPTCHA já resolvido na {i+1}° página.")
                    continue
                page.ele(CSS['repsonse_captcha']).set.style('display', 'block')
                page.ele(CSS['repsonse_captcha']).input(captcha_token)

            # for page in self.tabs:
            #     frame_captcha = page.ele('css=iframe[title="reCAPTCHA"]')
            #     frame_captcha.ele(CSS['check_captcha']).click()

            self.click(CSS['submit'])
            self.tab_principal.wait.url_change('enviar')
            logger.info("reCAPTCHA Resolvido com sucesso!")
            return True
        
        except Exception as e:
            logger.error(f"Erro ao resolver reCAPTCHA: {e}")
            return False

    def close(self):
        """Fecha a aba atual no navegador."""
        
        self.tab_principal.close()

    def quit(self):
        """Fecha o driver do Selenium."""

        logger.info("Fechando navegador")
        self.driver.quit()

    def __del__(self):
        self.quit()
