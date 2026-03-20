import requests
from playwright.sync_api import sync_playwright
import json

OPTIONS_PATH = "/data/options.json"

AVAILABLE = ["Zum Warenkorb hinzufügen", "In den Warenkorb"]
UNAVAILABLE = ["nicht vorrätig", "ausverkauft"]

def load_options():
    with open(OPTIONS_PATH, "r") as f:
        return json.load(f)

def send_webhook(url, msg):
    requests.post(url, json={"message": msg}, timeout=10)

def main():
    opt = load_options()
    url = opt["product_url"]
    webhook = opt["webhook_url"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(url, timeout=60000)
        page.wait_for_timeout(10000)

        text = page.inner_text("body")

        browser.close()

    if any(x.lower() in text.lower() for x in AVAILABLE):
        send_webhook(webhook, "AVAILABLE")
    elif any(x.lower() in text.lower() for x in UNAVAILABLE):
        print("not available")
    else:
        print("unknown")

if __name__ == "__main__":
    main()
