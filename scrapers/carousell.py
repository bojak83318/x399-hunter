#!/usr/bin/env python3
"""
Carousell X399 scraper using Playwright (primary) and curl-cffi (backup).
Outputs JSON with normalized schema.
"""
import asyncio
import json
import argparse
import os
import sys
from datetime import datetime
from urllib.parse import urlparse
import yaml

# Import Playwright
from playwright.async_api import async_playwright

# Import curl_cffi for backup
try:
    from curl_cffi import requests as crequests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False


def parse_proxy_url(proxy_url):
    """
    Parses a proxy URL string into Playwright-compatible dictionary.
    Input: schema://user:pass@host:port
    Output: { "server": "schema://host:port", "username": "user", "password": "pass" }
    """
    if not proxy_url:
        return None
    
    parsed = urlparse(proxy_url)
    scheme = parsed.scheme if parsed.scheme else "http"
    
    # Reconstruct server URL without auth
    server = f"{scheme}://{parsed.hostname}:{parsed.port}"
    
    return {
        "server": server,
        "username": parsed.username,
        "password": parsed.password
    }

async def scrape_playwright(search_query, proxy_config=None, max_results=50):
    """
    Scrapes Carousell using Playwright.
    """
    print(f"  [Playwright] Searching for '{search_query}'...")
    results = []
    
    async with async_playwright() as p:
        # Launch options
        launch_args = {"headless": True}
        if proxy_config:
            launch_args["proxy"] = proxy_config
            
        browser = await p.chromium.launch(**launch_args)
        
        # Context options usually help avoid detection
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        
        page = await context.new_page()
        
        try:
            # Navigate
            url = f"https://www.carousell.sg/search/{search_query}"
            # Block heavy resources to speed up
            await page.route("**/*.{png,jpg,jpeg,gif,webp}", lambda route: route.abort())
            
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Smart wait for content
            try:
                await page.wait_for_selector('[data-testid="listing-card"]', timeout=15000)
            except:
                print("  [Playwright] Timeout waiting for listing cards. Checking for empty state or blocking.")
                # Snapshot for debug in a real scenario, but here just return empty or raise
                content = await page.content()
                if "No results found" in content:
                    print("  [Playwright] No results found.")
                    await browser.close()
                    return []
                # If we are here, might be blocked or structure changed
                raise Exception("Selector timeout - possible change in structure or blocking")

            # Extract
            cards = await page.query_selector_all('[data-testid="listing-card"]')
            print(f"  [Playwright] Found {len(cards)} cards (parsing max {max_results}).")
            
            for card in cards[:max_results]:
                try:
                    # Carousell structure heavily uses data-testid
                    title_el = await card.query_selector('p[data-testid="listing-card-text-title"]')
                    price_el = await card.query_selector('p[data-testid="listing-card-text-price"]')
                    link_el = await card.query_selector('a')
                    seller_el = await card.query_selector('p[data-testid="listing-card-text-seller-name"]')
                    
                    if not (title_el and price_el and link_el):
                        continue
                        
                    title = await title_el.inner_text()
                    price_text = await price_el.inner_text()
                    href = await link_el.get_attribute('href')
                    seller = await seller_el.inner_text() if seller_el else "Unknown"
                    
                    # Clean Price
                    # "S$1,234" -> 1234.0
                    price_clean = price_text.replace('S$', '').replace(',', '').strip()
                    try:
                        price_sgd = float(price_clean)
                    except ValueError:
                        price_sgd = 0.0
                        
                    full_url = f"https://www.carousell.sg{href}"
                    
                    results.append({
                        "title": title,
                        "price_sgd": price_sgd,
                        "seller": seller,
                        "url": full_url,
                        "source": "carousell",
                        "timestamp": datetime.utcnow().isoformat(),
                        "method": "playwright"
                    })
                except Exception as e:
                    continue # Skip bad card
                    
        except Exception as e:
            print(f"  [Playwright] Error: {e}")
            raise e # Re-raise to trigger backup
        finally:
            await browser.close()
            
    return results

def scrape_curl_cffi(search_query, proxy_url=None, max_results=50):
    """
    Backup scraper using curl_cffi to impersonate real browser TLS.
    Note: Carousell is an SPA (Single Page App). 
    This method attempts to get initial data from extracting JSON from script tags 
    or just pure HTML parsing if SSR is active.
    """
    if not CURL_CFFI_AVAILABLE:
        print("  [curl-cffi] Library not installed. Skipping backup.")
        return []
        
    print(f"  [curl-cffi] Backup search for '{search_query}'...")
    
    url = f"https://www.carousell.sg/search/{search_query}"
    proxies = {"https": proxy_url, "http": proxy_url} if proxy_url else None
    
    try:
        # Impersonate Chrome 110
        response = crequests.get(
            url,
            impersonate="chrome110",
            proxies=proxies,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"  [curl-cffi] Status {response.status_code}")
            return []
            
        # Basic HTML parsing - Looking for JSON embedded in Next.js/React hydration
        # This is brittle but common for SPAs
        # Strategy: Look for specific class names if simple parsing, 
        # but regexing the window.initialState is better.
        # For this MVP backup, we will try a simpler text search or basic bs4 if we had it.
        # Since we don't have bs4 in requirements, we'll do raw string parsing or standard lib html.parser.
        
        # Quick and dirty check if we got blocked
        if "Access Denied" in response.text or "Cloudflare" in response.text:
            print("  [curl-cffi] Blocked by WAF.")
            return []

        # NOTE: Parsing client-side rendered carousell with just requests is hard.
        # This is a placeholder for a robust API-based approach.
        print("  [curl-cffi] Page retrieved. (Parsing logic to be implemented for specific DOM structure)")
        
        # Logic: If we really needed this, we'd reverse the internal API:
        # https://www.carousell.sg/api-service/filter/search/2.2/
        # But that requires signing/tokens.
        # Returning empty for now to signify "tried but unimplemented backup parsing"
        # In a real deployed version, we would implement the API call here.
        return []

    except Exception as e:
        print(f"  [curl-cffi] Error: {e}")
        return []

async def main_async():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True, help='Path to targets.yaml')
    parser.add_argument('--output', required=True, help='Output JSON file')
    args = parser.parse_args()
    
    # Load config
    with open(args.config) as f:
        config = yaml.safe_load(f)
        
    # Get Proxy
    proxy_url = os.getenv('PROXY_URL')
    proxy_config = parse_proxy_url(proxy_url)
    
    all_results = []
    
    for query in config['carousell']['queries']:
        try:
            # Try Primary
            results = await scrape_playwright(query, proxy_config)
            all_results.extend(results)
        except Exception as e:
            print(f"⚠️ Primary scraper failed for '{query}'. Attempting backup...")
            # Try Backup (run sync in executor if needed, or just call direct)
            # using the raw proxy string for requests
            backup_results = scrape_curl_cffi(query, proxy_url)
            if backup_results:
                all_results.extend(backup_results)
            else:
                print(f"❌ Backup also failed (or unimplemented) for '{query}'.")

    # Save
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"✅ Scraped {len(all_results)} listings -> {args.output}")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
