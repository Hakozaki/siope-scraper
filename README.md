# SIOPE Data Scraper 🇧🇷

Extrai dados de receitas municipais do [SIOPE/FNDE](https://www.fnde.gov.br/siope/dadosInformadosMunicipio.do) — Sistema de Informações sobre Orçamentos Públicos em Educação.

## Instalação

```bash
# Criar ambiente virtual e instalar dependências
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Chrome é necessário (já deve estar instalado)
```

## Uso

```bash
# Extrair dados do Acre (padrão), série 2016-2025
python scraper.py

# Especificar UF
python scraper.py --uf SP

# Ano específico
python scraper.py --uf AC --ano 2024

# Múltiplos anos
python scraper.py --uf AC --ano 2022 2023 2024

# Listar UFs disponíveis
python scraper.py --list-ufs
```

## Como funciona

1. O script abre o Chrome e navega ao SIOPE
2. Para cada **município × ano**, preenche o formulário automaticamente
3. Quando o **CAPTCHA** aparecer, pausa e pede para você resolver manualmente
4. Extrai a tabela de receitas e salva em CSV

## Estrutura de saída

```
data/
└── AC/
    ├── acrelândia.csv
    ├── assis_brasil.csv
    ├── brasiléia.csv
    └── ...
```

Cada CSV contém colunas: `ano`, `municipio`, `uf`, + colunas da tabela de receitas.

## Configuração

Edite `config.py` para ajustar:
- `ANOS` — série histórica (padrão: 2016-2025)
- `REQUEST_DELAY` — delay entre consultas
- `CAPTCHA_WAIT_TIMEOUT` — timeout para CAPTCHA
