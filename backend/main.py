from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
import time
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_driver():
    """Initialize and return a Chrome WebDriver instance."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    return webdriver.Chrome(options=chrome_options)

def extract_price(price_text):
    """Extract numeric price from text."""
    if not price_text:
        return 0
    # Remove currency symbols and commas, then convert to float
    price = re.sub(r'[^\d.]', '', price_text)
    try:
        return float(price)
    except ValueError:
        return 0

def scrape_amazon(query):
    """Scrape product information from Amazon."""
    try:
        driver = get_driver()
        url = f"https://www.amazon.in/s?k={query.replace(' ', '+')}"
        logger.info(f"Scraping Amazon: {url}")
        
        driver.get(url)
        time.sleep(2)  # Wait for page load
        
        # Wait for product elements
        wait = WebDriverWait(driver, 10)
        product = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-component-type="s-search-result"]'))
        )
        
        # Extract price
        price_element = product.find_element(By.CSS_SELECTOR, 'span.a-price-whole')
        price = extract_price(price_element.text)
        
        # Extract link
        link_element = product.find_element(By.CSS_SELECTOR, 'h2 a')
        link = link_element.get_attribute('href')
        
        logger.info(f"Amazon found: Price={price}, Link={link}")
        return {"platform": "Amazon", "price": price, "link": link}
    except Exception as e:
        logger.error(f"Amazon scraping error: {str(e)}")
        return {"platform": "Amazon", "price": 0, "link": ""}
    finally:
        driver.quit()

def scrape_flipkart(query):
    """Scrape product information from Flipkart."""
    try:
        driver = get_driver()
        url = f"https://www.flipkart.com/search?q={query.replace(' ', '%20')}"
        logger.info(f"Scraping Flipkart: {url}")
        
        driver.get(url)
        time.sleep(2)  # Wait for page load
        
        # Wait for product elements
        wait = WebDriverWait(driver, 10)
        product = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div._1AtVbE, div._4rR01T, div.tUxRFH, div._2kHMtA'))
        )
        
        # Extract price
        price_element = product.find_element(By.CSS_SELECTOR, 'div._30jeq3, div._1_WHN1')
        price = extract_price(price_element.text)
        
        # Extract link
        link_element = product.find_element(By.CSS_SELECTOR, 'a._1fQZEK, a._2UzuFa')
        link = link_element.get_attribute('href')
        
        logger.info(f"Flipkart found: Price={price}, Link={link}")
        return {"platform": "Flipkart", "price": price, "link": link}
    except Exception as e:
        logger.error(f"Flipkart scraping error: {str(e)}")
        return {"platform": "Flipkart", "price": 0, "link": ""}
    finally:
        driver.quit()

def scrape_meesho(query):
    """Scrape product information from Meesho."""
    try:
        driver = get_driver()
        url = f"https://www.meesho.com/search?q={query.replace(' ', '%20')}"
        logger.info(f"Scraping Meesho: {url}")
        
        driver.get(url)
        time.sleep(2)  # Wait for page load
        
        # Wait for product elements
        wait = WebDriverWait(driver, 10)
        product = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.ProductList__GridCol-sc-8lnc8o-0'))
        )
        
        # Extract price
        price_element = product.find_element(By.CSS_SELECTOR, 'span.ProductPrice__Price-sc-1e0n1w-0')
        price = extract_price(price_element.text)
        
        # Extract link
        link_element = product.find_element(By.CSS_SELECTOR, 'a')
        link = link_element.get_attribute('href')
        
        logger.info(f"Meesho found: Price={price}, Link={link}")
        return {"platform": "Meesho", "price": price, "link": link}
    except Exception as e:
        logger.warning(f"No product found on Meesho")
        return {"platform": "Meesho", "price": 0, "link": ""}
    finally:
        driver.quit()

@app.get("/compare/{query}")
async def compare_prices(query: str):
    """Compare prices across different platforms."""
    logger.info(f"\nSearching for: {query}")
    
    results = []
    results.append(scrape_amazon(query))
    results.append(scrape_flipkart(query))
    results.append(scrape_meesho(query))
    
    logger.info(f"Results: {results}")
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 