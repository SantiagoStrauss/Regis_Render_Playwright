from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import logging
from typing import Optional
from dataclasses import dataclass
from contextlib import contextmanager
import traceback
import os

@dataclass
class RegistraduriaData:
    nuip: str
    fecha_consulta: Optional[str] = None
    documento: Optional[str] = None
    estado: Optional[str] = None

class RegistraduriaScraper:
    URL = 'https://www.fcm.org.co/simit/#/home-public'
    INPUT_SELECTOR = '#txtBusqueda'
    BUTTON_SELECTOR = '#consultar'
    BANNER_CLOSE_SELECTOR = '#modalInformation > div > div > div.modal-header > button > span'
    RESULTADOS_XPATH = '//*[@id="mainView"]/div/div[1]/div/div[2]/div[2]/p[1]'
    RESULTADOS_XPATH_ALTERNATIVE = '//*[@id="resumenEstadoCuenta"]/div/div'

    def __init__(self, headless: bool = True):
        self.logger = self._setup_logger()
        self.headless = headless
        
        # Ensure PLAYWRIGHT_BROWSERS_PATH is set
        if not os.getenv('PLAYWRIGHT_BROWSERS_PATH'):
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/opt/render/.cache/ms-playwright'
            self.logger.info(f"Set PLAYWRIGHT_BROWSERS_PATH to {os.getenv('PLAYWRIGHT_BROWSERS_PATH')}")

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

    @contextmanager
    def _get_browser(self):
        browser = None
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--window-size=1920,1080",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-software-rasterizer"
                    ],
                    slow_mo=50
                )
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
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
                    try:
                        browser.close()
                        self.logger.info("Browser cerrado correctamente")
                    except Exception as e:
                        self.logger.error(f"Error al cerrar el navegador: {e}")

    def scrape(self, nuip: str) -> Optional[RegistraduriaData]:
        try:
            with self._get_browser() as page:
                # Configure timeouts
                page.set_default_timeout(30000)  # 30 seconds
                page.set_default_navigation_timeout(30000)

                # Navigate to the page
                self.logger.info(f"Navegando a {self.URL}")
                page.goto(self.URL, wait_until="networkidle")

                # Wait for page to be fully loaded
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_load_state("networkidle")

                # Cerrar banner si está presente
                try:
                    if page.is_visible(self.BANNER_CLOSE_SELECTOR, timeout=5000):
                        page.click(self.BANNER_CLOSE_SELECTOR)
                        self.logger.info("Banner cerrado.")
                except PlaywrightTimeoutError:
                    self.logger.info("No se encontró el banner o ya está cerrado.")
                except Exception as e:
                    self.logger.warning(f"Error al cerrar el banner: {e}")
                    # Continue execution as this is not critical

                # Ingresar NUIP y realizar búsqueda
                try:
                    self.logger.info(f"Esperando por el campo de entrada {self.INPUT_SELECTOR}")
                    page.wait_for_selector(self.INPUT_SELECTOR, state="visible")
                    page.fill(self.INPUT_SELECTOR, nuip)
                    self.logger.info(f"NUIP ingresado: {nuip}")
                    
                    page.wait_for_selector(self.BUTTON_SELECTOR, state="visible")
                    page.click(self.BUTTON_SELECTOR)
                    self.logger.info("Botón de búsqueda clickeado.")
                except Exception as e:
                    self.logger.error(f"Error al ingresar NUIP o clicar el botón: {e}")
                    return None

                # Esperar y extraer resultados
                estado_text = None
                
                # Intentar con el primer XPath
                try:
                    self.logger.info("Intentando extraer resultados con XPath principal")
                    page.wait_for_selector(f'xpath={self.RESULTADOS_XPATH}', timeout=10000)
                    elemento = page.query_selector(f'xpath={self.RESULTADOS_XPATH}')
                    if elemento:
                        estado_text = elemento.inner_text().strip()
                        self.logger.info(f"Resultados encontrados con XPath principal: {estado_text}")
                except PlaywrightTimeoutError:
                    self.logger.info("No se encontraron resultados con XPath principal")
                
                # Si no se encontró con el primer XPath, intentar con el alternativo
                if not estado_text:
                    try:
                        self.logger.info("Intentando extraer resultados con XPath alternativo")
                        page.wait_for_selector(f'xpath={self.RESULTADOS_XPATH_ALTERNATIVE}', timeout=10000)
                        elemento = page.query_selector(f'xpath={self.RESULTADOS_XPATH_ALTERNATIVE}')
                        if elemento:
                            estado_text = elemento.inner_text().strip()
                            self.logger.info(f"Resultados encontrados con XPath alternativo: {estado_text}")
                    except PlaywrightTimeoutError:
                        self.logger.warning("No se encontraron resultados con XPath alternativo")

                if estado_text:
                    return RegistraduriaData(nuip=nuip, estado=estado_text)
                else:
                    self.logger.warning("No se encontró información en ningún XPath")
                    return None

        except Exception as e:
            self.logger.error(f"Error general en el proceso de scraping: {e}")
            self.logger.error(traceback.format_exc())
            return None

    def __str__(self) -> str:
        return f"RegistraduriaScraper(headless={self.headless})"

    def __repr__(self) -> str:
        return self.__str__()