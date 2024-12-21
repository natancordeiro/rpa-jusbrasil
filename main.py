import asyncio
from playwright.async_api import async_playwright
import yaml
import pandas as pd
from asyncio import Semaphore

from utils.logger_config import logger

# Função para carregar a configuração do arquivo YAML
def carregar_configuracao(caminho_arquivo):
    with open(caminho_arquivo, 'r') as arquivo:
        return yaml.safe_load(arquivo)

# Função para carregar os links do arquivo .txt
def carregar_links_txt(caminho_txt):
    with open(caminho_txt, 'r') as arquivo:
        linhas = arquivo.readlines()
    links_processados = []
    for linha in linhas:
        partes = linha.strip().split(';')
        if len(partes) == 2:
            links_processados.append({'url': partes[0], 'nome': partes[1]})
    return links_processados

# Função assíncrona para processar cada link
async def processar_link(url, nome, semaforo):
    async with semaforo:
        async with async_playwright() as p:
            navegador = await p.chromium.launch(headless=False)
            contexto = await navegador.new_context()
            pagina = await contexto.new_page()

            try:
                logger.info(f"Acessando: {url} para remover {nome}")
                await pagina.goto(url)

                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Erro ao acessar {url}: {e}")
            finally:
                await navegador.close()

# Função principal para gerenciar a execução
def executar(caminho_yaml, caminho_txt):
    config = carregar_configuracao(caminho_yaml)
    links = carregar_links_txt(caminho_txt)

    max_navegadores = config.get('navegadores_simultaneos', 5)
    semaforo = Semaphore(max_navegadores)

    asyncio.run(executar_links(links, semaforo))

# Função assíncrona para orquestrar os acessos aos links
async def executar_links(links, semaforo):
    tarefas = []

    for link_info in links:
        tarefas.append(processar_link(link_info['url'], link_info['nome'], semaforo))

    await asyncio.gather(*tarefas)

# Exemplo de chamada (ajustar os caminhos conforme necessário)
executar("config.yaml", "dados.txt")