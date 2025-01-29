from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import logging
import os
from typing import List, Optional
from dataclasses import dataclass
from contextlib import contextmanager
import traceback

# Constants for Chrome setup
DEFAULT_CHROME_PATH = "/opt/render/project/.chrome/chrome-linux64/chrome-linux64/chrome"
CHROME_BINARY_PATH = os.getenv('CHROME_BINARY', DEFAULT_CHROME_PATH)


@dataclass
class RegistraduriaData:
    nuip: str
    fecha_consulta: Optional[str] = None
    documento: Optional[str] = None  
    estado: Optional[str] = None

class RegistraduriaScraper:
    URL = "https://defunciones.registraduria.gov.co/"
    INPUT_SELECTOR = "input[name='nuip']"
    BUTTON_SELECTOR = "button[type='submit']"

    def __init__(self, headless: bool = True):
        self.logger = self._setup_logger()
        self.verify_chrome_binary()
        self.headless = headless

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
            logger.setLevel(logging.INFO)
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
                    headless=self.headless,
                    executable_path=CHROME_BINARY_PATH,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-extensions',
                        '--disable-software-rasterizer'
                    ],
                )
                context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                                                       "Chrome/131.0.6778.108 Safari/537.36")
                page = context.new_page()
                self.logger.info("Playwright browser started successfully")
                yield page
            except Exception as e:
                self.logger.error(f"Failed to start Playwright browser: {e}")
                raise
            finally:
                browser.close()
                self.logger.info("Browser closed")

    def scrape(self, nuip: str) -> Optional[RegistraduriaData]:
        try:
            with self._get_browser() as page:
                page.goto(self.URL)
                self.logger.info(f"Navigating to {self.URL}")

                try:
                    page.fill(self.INPUT_SELECTOR, nuip)
                    self.logger.info(f"NUIP entered: {nuip}")
                    page.click(self.BUTTON_SELECTOR)
                    self.logger.info("Search button clicked")
                except PlaywrightTimeoutError:
                    self.logger.error("NUIP field not found within timeout")
                    return None
                except Exception as e:
                    self.logger.error(f"Error entering NUIP or clicking button: {e}")
                    self.logger.error(traceback.format_exc())
                    return None

                try:
                    results_selector = '//*[@id="content"]/div[2]/div/div/div/div'
                    page.wait_for_selector(results_selector, timeout=10000)
                    result_element = page.query_selector(results_selector)
                    
                    # Get consultation date
                    try:
                        fecha_consulta = result_element.query_selector('.card-title').inner_text().replace('Fecha Consulta: ', '').strip()
                    except AttributeError:
                        fecha_consulta = None
                        self.logger.error("Consultation date element not found")
                    
                    # Get document number
                    try:
                        documento = result_element.query_selector_all('.lead > span > strong')[0].inner_text()
                    except (AttributeError, IndexError):
                        documento = None
                        self.logger.error("Document number element not found")
                    
                    # Get status
                    try:
                        estado = result_element.query_selector_all('.lead > span > strong')[1].inner_text()
                    except (AttributeError, IndexError):
                        estado = None
                        self.logger.error("Status element not found")

                    data = RegistraduriaData(
                        nuip=nuip,
                        fecha_consulta=fecha_consulta,
                        documento=documento,
                        estado=estado
                    )
                    self.logger.info(f"Data extracted: {data}")
                    return data
                        
                except PlaywrightTimeoutError:
                    self.logger.error("Results not found within timeout")
                    return None
                except Exception as e:
                    self.logger.error(f"Error extracting data: {e}")
                    self.logger.error(traceback.format_exc())
                    return None
                        
        except Exception as e:
            self.logger.error(f"Error during scraping: {e}")
            self.logger.error(traceback.format_exc())
            return None