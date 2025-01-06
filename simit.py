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
        
        # Set browser path to user's home directory
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = os.path.expanduser('~/.cache/ms-playwright')
        self.logger.info(f"PLAYWRIGHT_BROWSERS_PATH set to {os.getenv('PLAYWRIGHT_BROWSERS_PATH')}")

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
                # Try different browser types in case chromium fails
                browser_types = [p.chromium, p.firefox, p.webkit]
                last_error = None
                
                for browser_type in browser_types:
                    try:
                        browser = browser_type.launch(
                            headless=self.headless,
                            args=[
                                "--no-sandbox",
                                "--disable-dev-shm-usage",
                                "--disable-gpu",
                                "--disable-software-rasterizer",
                                "--disable-setuid-sandbox",
                                "--no-zygote",
                                "--single-process",
                            ]
                        )
                        self.logger.info(f"Successfully launched browser using {browser_type}")
                        break
                    except Exception as e:
                        last_error = e
                        self.logger.warning(f"Failed to launch {browser_type}: {e}")
                        continue
                
                if browser is None:
                    raise Exception(f"Failed to launch any browser. Last error: {last_error}")

                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/98.0.4758.102 Safari/537.36"
                )
                page = context.new_page()
                self.logger.info("Browser context and page created successfully")
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
                page.set_default_timeout(30000)
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
                
                # Try both XPaths
                for xpath, description in [
                    (self.RESULTADOS_XPATH, "principal"),
                    (self.RESULTADOS_XPATH_ALTERNATIVE, "alternativo")
                ]:
                    try:
                        self.logger.info(f"Intentando extraer resultados con XPath {description}")
                        page.wait_for_selector(f'xpath={xpath}', timeout=10000)
                        elemento = page.query_selector(f'xpath={xpath}')
                        if elemento:
                            estado_text = elemento.inner_text().strip()
                            self.logger.info(f"Resultados encontrados con XPath {description}: {estado_text}")
                            break
                    except PlaywrightTimeoutError:
                        self.logger.info(f"No se encontraron resultados con XPath {description}")
                    except Exception as e:
                        self.logger.error(f"Error al extraer con XPath {description}: {e}")

                if estado_text:
                    return RegistraduriaData(nuip=nuip, estado=estado_text)
                else:
                    self.logger.warning("No se encontró información en ningún XPath")
                    return None

        except Exception as e:
            self.logger.error(f"Error general en el proceso de scraping: {e}")
            self.logger.error(traceback.format_exc())
            return None