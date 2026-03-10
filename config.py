"""
Configurações do scraper SIOPE.
"""
import os
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()
# URL base do SIOPE (pode ser sobrescrita pelo arquivo .env)
BASE_URL = os.getenv("BASE_URL", "https://www.fnde.gov.br/siope/dadosInformadosMunicipio.do")

# Série histórica configurável pelo .env (padrão 2016 a 2025)
ANO_INICIO = int(os.getenv("ANO_INICIO", 2016))
ANO_FIM = int(os.getenv("ANO_FIM", 2025))
ANOS = list(range(ANO_INICIO, ANO_FIM + 1))

# IDs dos elementos do formulário
FORM_IDS = {
    "exibir": "tp_relatorio",
    "ano": "num_ano",
    "periodo": "num_peri",
    "uf": "cod_uf",
    "municipio": "cod_muni",
    "administracao": "admin",
    "planilha": "planilhas",
}

# Valores fixos do formulário (values reais do HTML)
VALORES_FIXOS = {
    "exibir": "R",                # Exibir = Receitas (R=Receitas, D=Despesas, P=Público-Alvo, I=Info)
    "periodo": "6",               # Período = Anual (6=Anual, 1-5=Bimestres)
    "administracao": "3",         # Administração = Consolidada (3=Consolidada, 1=Executivo, 2=Legislativo)
}

# Mapeamento UF → código IBGE
UFS = {
    "AC": "12",  # Acre
    "AL": "27",  # Alagoas
    "AM": "13",  # Amazonas
    "AP": "16",  # Amapá
    "BA": "29",  # Bahia
    "CE": "23",  # Ceará
    "DF": "53",  # Distrito Federal
    "ES": "32",  # Espírito Santo
    "GO": "52",  # Goiás
    "MA": "21",  # Maranhão
    "MG": "31",  # Minas Gerais
    "MS": "50",  # Mato Grosso do Sul
    "MT": "51",  # Mato Grosso
    "PA": "15",  # Pará
    "PB": "25",  # Paraíba
    "PE": "26",  # Pernambuco
    "PI": "22",  # Piauí
    "PR": "41",  # Paraná
    "RJ": "33",  # Rio de Janeiro
    "RN": "24",  # Rio Grande do Norte
    "RO": "11",  # Rondônia
    "RR": "14",  # Roraima
    "RS": "43",  # Rio Grande do Sul
    "SC": "42",  # Santa Catarina
    "SE": "28",  # Sergipe
    "SP": "35",  # São Paulo
    "TO": "17",  # Tocantins
}

# Diretório de saída para os CSVs
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Timeouts (em segundos)
PAGE_LOAD_TIMEOUT = 30
ELEMENT_WAIT_TIMEOUT = 15
CAPTCHA_WAIT_TIMEOUT = 300  # 5 minutos para resolver CAPTCHA manualmente
POST_SUBMIT_WAIT = 5        # Espera após submeter o formulário

# Delay entre consultas (em segundos) para não sobrecarregar o servidor
REQUEST_DELAY = 2
