# filepath: /C:/Users/david/Documents/LISTAS PYTHON/LISTAS PYTHON/simit - Playwright/simit.py
import os

# Set Playwright browsers path before importing Playwright
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "./.playwright-browsers"

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import logging
from typing import Optional
from dataclasses import dataclass
from contextlib import contextmanager
import traceback
from datetime import datetime

@dataclass
class RegistraduriaData:
    documento: str
    estado: str
    fecha_consulta: str

class RegistraduriaScraper:
    URL = 'https://defunciones.registraduria.gov.co/'
    INPUT_SELECTOR = '//*[@id="nuip"]'
    BUTTON_SELECTOR = '//*[@id="content"]/div/div/div/div/div[2]/form/div/button'
    RESULTADOS_XPATH = '//*[@id="content"]/div[2]/div/div/div/div'

    def __init__(self, headless: bool = True):
        self.logger = self._setup_logger()
        self.headless = headless

    @staticmethod
    def _setup_logger() -> logging.Logger:
        logger = logging.getLogger('registraduria_scraper')
        if not logger.handlers:
            logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            )
            logger.addHandler(handler)
        return logger

    def _parse_estado(self, content: str) -> str:
        return "Vigente (Vivo)" if "vigente" in content.lower() else "Cancelada por Muerte"

    def _get_fecha_actual(self) -> str:
        return datetime.now().strftime("%d/%m/%Y")

    @contextmanager
    def _get_browser(self):
        browser = None
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(
                    headless=self.headless, 
                    args=[
                        "--window-size=1280,720",
                        "--disable-gpu",
                        "--disable-dev-shm-usage",
                        "--disable-extensions",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-images",
                        "--disable-plugins",
                        "--mute-audio"
                    ],
                    slow_mo=50
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/98.0.4758.102 Safari/537.36"
                )
                page = context.new_page()
                self.logger.info("Browser launched successfully")
                yield page
            except Exception as e:
                self.logger.error(f"Error al iniciar el navegador: {e}")
                self.logger.error(traceback.format_exc())
                raise
            finally:
                if browser:
                    browser.close()
                    self.logger.info("Browser cerrado")

    def scrape(self, nuip: str) -> Optional[RegistraduriaData]:
        try:
            with self._get_browser() as page:
                page.goto(self.URL, timeout=600000, wait_until='networkidle')
                self.logger.info(f"Navegando a {self.URL}")

                # Ingresar NUIP
                try:
                    page.click(self.INPUT_SELECTOR)
                    page.fill(self.INPUT_SELECTOR, nuip)
                    self.logger.info(f"NUIP ingresado: {nuip}")
                except Exception as e:
                    self.logger.error(f"Error al ingresar NUIP: {e}")
                    return None

                # Clicar el botón de búsqueda
                try:
                    page.click(self.BUTTON_SELECTOR)
                    self.logger.info("Botón de búsqueda clickeado.")
                except Exception as e:
                    self.logger.error(f"Error al clicar el botón de búsqueda: {e}")
                    return None

                # Esperar y extraer resultados
                try:
                    page.wait_for_selector(self.RESULTADOS_XPATH, timeout=10000, state='visible')
                    content_element = page.query_selector(self.RESULTADOS_XPATH)
                    content_text = content_element.inner_text().strip() if content_element else None
                    self.logger.debug(f"Texto extraído: {content_text}")

                    if content_text:
                        return RegistraduriaData(
                            documento=nuip,
                            estado=self._parse_estado(content_text),
                            fecha_consulta=self._get_fecha_actual(),
                        )
                    else:
                        self.logger.warning("No se encontró información en los resultados.")
                        return None

                except PlaywrightTimeoutError:
                    self.logger.warning("Selector de resultados no encontrado.")
                    return None
                except Exception as e:
                    self.logger.error(f"Error al extraer información: {e}")
                    self.logger.error(traceback.format_exc())
                    return None

        except Exception as e:
            self.logger.error(f"Error general en el proceso de scraping: {e}")
            self.logger.error(traceback.format_exc())
            return None