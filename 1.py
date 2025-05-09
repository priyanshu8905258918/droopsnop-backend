from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Price Comparison API is running. Use /compare/{product_name} to search for products."}

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
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    return webdriver.Chrome(options=chrome_options)

def scrape_amazon(product_name: str) -> Dict:
    try:
        driver = get_driver()
        search_url = f"https://www.amazon.in/s?k={product_name.replace(' ', '+')}"
        logger.info(f"Scraping Amazon: {search_url}")
        
        driver.get(search_url)
        time.sleep(3)  # Wait for page to load
        
        # Wait for product elements
        try:
            product = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-component-type="s-search-result"]'))
            )
            
            # Try different price selectors
            price_element = None
            for selector in ['span.a-price-whole', 'span.a-offscreen', 'span.a-price']:
                try:
                    price_element = product.find_element(By.CSS_SELECTOR, selector)
                    if price_element:
                        break
                except:
                    continue
            
            # Try different link selectors
            link_element = None
            for selector in ['a.a-link-normal.s-no-outline', 'a.a-link-normal.s-underline-text', 'a.a-link-normal']:
                try:
                    link_element = product.find_element(By.CSS_SELECTOR, selector)
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

@app.get("/compare/{product_name}")
async def compare_prices(product_name: str) -> List[Dict]:
    logger.info(f"\nSearching for: {product_name}")
    results = []
    
    # Scrape from all platforms
    amazon_result = scrape_amazon(product_name)
    flipkart_result = scrape_flipkart(product_name)
    meesho_result = scrape_meesho(product_name)
    
    results.extend([amazon_result, flipkart_result, meesho_result])
    logger.info(f"Results: {json.dumps(results, indent=2)}")
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
