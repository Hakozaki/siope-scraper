"""
Funções utilitárias para o scraper SIOPE.
"""
import os
import re
import pandas as pd


def sanitize_filename(name: str) -> str:
    """
    Converte nome de município para nome de arquivo seguro.
    Ex: "Cruzeiro do Sul" -> "cruzeiro_do_sul"
    """
    # Remove acentos comuns do português
    replacements = {
        "á": "a", "à": "a", "ã": "a", "â": "a",
        "é": "e", "ê": "e",
        "í": "i",
        "ó": "o", "ô": "o", "õ": "o",
        "ú": "u", "ü": "u",
        "ç": "c",
        "Á": "A", "À": "A", "Ã": "A", "Â": "A",
        "É": "E", "Ê": "E",
        "Í": "I",
        "Ó": "O", "Ô": "O", "Õ": "O",
        "Ú": "U", "Ü": "U",
        "Ç": "C",
    }
    for original, replacement in replacements.items():
        name = name.replace(original, replacement)

    # Converte para lowercase e substitui espaços/caracteres especiais por _
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")
    return name


def ensure_directory(path: str) -> None:
    """Cria diretório se não existir."""
    os.makedirs(path, exist_ok=True)


def parse_html_table(table_element) -> pd.DataFrame:
    """
    Converte um elemento <table> do Selenium em um DataFrame do pandas.
    
    Args:
        table_element: WebElement da tabela
    
    Returns:
        DataFrame com os dados da tabela
    """
    # Extrair cabeçalhos
    headers = []
    header_rows = table_element.find_elements("tag name", "th")
    for th in header_rows:
        headers.append(th.text.strip())

    # Se não encontrou <th>, tenta pegar da primeira <tr>
    if not headers:
        first_row = table_element.find_element("tag name", "tr")
        for td in first_row.find_elements("tag name", "td"):
            headers.append(td.text.strip())

    # Extrair linhas de dados
    rows = []
    tbody = table_element.find_elements("tag name", "tbody")
    if tbody:
        tr_elements = tbody[0].find_elements("tag name", "tr")
    else:
        tr_elements = table_element.find_elements("tag name", "tr")
        # Pula a primeira linha se já foi usada como cabeçalho
        if headers:
            tr_elements = tr_elements[1:]

    for tr in tr_elements:
        cells = tr.find_elements("tag name", "td")
        if cells:
            row = [cell.text.strip() for cell in cells]
            rows.append(row)

    # Criar DataFrame
    if headers and rows:
        # Ajusta headers se número de colunas não bate
        if rows and len(headers) != len(rows[0]):
            headers = [f"col_{i}" for i in range(len(rows[0]))]
        df = pd.DataFrame(rows, columns=headers)
    elif rows:
        df = pd.DataFrame(rows)
    else:
        df = pd.DataFrame()

    return df


def save_to_csv(df: pd.DataFrame, filepath: str) -> None:
    """
    Salva DataFrame em CSV. Se o arquivo já existir, faz append.
    
    Args:
        df: DataFrame com os dados
        filepath: Caminho completo do arquivo CSV
    """
    if df.empty:
        return

    ensure_directory(os.path.dirname(filepath))

    if os.path.exists(filepath):
        # Append sem repetir cabeçalho
        df.to_csv(filepath, mode="a", header=False, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(filepath, index=False, encoding="utf-8-sig")


def format_progress(current: int, total: int, label: str = "") -> str:
    """Formata uma string de progresso."""
    pct = (current / total * 100) if total > 0 else 0
    bar_len = 30
    filled = int(bar_len * current / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_len - filled)
    return f"  [{bar}] {current}/{total} ({pct:.0f}%) {label}"
