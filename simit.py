import os
import sys
import subprocess
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import logging
from typing import Optional
from dataclasses import dataclass
from contextlib import contextmanager
import traceback
from flask import Flask, request, jsonify

app = Flask(__name__)

@dataclass
class RegistraduriaData:
    nuip: str
    fecha_consulta: Optional[str] = None
    documento: Optional[str] = None
    estado: Optional[str] = None

def install_browser():
    """Install browser on startup"""
    logger = logging.getLogger('browser_install')
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

    try:
        # Set environment variables
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/opt/render/project/.playwright'
        os.environ['PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD'] = '0'
        os.environ['PLAYWRIGHT_SKIP_VALIDATION'] = '1'

        logger.info("Installing playwright browsers...")
        subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], 
                      check=True, capture_output=True)
        
        # Set permissions
        browser_path = os.environ['PLAYWRIGHT_BROWSERS_PATH']
        subprocess.run(['chmod', '-R', '777', browser_path], check=True)
        
        logger.info("Browser installation completed")
        return True
    except Exception as e:
        logger.error(f"Browser installation failed: {e}")
        return False

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
        
        # Use the environment variable set during installation
        self.browser_path = os.environ['PLAYWRIGHT_BROWSERS_PATH']
        self.logger.info(f"Using browser path: {self.browser_path}")

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
                yield page
            except Exception as e:
                self.logger.error(f"Error launching browser: {e}")
                self.logger.error(traceback.format_exc())
                raise
            finally:
                if browser:
                    try:
                        browser.close()
                    except Exception as e:
                        self.logger.error(f"Error closing browser: {e}")

    def scrape(self, nuip: str) -> Optional[RegistraduriaData]:
        """
        Scrape data for a given NUIP number.
        """
        try:
            with self._get_browser() as page:
                # Configure timeouts
                page.set_default_timeout(30000)
                page.set_default_navigation_timeout(30000)

                # Navigate to the page
                self.logger.info(f"Navigating to {self.URL}")
                page.goto(self.URL, wait_until="networkidle")

                # Wait for page load
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_load_state("networkidle")

                # Close banner if present
                try:
                    if page.is_visible(self.BANNER_CLOSE_SELECTOR, timeout=5000):
                        page.click(self.BANNER_CLOSE_SELECTOR)
                except PlaywrightTimeoutError:
                    self.logger.info("Banner not found or already closed")
                except Exception as e:
                    self.logger.warning(f"Error closing banner: {e}")

                # Enter NUIP and search
                try:
                    page.wait_for_selector(self.INPUT_SELECTOR, state="visible")
                    page.fill(self.INPUT_SELECTOR, nuip)
                    
                    page.wait_for_selector(self.BUTTON_SELECTOR, state="visible")
                    page.click(self.BUTTON_SELECTOR)
                except Exception as e:
                    self.logger.error(f"Error with form interaction: {e}")
                    return None

                # Extract results
                estado_text = None
                for xpath, description in [
                    (self.RESULTADOS_XPATH, "primary"),
                    (self.RESULTADOS_XPATH_ALTERNATIVE, "alternative")
                ]:
                    try:
                        page.wait_for_selector(f'xpath={xpath}', timeout=10000)
                        elemento = page.query_selector(f'xpath={xpath}')
                        if elemento:
                            estado_text = elemento.inner_text().strip()
                            break
                    except Exception:
                        continue

                return RegistraduriaData(nuip=nuip, estado=estado_text) if estado_text else None

        except Exception as e:
            self.logger.error(f"Scraping error: {e}")
            self.logger.error(traceback.format_exc())
            return None

# Flask routes
@app.route('/scrape', methods=['POST'])
def scrape():
    nuip = request.json.get('nuip')
    if not nuip:
        return jsonify({'error': 'NUIP is required'}), 400
    
    scraper = RegistraduriaScraper(headless=True)
    result = scraper.scrape(nuip)
    
    if result:
        return jsonify({
            'nuip': result.nuip,
            'estado': result.estado
        })
    return jsonify({'error': 'No data found'}), 404

@app.route('/')
def home():
    return "Simit Scraper API is running"

if __name__ == '__main__':
    # Install browser on startup
    if not install_browser():
        print("Failed to install browser. Exiting.")
        sys.exit(1)
        
    # Start Flask server
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)