import json
import os
import time
import requests
from playwright.sync_api import sync_playwright

OPTIONS_PATH = "/data/options.json"
STATE_FILE = "/data/last_state.txt"

AVAILABLE = [
    "Zum Warenkorb hinzufügen",
    "In den Warenkorb",
    "Add to cart",
]

UNAVAILABLE = [
    "nicht vorrätig",
    "nicht verfügbar",
    "ausverkauft",
    "out of stock",
    "sold out",
]


def load_options():
    with open(OPTIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_last_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "unknown"


def set_last_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(state)


def send_webhook(url, msg):
    requests.post(url, json={"message": msg}, timeout=15).raise_for_status()


def detect_state(text):
    lower = text.lower()

    for item in AVAILABLE:
        if item.lower() in lower:
            return "available"

    for item in UNAVAILABLE:
        if item.lower() in lower:
            return "unavailable"

    return "unknown"


def check_product(product_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        page = browser.new_page()
        page.goto(product_url, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(12000)

        for selector in [
            "button:has-text('Akzeptieren')",
            "button:has-text('Alle akzeptieren')",
            "button:has-text('Accept')",
        ]:
            try:
                page.locator(selector).first.click(timeout=1500)
                page.wait_for_timeout(1000)
                break
            except Exception:
                pass

        page.wait_for_timeout(5000)
        text = page.locator("body").inner_text(timeout=10000)
        page.screenshot(path="/data/debug.png", full_page=True)
        browser.close()
        return detect_state(text)


def main():
    while True:
        options = load_options()
        product_url = options["product_url"]
        webhook_url = options["webhook_url"]
        interval_seconds = int(options.get("interval_seconds", 120))

        try:
            state = check_product(product_url)
            last_state = get_last_state()

            print(f"Detected state: {state} (previous: {last_state})")

            if state == "available" and last_state != "available":
                send_webhook(webhook_url, "Nintendo-Artikel verfügbar")

            set_last_state(state)

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(interval_seconds)


if __name__ == "__main__":
    main()
