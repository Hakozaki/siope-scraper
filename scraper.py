#!/usr/bin/env python3
"""
SIOPE Data Scraper
==================
Extrai dados de receitas municipais do SIOPE/FNDE.

Uso:
    python scraper.py                    # Roda para Acre (padrão)
    python scraper.py --uf AC            # Especifica UF
    python scraper.py --uf AC --ano 2024 # Especifica UF e ano único
    python scraper.py --headless         # Modo headless (sem janela)
"""
import argparse
import logging
import os
import sys
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)

import config
from utils import (
    sanitize_filename,
    parse_html_table,
    save_to_csv,
    ensure_directory,
    format_progress,
)


def setup_logging(uf: str = "geral") -> logging.Logger:
    """
    Configura logging para console + arquivo.
    Cria um arquivo de log em logs/siope_{UF}_{timestamp}.log
    """
    log = logging.getLogger("siope")
    log.setLevel(logging.DEBUG)

    # Limpa handlers anteriores (para re-execuções)
    log.handlers.clear()

    # Formato das mensagens
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)
    log.addHandler(console_handler)

    # Handler para arquivo
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    ensure_directory(log_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"siope_{uf}_{timestamp}.log")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)-8s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    log.addHandler(file_handler)

    log.info(f"Log salvo em: {log_file}")
    return log


log = logging.getLogger("siope")


class SiopeScraper:
    """Scraper para dados do SIOPE/FNDE."""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.driver = None

    # ──────────────────────────────────────────────
    #  Setup e Teardown
    # ──────────────────────────────────────────────
    def setup_driver(self):
        """Inicializa o Chrome WebDriver."""
        log.info("Iniciando Chrome WebDriver...")
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1280,900")
        # Desabilita notificações
        options.add_argument("--disable-notifications")
        # Ignora erros de certificado SSL (necessário em redes com proxy)
        options.add_argument("--ignore-certificate-errors")
        options.add_experimental_option(
            "prefs", {"profile.default_content_setting_values.notifications": 2}
        )

        # Selenium 4.6+ gerencia o ChromeDriver automaticamente
        # sem precisar do webdriver-manager
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(config.PAGE_LOAD_TIMEOUT)
        log.info("Chrome WebDriver iniciado com sucesso.")

    def teardown(self):
        """Fecha o navegador."""
        if self.driver:
            self.driver.quit()
            log.info("Navegador fechado.")

    # ──────────────────────────────────────────────
    #  Navegação e Interação com o Formulário
    # ──────────────────────────────────────────────
    def navigate_to_page(self):
        """Navega até a página do SIOPE."""
        log.info(f"Navegando para {config.BASE_URL}")
        self.driver.get(config.BASE_URL)
        # Espera o formulário carregar
        WebDriverWait(self.driver, config.ELEMENT_WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.ID, config.FORM_IDS["uf"]))
        )
        log.info("Página carregada com sucesso.")

    def _select_dropdown(self, element_id: str, value: str, wait_reload: bool = False):
        """
        Seleciona um valor em um dropdown <select>.
        
        Args:
            element_id: ID do elemento select
            value: Valor da opção (atributo value)
            wait_reload: Se True, espera a página recarregar após a seleção
        """
        # Mapeamento de fallback: value → texto visível (para quando o value muda)
        VALUE_TO_TEXT = {
            "R": "Receitas", "D": "Despesas", "P": "Despesas - Público-Alvo",
            "I": "Info. Complementares", "6": "Anual", "3": "Consolidada",
            "1": "Poder Executivo", "2": "Poder Legislativo",
        }

        try:
            select_element = WebDriverWait(self.driver, config.ELEMENT_WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.ID, element_id))
            )
            select = Select(select_element)
            
            # Log DEBUG com todas as opções disponíveis
            available = [(o.get_attribute("value"), o.text.strip()) for o in select.options]
            log.debug(f"Dropdown {element_id}: opções disponíveis = {available}")
            
            try:
                select.select_by_value(value)
                log.debug(f"Dropdown {element_id}: selecionado por value '{value}'")
            except NoSuchElementException:
                # Fallback: tenta pelo texto visível
                fallback_text = VALUE_TO_TEXT.get(value)
                if fallback_text:
                    log.debug(f"Dropdown {element_id}: value '{value}' não encontrado, tentando texto '{fallback_text}'")
                    select.select_by_visible_text(fallback_text)
                    log.debug(f"Dropdown {element_id}: selecionado por texto '{fallback_text}'")
                else:
                    raise
            
            if wait_reload:
                # A página faz POST e recarrega ao mudar UF/Município
                time.sleep(config.REQUEST_DELAY)
                WebDriverWait(self.driver, config.PAGE_LOAD_TIMEOUT).until(
                    EC.presence_of_element_located((By.ID, element_id))
                )
        except Exception as e:
            log.error(f"Erro ao selecionar {element_id} = {value}: {e}")
            raise

    def select_form_fields(self, ano: str, uf_code: str, muni_code: str):
        """
        Preenche todos os campos do formulário.
        
        Args:
            ano: Ano (ex: "2024")
            uf_code: Código da UF (ex: "12" para Acre)
            muni_code: Código do município
        """
        # 1. Exibir = Receitas (já é o padrão, mas garante)
        self._select_dropdown(config.FORM_IDS["exibir"], config.VALORES_FIXOS["exibir"])
        time.sleep(0.5)

        # 2. Ano
        self._select_dropdown(config.FORM_IDS["ano"], str(ano), wait_reload=True)

        # 3. Período = Anual
        self._select_dropdown(config.FORM_IDS["periodo"], config.VALORES_FIXOS["periodo"])
        time.sleep(0.5)

        # 4. UF (causa reload da página)
        self._select_dropdown(config.FORM_IDS["uf"], uf_code, wait_reload=True)

        # 5. Município (causa reload da página)
        self._select_dropdown(config.FORM_IDS["municipio"], muni_code, wait_reload=True)

        # 6. Administração = Consolidada
        self._select_dropdown(
            config.FORM_IDS["administracao"], config.VALORES_FIXOS["administracao"]
        )
        time.sleep(0.5)

        log.info(f"Formulário preenchido: ano={ano}, uf={uf_code}, muni={muni_code}")

    def get_municipios(self, uf_code: str) -> list[tuple[str, str]]:
        """
        Obtém a lista de municípios disponíveis para uma UF.
        
        Navega até a página, seleciona a UF, e extrai as opções do dropdown.
        
        Returns:
            Lista de tuplas (código, nome) dos municípios
        """
        log.info(f"Buscando municípios para UF código {uf_code}...")
        
        # Navega para a página fresca
        self.navigate_to_page()
        
        # Seleciona a UF (causa reload)
        self._select_dropdown(config.FORM_IDS["uf"], uf_code, wait_reload=True)
        
        # Espera o dropdown de municípios ser populado
        time.sleep(config.REQUEST_DELAY)
        
        muni_select = WebDriverWait(self.driver, config.ELEMENT_WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.ID, config.FORM_IDS["municipio"]))
        )
        select = Select(muni_select)
        
        municipios = []
        for option in select.options:
            value = option.get_attribute("value")
            text = option.text.strip()
            # Ignora a opção padrão "Selecione o Município"
            if value and text and "Selecione" not in text:
                municipios.append((value, text))
        
        log.info(f"Encontrados {len(municipios)} municípios.")
        return municipios

    # ──────────────────────────────────────────────
    #  CAPTCHA
    # ──────────────────────────────────────────────
    def wait_for_captcha_resolution(self):
        """
        Espera o usuário resolver o CAPTCHA manualmente.
        
        Detecta o reCAPTCHA na página e pausa a execução até que
        ele seja resolvido ou o timeout expire.
        """
        print("\n" + "=" * 60)
        print("  ⚠️  CAPTCHA DETECTADO!")
        print("  Por favor, resolva o CAPTCHA no navegador.")
        print("  Pressione ENTER aqui quando terminar...")
        print("=" * 60)
        
        try:
            input()
        except EOFError:
            # Se estiver em modo não-interativo, espera um timeout
            log.warning("Modo não-interativo detectado. Aguardando CAPTCHA por timeout...")
            time.sleep(config.CAPTCHA_WAIT_TIMEOUT)

    # ──────────────────────────────────────────────
    #  Consulta e Extração
    # ──────────────────────────────────────────────
    def click_consultar(self):
        """Clica no botão Consultar para submeter o formulário."""
        try:
            # O botão Consultar pode ser um <input type="button"> ou um <button>
            # Tenta encontrar por diferentes seletores
            btn = None
            
            # Tenta pelo valor/texto "Consultar"
            for selector in [
                "//input[@value='Consultar']",
                "//button[contains(text(), 'Consultar')]",
                "//input[@type='button' and @value='Consultar']",
                "//input[@type='submit']",
            ]:
                try:
                    btn = self.driver.find_element(By.XPATH, selector)
                    if btn.is_displayed():
                        break
                except NoSuchElementException:
                    continue
            
            if btn is None:
                # Tenta via JavaScript - a função submitForm() existe na página
                log.info("Botão não encontrado, tentando submitForm() via JS...")
                self.driver.execute_script("submitForm();")
            else:
                btn.click()
            
            log.info("Formulário submetido.")
            time.sleep(config.POST_SUBMIT_WAIT)
            
        except Exception as e:
            log.error(f"Erro ao clicar Consultar: {e}")
            raise

    def _check_captcha_required(self) -> bool:
        """Verifica se a mensagem de CAPTCHA obrigatório apareceu."""
        try:
            page_text = self.driver.page_source
            return "necessário validar o captcha" in page_text.lower()
        except Exception:
            return False

    def extract_table_data(self) -> "pd.DataFrame":
        """
        Extrai dados da tabela de resultados após a consulta.
        
        Returns:
            DataFrame com os dados extraídos
        """
        import pandas as pd
        
        try:
            # Espera a tabela de resultados aparecer
            table = WebDriverWait(self.driver, config.ELEMENT_WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.listagem, table.resultado, table"))
            )
            
            # Pode haver múltiplas tabelas; pega a que tem dados
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            
            best_table = None
            max_rows = 0
            
            for t in tables:
                rows = t.find_elements(By.TAG_NAME, "tr")
                if len(rows) > max_rows:
                    max_rows = len(rows)
                    best_table = t
            
            if best_table is None or max_rows <= 1:
                log.warning("Nenhuma tabela de dados encontrada.")
                return pd.DataFrame()
            
            df = parse_html_table(best_table)
            log.info(f"Extraídos {len(df)} linhas da tabela.")
            return df
            
        except TimeoutException:
            log.warning("Timeout esperando tabela de resultados.")
            return pd.DataFrame()
        except Exception as e:
            log.error(f"Erro ao extrair tabela: {e}")
            return pd.DataFrame()

    # ──────────────────────────────────────────────
    #  Loop Principal
    # ──────────────────────────────────────────────
    def run(self, uf: str, anos: list[int] | None = None):
        """
        Executa o scraping para uma UF específica.
        
        Args:
            uf: Sigla do estado (ex: "AC")
            anos: Lista de anos. Se None, usa config.ANOS.
        """
        import pandas as pd
        
        if anos is None:
            anos = config.ANOS

        uf_code = config.UFS.get(uf)
        if not uf_code:
            log.error(f"UF '{uf}' não encontrada. UFs válidas: {list(config.UFS.keys())}")
            return

        uf_dir = os.path.join(config.OUTPUT_DIR, uf)
        ensure_directory(uf_dir)

        try:
            self.setup_driver()
            
            # 1. Obter lista de municípios
            municipios = self.get_municipios(uf_code)
            if not municipios:
                log.error("Nenhum município encontrado!")
                return

            total = len(municipios) * len(anos)
            current = 0

            log.info(f"\n{'='*60}")
            log.info(f"  SIOPE Scraper - {uf}")
            log.info(f"  {len(municipios)} municípios × {len(anos)} anos = {total} consultas")
            log.info(f"{'='*60}\n")

            # 2. Para cada município
            for muni_idx, (muni_code, muni_name) in enumerate(municipios):
                safe_name = sanitize_filename(muni_name)
                muni_dir = os.path.join(uf_dir, safe_name)
                ensure_directory(muni_dir)
                
                log.info(f"\n📍 Município: {muni_name} ({muni_idx + 1}/{len(municipios)})")

                # 3. Para cada ano
                for ano_idx, ano in enumerate(anos):
                    current += 1
                    csv_path = os.path.join(muni_dir, f"{safe_name}_{ano}.csv")
                    
                    # Pula se CSV já existe (permite retomar execuções interrompidas)
                    if os.path.exists(csv_path):
                        log.info(format_progress(current, total, f"{muni_name} - {ano} (já existe, pulando)"))
                        continue

                    log.info(format_progress(current, total, f"{muni_name} - {ano}"))

                    try:
                        # Navega para a página fresca
                        self.navigate_to_page()
                        
                        # Preenche o formulário
                        self.select_form_fields(str(ano), uf_code, muni_code)

                        # Verifica se o botão Consultar apareceu
                        # (pode não aparecer se não há planilha para este ano)
                        try:
                            planilha_select = Select(
                                self.driver.find_element(By.ID, config.FORM_IDS["planilha"])
                            )
                            planilha_options = [
                                o for o in planilha_select.options 
                                if o.get_attribute("value")
                            ]
                            
                            if not planilha_options or "Não há" in planilha_select.first_selected_option.text:
                                log.info(f"  ⏭️  Sem dados para {ano} - pulando")
                                continue
                        except Exception:
                            log.info(f"  ⏭️  Planilha não disponível para {ano} - pulando")
                            continue

                        # Tenta consultar
                        self.click_consultar()

                        # Verifica se precisa de CAPTCHA
                        if self._check_captcha_required():
                            self.wait_for_captcha_resolution()
                            # Tenta consultar novamente após CAPTCHA
                            self.click_consultar()

                        # Extrai dados da tabela
                        df = self.extract_table_data()
                        
                        if not df.empty:
                            df.insert(0, "ano", ano)
                            df.insert(1, "municipio", muni_name)
                            df.insert(2, "uf", uf)
                            # Salva imediatamente
                            save_to_csv(df, csv_path)
                            log.info(f"  ✅ {len(df)} linhas → {csv_path}")
                        else:
                            log.info(f"  ⚠️  Sem dados na tabela para {ano}")

                    except Exception as e:
                        log.error(f"  ❌ Erro em {muni_name}/{ano}: {e}")
                        continue

                    # Delay entre consultas
                    time.sleep(config.REQUEST_DELAY)

        except KeyboardInterrupt:
            log.info("\n\n⚠️  Interrompido pelo usuário.")
        except Exception as e:
            log.error(f"Erro fatal: {e}")
            raise
        finally:
            self.teardown()


def main():
    parser = argparse.ArgumentParser(
        description="SIOPE Data Scraper - Extrai dados de receitas municipais do FNDE/SIOPE"
    )
    parser.add_argument(
        "--uf",
        type=str,
        default="AC",
        help="Sigla da UF (ex: AC, SP, RJ). Padrão: AC",
    )
    parser.add_argument(
        "--ano",
        type=int,
        nargs="*",
        help="Ano(s) específico(s). Se não informado, usa série 2016-2025",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Executa em modo headless (sem janela do Chrome)",
    )
    parser.add_argument(
        "--list-ufs",
        action="store_true",
        help="Lista todas as UFs disponíveis e sai",
    )
    
    args = parser.parse_args()

    if args.list_ufs:
        print("\nUFs disponíveis:")
        for sigla, codigo in sorted(config.UFS.items()):
            print(f"  {sigla} (código: {codigo})")
        return

    uf = args.uf.upper()
    anos = args.ano if args.ano else None

    # Inicializa logging (console + arquivo)
    setup_logging(uf=uf)

    scraper = SiopeScraper(headless=args.headless)
    scraper.run(uf=uf, anos=anos)


if __name__ == "__main__":
    main()
