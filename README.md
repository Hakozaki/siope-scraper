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

Edite o arquivo `.env` para ajustar o período de busca da série histórica e a URL base. Para criá-lo pela primeira vez, copie o modelo:
```bash
cp .env.example .env
```

## Como Compartilhar/Instalar em Outro Computador

Para enviar esse robô para outra pessoa usar na máquina dela, siga os seguintes passos:

1. **Compacte os arquivos essenciais num arquivo `.zip`.** Envie apenas estes arquivos:
   - `scraper.py`
   - `utils.py`
   - `config.py`
   - `requirements.txt`
   - `README.md`
   - `.env.example`
   - *(NÃO envie as pastas `venv/`, `__pycache__/`, `logs/` ou `data/`)*

2. **Na máquina da usuária:**
   - Ela precisa ter o **Python** (versão 3.10 ou superior) instalado.
   - Ela precisa extrair a pasta com os arquivos.
   - Usando o Terminal ou Prompt de Comando dentro da pasta, ela roda os comandos de setup:

   **No Windows:**
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env
   ```

   **No Linux/Mac:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   ```

3. **Pronto!** A partir desse momento ela só precisa abrir o terminal na pasta, ativar o `.env` (passo 2) e rodar o script como você já faz:
   ```bash
   python scraper.py --uf AC
   ```
