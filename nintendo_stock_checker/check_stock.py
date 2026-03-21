import json
import os
import time
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

OPTIONS_PATH = "/data/options.json"
STATE_FILE = "/data/last_state.txt"

UNAVAILABLE_TEXT = "nicht vorrätig"


def log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}", flush=True)


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
    log(f"Webhook senden → {msg}")
    requests.post(url, json={"message": msg}, timeout=15).raise_for_status()


def detect_state(text):
    lower = text.lower()

    if UNAVAILABLE_TEXT in lower:
        return "unavailable"

    return "available"


def check_product(product_url):
    log(f"Öffne Seite: {product_url}")

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
                log("Cookie-Banner geschlossen")
                page.wait_for_timeout(1000)
                break
            except Exception:
                pass

        page.wait_for_timeout(5000)

        text = page.locator("body").inner_text(timeout=10000)
        page.screenshot(path="/data/debug.png", full_page=True)
        browser.close()

        preview = text[:1500].replace("\n", " ")
        log(f"Seitentext-Vorschau: {preview}")
        log(f"Prüfe auf Text: '{UNAVAILABLE_TEXT}'")

        state = detect_state(text)
        log(f"Erkannter Zustand: {state}")

        return state


def main():
    log("=== Add-on gestartet ===")

    while True:
        try:
            options = load_options()
            product_url = options["product_url"]
            webhook_url = options["webhook_url"]
            interval_seconds = int(options.get("interval_seconds", 120))

            log("Starte neuen Prüfzyklus")

            state = check_product(product_url)
            last_state = get_last_state()

            log(f"Vorheriger Zustand: {last_state}")

            if state == "available" and last_state != "available":
                send_webhook(webhook_url, "Nintendo-Artikel verfügbar")

            set_last_state(state)

            log(f"Warte {interval_seconds} Sekunden bis zum nächsten Check")
            log("----------------------------------------")

        except Exception as e:
            log(f"FEHLER: {e}")

        time.sleep(interval_seconds)


if __name__ == "__main__":
    main()
