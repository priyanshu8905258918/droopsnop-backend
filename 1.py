from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, Response
import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict
import json
import random
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Set up logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Price Comparison API",
             description="API for comparing prices across Amazon, Flipkart, and Meesho",
             version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    try:
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {str(e)}"}
        )

@app.get("/", response_class=HTMLResponse)
async def root():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Price Comparison</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        <style>
            .loading { display: none; text-align: center; margin: 20px 0; }
            .result-card { transition: all 0.3s ease; }
            .result-card:hover { transform: translateY(-5px); box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
        </style>
    </head>
    <body class="bg-gray-100 min-h-screen">
        <div class="container mx-auto px-4 py-8">
            <h1 class="text-4xl font-bold text-center mb-8 text-gray-800">Price Comparison</h1>
            
            <div class="max-w-2xl mx-auto bg-white rounded-lg shadow-md p-6 mb-8">
                <div class="flex gap-4">
                    <input type="text" id="productInput" 
                           class="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                           placeholder="Enter product name...">
                    <button onclick="searchProduct()" 
                            class="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors">
                        Search
                    </button>
                </div>
            </div>

            <div id="loading" class="loading">
                <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
                <p class="mt-4 text-gray-600">Searching for best prices...</p>
            </div>

            <div id="results" class="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-6xl mx-auto">
                <!-- Results will be inserted here -->
            </div>
        </div>

        <script>
            async function searchProduct() {
                const productInput = document.getElementById('productInput');
                const loading = document.getElementById('loading');
                const results = document.getElementById('results');
                
                if (!productInput.value.trim()) {
                    alert('Please enter a product name');
                    return;
                }

                loading.style.display = 'block';
                results.innerHTML = '';

                try {
                    const response = await fetch(`/compare/${encodeURIComponent(productInput.value)}`);
                    const data = await response.json();
                    
                    results.innerHTML = data.map(item => `
                        <div class="result-card bg-white rounded-lg shadow-md p-6">
                            <h2 class="text-xl font-semibold mb-4 text-gray-800">${item.platform}</h2>
                            <p class="text-2xl font-bold text-blue-600 mb-4">₹${item.price.toLocaleString()}</p>
                            ${item.link ? `
                                <a href="${item.link}" target="_blank" 
                                   class="block text-center px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors">
                                    View Product
                                </a>
                            ` : '<p class="text-red-500 text-center">Product not found</p>'}
                        </div>
                    `).join('');
                } catch (error) {
                    results.innerHTML = `
                        <div class="col-span-3 text-center text-red-500">
                            Error: ${error.message}
                        </div>
                    `;
                } finally {
                    loading.style.display = 'none';
                }
            }

            // Allow Enter key to trigger search
            document.getElementById('productInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    searchProduct();
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

def clean_price(price_str: str) -> float:
    try:
        # Extract numbers from price string
        numbers = re.findall(r'\d+', price_str)
        if numbers:
            return float(''.join(numbers))
        return 0.0
    except Exception as e:
        logger.error(f"Error cleaning price: {str(e)}")
        return 0.0

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--disable-popup-blocking')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Add additional preferences
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        # Execute CDP commands to prevent detection
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })
        return driver
    except Exception as e:
        logger.error(f"Error creating Chrome driver: {str(e)}")
        raise

def scrape_amazon(product_name: str) -> Dict:
    try:
        driver = get_driver()
        search_url = f"https://www.amazon.in/s?k={product_name.replace(' ', '+')}"
        logger.info(f"Scraping Amazon: {search_url}")
        
        driver.get(search_url)
        time.sleep(5)  # Increased wait time
        
        # Wait for product elements with increased timeout
        try:
            product = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-component-type="s-search-result"]'))
            )
            
            # Try different price selectors
            price_element = None
            for selector in ['span.a-price-whole', 'span.a-offscreen', 'span.a-price']:
                try:
                    price_element = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if price_element:
                        break
                except:
                    continue
            
            # Try different link selectors
            link_element = None
            for selector in ['a.a-link-normal.s-no-outline', 'a.a-link-normal.s-underline-text', 'a.a-link-normal']:
                try:
                    link_element = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if link_element:
                        break
                except:
                    continue
            
            price = clean_price(price_element.text) if price_element else 0
            link = link_element.get_attribute('href') if link_element else ""
            
            logger.info(f"Amazon found: Price={price}, Link={link}")
            driver.quit()
            return {
                "platform": "Amazon",
                "price": price,
                "link": link
            }
        except TimeoutException:
            logger.warning("No product found on Amazon")
            driver.quit()
    except Exception as e:
        logger.error(f"Amazon scraping error: {str(e)}")
        try:
            driver.quit()
        except:
            pass
    return {"platform": "Amazon", "price": 0, "link": ""}

def scrape_flipkart(product_name: str) -> Dict:
    try:
        driver = get_driver()
        search_url = f"https://www.flipkart.com/search?q={product_name.replace(' ', '%20')}"
        logger.info(f"Scraping Flipkart: {search_url}")
        
        driver.get(search_url)
        time.sleep(3)  # Wait for page to load
        
        # Wait for product elements
        try:
            product = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div._1AtVbE, div._4rR01T, div.tUxRFH, div._2kHMtA'))
            )
            
            # Try different price selectors
            price_element = None
            for selector in ['div._30jeq3', 'div._1_WHN1', 'div._16Jk6d']:
                try:
                    price_element = product.find_element(By.CSS_SELECTOR, selector)
                    if price_element:
                        break
                except:
                    continue
            
            # Try different link selectors
            link_element = None
            for selector in ['a._1fQZEK', 'a._2UzuFa', 'a.s1Q9rs']:
                try:
                    link_element = product.find_element(By.CSS_SELECTOR, selector)
                    if link_element:
                        break
                except:
                    continue
            
            price = clean_price(price_element.text) if price_element else 0
            link = link_element.get_attribute('href') if link_element else ""
            
            logger.info(f"Flipkart found: Price={price}, Link={link}")
            driver.quit()
            return {
                "platform": "Flipkart",
                "price": price,
                "link": link
            }
        except TimeoutException:
            logger.warning("No product found on Flipkart")
            driver.quit()
    except Exception as e:
        logger.error(f"Flipkart scraping error: {str(e)}")
        try:
            driver.quit()
        except:
            pass
    return {"platform": "Flipkart", "price": 0, "link": ""}

def scrape_meesho(product_name: str) -> Dict:
    try:
        driver = get_driver()
        search_url = f"https://www.meesho.com/search?q={product_name.replace(' ', '%20')}"
        logger.info(f"Scraping Meesho: {search_url}")
        
        driver.get(search_url)
        time.sleep(3)  # Wait for page to load
        
        # Wait for product elements
        try:
            product = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.ProductList__GridCol, div.sc-dkzDqf, div.ProductCard__BaseCard'))
            )
            
            # Try different price selectors
            price_element = None
            for selector in ['div.ProductCard__Price', 'div.sc-dkzDqf', 'div.ProductCard__PriceText']:
                try:
                    price_element = product.find_element(By.CSS_SELECTOR, selector)
                    if price_element:
                        break
                except:
                    continue
            
            # Try different link selectors
            link_element = None
            for selector in ['a.ProductCard__Link', 'a.sc-dkzDqf', 'a.ProductCard__BaseCard']:
                try:
                    link_element = product.find_element(By.CSS_SELECTOR, selector)
                    if link_element:
                        break
                except:
                    continue
            
            price = clean_price(price_element.text) if price_element else 0
            link = link_element.get_attribute('href') if link_element else ""
            
            logger.info(f"Meesho found: Price={price}, Link={link}")
            driver.quit()
            return {
                "platform": "Meesho",
                "price": price,
                "link": link
            }
        except TimeoutException:
            logger.warning("No product found on Meesho")
            driver.quit()
    except Exception as e:
        logger.error(f"Meesho scraping error: {str(e)}")
        try:
            driver.quit()
        except:
            pass
    return {"platform": "Meesho", "price": 0, "link": ""}

@app.get("/compare/{product_name}", tags=["Price Comparison"])
async def compare_prices(product_name: str) -> List[Dict]:
    logger.info(f"Compare endpoint accessed for product: {product_name}")
    try:
        if not product_name or len(product_name.strip()) == 0:
            raise HTTPException(status_code=400, detail="Product name cannot be empty")
            
        results = []
        
        # Scrape from all platforms
        amazon_result = scrape_amazon(product_name)
        time.sleep(2)  # Add delay between requests
        flipkart_result = scrape_flipkart(product_name)
        time.sleep(2)  # Add delay between requests
        meesho_result = scrape_meesho(product_name)
        
        results.extend([amazon_result, flipkart_result, meesho_result])
        logger.info(f"Results: {json.dumps(results, indent=2)}")
        return results
    except Exception as e:
        logger.error(f"Error in compare_prices: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting the application...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
