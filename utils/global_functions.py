"""
Módulo onde é guardado as funções externas para utilização geral do projeto.
"""
import yaml
import random
from urllib.parse import urlparse, parse_qs

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

def gerar_numero_telefone():
    """
    Gera um número de telefone falso no padrão brasileiro (XX) XXXXX-XXXX.
    """

    # Lista de DDDs válidos no Brasil
    ddds_validos = [
        11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 24, 27, 28, 
        31, 32, 33, 34, 35, 37, 38, 41, 42, 43, 44, 45, 46, 47, 
        48, 49, 51, 53, 54, 55, 61, 62, 63, 64, 65, 66, 67, 68, 
        69, 71, 73, 74, 75, 77, 79, 81, 82, 83, 84, 85, 86, 87, 
        88, 89, 91, 92, 93, 94, 95, 96, 97, 98, 99
    ]
    
    # Seleciona um DDD aleatório
    ddd = random.choice(ddds_validos)
    
    # Gera o número no formato XXXXX-XXXX
    numero = f"{random.randint(90000, 99999)}-{random.randint(1000, 9999)}"
    
    # Retorna o número completo com DDD
    return f"({ddd}) {numero}"

def get_sitekey(url):
    """
    Extrai o valor do parâmetro 'k' de uma URL.
    
    :param url: URL de onde o parâmetro será extraído.
    :return: Valor do parâmetro 'k' ou None se não encontrado.
    """

    # Fazer o parsing da URL
    parsed_url = urlparse(url)
    
    # Obter os parâmetros da query string
    parametros = parse_qs(parsed_url.query)
    
    # Retornar o valor do parâmetro 'k' (se existir)
    return parametros.get('k', [None])[0]
