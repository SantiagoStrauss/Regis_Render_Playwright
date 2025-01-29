from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import logging
from typing import Optional
from dataclasses import dataclass
from contextlib import contextmanager
import traceback
from datetime import datetime
import os

# Constants for Chrome setup
DEFAULT_CHROME_PATH = "/opt/render/project/.chrome/chrome-linux64/chrome-linux64/chrome"
CHROME_BINARY_PATH = os.getenv('CHROME_BINARY', DEFAULT_CHROME_PATH)

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
        self.verify_chrome_binary()

    def verify_chrome_binary(self) -> None:
        global CHROME_BINARY_PATH
        if not os.path.isfile(CHROME_BINARY_PATH):
            fallback_path = os.path.join(os.getcwd(), "chrome", "chrome.exe")
            if os.path.isfile(fallback_path):
                CHROME_BINARY_PATH = fallback_path
            else:
                self.logger.error(f"Chrome binary not found at {CHROME_BINARY_PATH}")
                raise FileNotFoundError(f"Chrome binary not found at {CHROME_BINARY_PATH}")
        
        if not os.access(CHROME_BINARY_PATH, os.X_OK):
            self.logger.error(f"Chrome binary not executable at {CHROME_BINARY_PATH}")
            raise PermissionError(f"Chrome binary not executable at {CHROME_BINARY_PATH}")

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

    def scrape(self, documento: str) -> Optional[RegistraduriaData]:
        try:
            with sync_playwright() as p:
                with p.chromium.launch(
                    executable_path=CHROME_BINARY_PATH,
                    headless=self.headless,
                    args=["--disable-dev-shm-usage", "--no-sandbox", "--disable-setuid-sandbox"]
                ) as browser:
                    self.logger.info("Playwright browser launched successfully")
                    with browser.new_page() as page:
                        self.logger.info(f"Navigating to {self.URL}")
                        page.goto(self.URL, timeout=60000)
                        self.logger.info("Page loaded successfully")

                        self.logger.debug("Filling in the documento field")
                        page.fill(self.INPUT_SELECTOR, documento)

                        self.logger.debug("Clicking the submit button")
                        page.click(self.BUTTON_SELECTOR)

                        self.logger.info("Waiting for resultados")
                        page.wait_for_selector(self.RESULTADOS_XPATH, timeout=30000)

                        resultados = page.query_selector(self.RESULTADOS_XPATH)
                        if resultados:
                            estado = resultados.inner_text().strip()
                            fecha_consulta = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            self.logger.info(f"Scraped data: documento={documento}, estado={estado}, fecha_consulta={fecha_consulta}")
                            return RegistraduriaData(documento=documento, estado=estado, fecha_consulta=fecha_consulta)
                        else:
                            self.logger.warning("No resultados found")
                            return None

        except PlaywrightTimeoutError as e:
            self.logger.error(f"Timeout while scraping documento {documento}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            self.logger.error(traceback.format_exc())
            return None

    def close(self):
        pass