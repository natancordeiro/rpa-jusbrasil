from src.bot import Bot

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

    # Carregar links a partir do arquivo
    links = carregar_links_txt(caminho_txt)
    qtde_abas = min(max_navegadores, len(links))

    bot = Bot(qtde_abas)
    bot.load_page(links[:qtde_abas])
    bot.login(email, senha)
    try:
        while links:

            # Abre a página de remoção do nome 
            bot.abre_remocao()

            # Preenche o formulário
            bot.preenche_formulario(links[:qtde_abas], token)

            bot.driver.clear_cache()

    except Exception as e:
        logger.error(e)

    finally:
        bot.quit()

if __name__ == '__main__':
    
    main()