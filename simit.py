from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import logging
from typing import Optional
from dataclasses import dataclass
from contextlib import contextmanager
import traceback
#funciona para ambos casos
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
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(
                    channel="chrome",
                    headless=self.headless,
                    args=["--window-size=1920,1080"],
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
                browser.close()
                self.logger.info("Browser cerrado")

    def scrape(self, nuip: str) -> Optional[RegistraduriaData]:
        try:
            with self._get_browser() as page:
                page.goto(self.URL)
                self.logger.info(f"Navegando a {self.URL}")

                # Cerrar banner si está presente
                try:
                    page.wait_for_selector(self.BANNER_CLOSE_SELECTOR, timeout=5000, state='visible')
                    page.click(self.BANNER_CLOSE_SELECTOR)
                    self.logger.info("Banner cerrado.")
                except PlaywrightTimeoutError:
                    self.logger.info("No se encontró el banner o ya está cerrado.")
                except Exception as e:
                    self.logger.error(f"Error al cerrar el banner: {e}")

                # Ingresar NUIP
                try:
                    page.fill(self.INPUT_SELECTOR, nuip)
                    self.logger.info(f"NUIP ingresado: {nuip}")
                    page.click(self.BUTTON_SELECTOR)
                    self.logger.info("Botón de búsqueda clickeado.")
                except Exception as e:
                    self.logger.error(f"Error al ingresar NUIP o clicar el botón: {e}")
                    return None

                # Esperar y extraer resultados usando ambos XPath
                try:
                    # Intentar con el primer XPath
                    try:
                        page.wait_for_selector(f'xpath={self.RESULTADOS_XPATH}', timeout=10000, state='visible')
                        estado_element = page.query_selector(f'xpath={self.RESULTADOS_XPATH}')
                        estado_text = estado_element.inner_text().strip() if estado_element else None
                        self.logger.debug(f"Texto extraído del XPath principal: {estado_text}")
                        
                        if estado_text:
                            return RegistraduriaData(nuip=nuip, estado=estado_text)
                            
                    except PlaywrightTimeoutError:
                        self.logger.warning("XPath principal no encontrado, intentando alternativo")
                        estado_text = None

                    # Si no se encontró en el primer XPath, intentar con el alternativo
                    try:
                        page.wait_for_selector(f'xpath={self.RESULTADOS_XPATH_ALTERNATIVE}', timeout=10000, state='visible')
                        alt_element = page.query_selector(f'xpath={self.RESULTADOS_XPATH_ALTERNATIVE}')
                        estado_text = alt_element.inner_text().strip() if alt_element else None
                        self.logger.debug(f"Texto extraído del XPath alternativo: {estado_text}")
                        
                        if estado_text:
                            return RegistraduriaData(nuip=nuip, estado=estado_text)
                            
                    except PlaywrightTimeoutError:
                        self.logger.warning("XPath alternativo no encontrado")
                        estado_text = None

                    if not estado_text:
                        self.logger.warning("No se encontró información en ningún XPath")
                        return None

                except Exception as e:
                    self.logger.error(f"Error al extraer información: {e}")
                    self.logger.error(traceback.format_exc())
                    return None

        except Exception as e:
            self.logger.error(f"Error general en el proceso de scraping: {e}")
            self.logger.error(traceback.format_exc())
            return None