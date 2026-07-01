import os
import time
from dotenv import load_dotenv
import requests
from playwright.sync_api import sync_playwright

# Load credentials from hidden .env profile
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# The customer-facing search page URL
TARGET_URL = "https://blinkit.com/s/?q=hot%20wheels"

TARGET_MODELS = [
    # JDM & Japanese Manufacturers
    "nissan", "skyline", "silvia", "gt-r", "datsun", "honda", "civic", "integra", "nsx", 
    "toyota", "supra", "celica", "ae86", "land cruiser", "mazda", "rx-7", "rx-8", "miata",
    "subaru", "impreza", "wrx", "mitsubishi", "lancer", "evo",

    # European Supercars & Classics
    "porsche", "911", "cayman", "carrera", "ferrari", "lamborghini", "countach", "huracan", 
    "aventador", "gallardo", "murcielago", "mclaren", "senna", "720s", "p1", "bugatti", "chiron", 
    "veyron", "aston martin", "jaguar", "lotus", "elise", "exige", "audi", "quattro", "r8",
    "bmw", "m3", "m4", "m5", "z4", "mercedes", "amg", "benz", "volkswagen", "vw", "beetle", "golf",

    # American Muscle & Trucks
    "chevy", "chevrolet", "camaro", "corvette", "silverado", "el camino", "impala", "nova", 
    "ford", "mustang", "gt40", "f-150", "raptor", "bronco", "shelby", "cobra", "dodge", 
    "charger", "challenger", "viper", "ram", "durango", "plymouth", "barracuda", "fury", 
    "pontiac", "gto", "firebird", "trans am", "buick", "riviera", "regal", "cadillac", 
    "jeep", "wrangler", "cherokee", "gmc", "tesla", "hummer", "lincoln", "chrysler",

    # Common Real-World Scale Spec Descriptors
    "die cast car", "die-cast car", "1:64", "gt3", "gt2", "turbo", "roadster", "targa",
    "convertible", "coupe", "sedan", "wagon", "pickup", "gasser", " Concept "
]


# Stateful persistent storage tracking what items have already been notified
previously_notified = set()

def dispatch_alert(item_name):
    """Pushes clean markdown notification payloads directly to your Telegram channel."""
    text_payload = (
        f"🏎️ *TARGET HOT WHEELS IN STOCK!*\n\n"
        f"📦 *Model:* {item_name}\n"
        f"🔗 *Search Link:* [View on Blinkit]({TARGET_URL})"
    )
    
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text_payload,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(telegram_url, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"[ALERT SENT] Notification pushed successfully for: {item_name}.")
        else:
            print(f"[TELEGRAM ERROR] API returned status code: {response.status_code}")
    except Exception as error:
        print(f"[NETWORK ERROR] Failed reaching Telegram: {error}")

def execute_browser_monitor(browser_context):
    """Uses a persistent browser context window to run clean inventory parsing sweeps."""
    global previously_notified
    
    page = browser_context.new_page()
    
    try:
        print("[MONITOR] Refreshing Blinkit catalog...")
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)
        
        # Allow client-side rendering frameworks to complete DOM injections
        page.wait_for_timeout(4000)
        
        # Target textual clusters representing product nodes
        product_elements = page.locator("[data-testid='product-card']").all() or page.locator("div.Product__Container").all()
        if not product_elements:
            product_elements = page.locator("div:has-text('Hot Wheels')").all()
            
        # Tracks unique items seen purely within THIS specific loop execution pass
        current_sweep_items = set()
        
        for element in product_elements:
            try:
                text_content = element.inner_text()
            except Exception:
                continue
                
            # Verification baseline: Valid Hot Wheels entry that can be purchased
            if "hot wheels" in text_content.lower() and "add" in text_content.lower():
                lines = [line.strip() for line in text_content.split("\n") if line.strip()]
                item_name = next((l for l in lines if "hot wheels" in l.lower()), None)
                
                if not item_name:
                    continue
                    
                # Whitelist evaluation check
                if TARGET_MODELS:
                    is_wanted = any(model in item_name.lower() for model in TARGET_MODELS)
                else:
                    is_wanted = True  # If list is empty, tracking default targets everything
                    
                if is_wanted:
                    # Deduplication Layer A: If we already parsed this item name during *this* sweep loop, skip it
                    if item_name in current_sweep_items:
                        continue
                        
                    current_sweep_items.add(item_name)
                    
                    # Deduplication Layer B: Check across time memory states
                    if item_name not in previously_notified:
                        dispatch_alert(item_name)
                        previously_notified.add(item_name)
                        
        # Retain state only for active items that remain live on the interface catalog
        # If an item disappears from current_sweep_items, it clears out of state memory,
        # allowing it to trigger a fresh alert if it gets restocked down the line.
        previously_notified = previously_notified.intersection(current_sweep_items)
        print(f"[MONITOR] Check complete. Active models available: {len(current_sweep_items)}")
        
    except Exception as error:
        print(f"[MONITOR ERROR] Iteration execution failed: {error}")
        
    finally:
        page.close()

if __name__ == "__main__":
    print("====== System Online: Persistent Targeted Monitor Engaged ======")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        while True:
            execute_browser_monitor(context)
            time.sleep(60)