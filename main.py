from src.bot import Bot, CloudflareBypasser

from utils.logger_config import logger
from utils.global_functions import *

def main():
    """Executa a navegação e processamento para uma URL específica."""

    
    # Carregar configurações globais
    config = carregar_configuracao('config.yaml')
    max_navegadores = config.get('navegadores_simultaneos', 5)
    caminho_txt = config.get('arquivo_input', 'dados.txt')
    email = config.get('login', '')
    senha = config.get('senha', '')
    token = config.get('token', '')
    salvar_login = config.get('salvar_login', False)

    # Carregar links a partir do arquivo
    links = carregar_links_txt(caminho_txt)
    qtde_abas = min(max_navegadores, len(links))

    bot = Bot(qtde_abas)
    bot.load_page(links[:qtde_abas], False)
    abriu = False

    criar_csv(bot.nome_arquivo_csv)

    if max_navegadores == 1:
        bot.tab_principal.set.window.max()

    if salvar_login:
        logado = bot.is_loged()
        if not logado:
            bot.login(email, senha)
    else:
        bot.login(email, senha)
    
    try:
        while links:

            if len(links[:qtde_abas]) < qtde_abas:
                excesso_abas = qtde_abas - len(links[:qtde_abas])
                for _ in range(excesso_abas):
                    bot.tabs.pop()

            # Abre a página de remoção do nome
            bot.load_page(links[:qtde_abas], True)
            abriu = bot.abre_remocao()

            # Se não conseguiu abrir a removção, ele vai tentar novamente.
            while not abriu:
                bot.quit()
                bot = Bot(qtde_abas)
                bot.load_page(links[:qtde_abas], True)
                abriu = bot.abre_remocao()

            # Preenche o formulário
            bot.preenche_formulario(links[:qtde_abas], token)

            # Se aparecer captcha novamente
            for i, page in enumerate(bot.tabs):
                cf_bypasser = CloudflareBypasser(page)
                cf_bypasser.bypass()
                logger.debug(f"Página {i+1}: CAPTCHA resolvido")

            links = links[qtde_abas:]
        
        logger.info("Processo finalizado com sucesso.")

    except Exception as e:
        logger.error(e)

    finally:
        bot.quit()

if __name__ == '__main__':
    
    main()