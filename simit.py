from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import logging
from typing import Optional
from dataclasses import dataclass
from contextlib import contextmanager
import traceback
import os
import subprocess

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
        
        # Set browser path and ensure it exists
        self.browser_path = os.getenv('PLAYWRIGHT_BROWSERS_PATH', 
                                    os.path.expanduser('~/.cache/ms-playwright'))
        os.makedirs(self.browser_path, exist_ok=True)
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = self.browser_path
        
        self._ensure_browser_installed()
        self.logger.info(f"PLAYWRIGHT_BROWSERS_PATH set to {self.browser_path}")

    def _ensure_browser_installed(self):
        """Ensure browser is installed before attempting to use it"""
        try:
            # Check if browser is already installed
            with sync_playwright() as p:
                try:
                    p.chromium.executable_path
                    return  # Browser exists
                except Exception:
                    self.logger.info("Browser not found, attempting installation")
            
            # Set environment variables for installation
            os.environ['PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD'] = '0'
            os.environ['PLAYWRIGHT_SKIP_VALIDATION'] = '1'
            
            # Attempt browser installation
            subprocess.run(['playwright', 'install', 'chromium', '--with-deps'], 
                         check=True, capture_output=True)
            
            # Ensure proper permissions
            subprocess.run(['chmod', '-R', '777', self.browser_path], 
                         check=True, capture_output=True)
        except Exception as e:
            self.logger.error(f"Failed to install browser: {e}")
            raise

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
            browser = None
            try:
                launch_args = [
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-setuid-sandbox",
                    "--no-zygote",
                    "--single-process",
                ]
                
                self.logger.info("Attempting to launch browser...")
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=launch_args
                )
                self.logger.info("Successfully launched browser")
                
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
                self.logger.error(f"Error launching browser: {e}")
                self.logger.error(traceback.format_exc())
                raise
            finally:
                if browser:
                    try:
                        browser.close()
                        self.logger.info("Browser closed successfully")
                    except Exception as e:
                        self.logger.error(f"Error closing browser: {e}")

    def scrape(self, nuip: str) -> Optional[RegistraduriaData]:
        """
        Scrape data for a given NUIP number.
        
        Args:
            nuip (str): The NUIP number to search for
            
        Returns:
            Optional[RegistraduriaData]: The scraped data or None if unsuccessful
        """
        try:
            with self._get_browser() as page:
                # Configure timeouts
                page.set_default_timeout(30000)
                page.set_default_navigation_timeout(30000)

                # Navigate to the page
                self.logger.info(f"Navigating to {self.URL}")
                page.goto(self.URL, wait_until="networkidle")

                # Wait for page to be fully loaded
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_load_state("networkidle")

                # Close banner if present
                try:
                    if page.is_visible(self.BANNER_CLOSE_SELECTOR, timeout=5000):
                        page.click(self.BANNER_CLOSE_SELECTOR)
                        self.logger.info("Banner closed")
                except PlaywrightTimeoutError:
                    self.logger.info("Banner not found or already closed")
                except Exception as e:
                    self.logger.warning(f"Error closing banner: {e}")

                # Enter NUIP and perform search
                try:
                    self.logger.info(f"Waiting for input field {self.INPUT_SELECTOR}")
                    page.wait_for_selector(self.INPUT_SELECTOR, state="visible")
                    page.fill(self.INPUT_SELECTOR, nuip)
                    self.logger.info(f"NUIP entered: {nuip}")
                    
                    page.wait_for_selector(self.BUTTON_SELECTOR, state="visible")
                    page.click(self.BUTTON_SELECTOR)
                    self.logger.info("Search button clicked")
                except Exception as e:
                    self.logger.error(f"Error entering NUIP or clicking button: {e}")
                    return None

                # Wait for and extract results
                estado_text = None
                
                # Try both XPaths
                for xpath, description in [
                    (self.RESULTADOS_XPATH, "primary"),
                    (self.RESULTADOS_XPATH_ALTERNATIVE, "alternative")
                ]:
                    try:
                        self.logger.info(f"Attempting to extract results with {description} XPath")
                        page.wait_for_selector(f'xpath={xpath}', timeout=10000)
                        elemento = page.query_selector(f'xpath={xpath}')
                        if elemento:
                            estado_text = elemento.inner_text().strip()
                            self.logger.info(f"Results found with {description} XPath: {estado_text}")
                            break
                    except PlaywrightTimeoutError:
                        self.logger.info(f"No results found with {description} XPath")
                    except Exception as e:
                        self.logger.error(f"Error extracting with {description} XPath: {e}")

                if estado_text:
                    return RegistraduriaData(nuip=nuip, estado=estado_text)
                else:
                    self.logger.warning("No information found in any XPath")
                    return None

        except Exception as e:
            self.logger.error(f"General error in scraping process: {e}")
            self.logger.error(traceback.format_exc())
            return None

# Example usage
if __name__ == "__main__":
    scraper = RegistraduriaScraper(headless=True)
    result = scraper.scrape("1234567890")
    print(result)