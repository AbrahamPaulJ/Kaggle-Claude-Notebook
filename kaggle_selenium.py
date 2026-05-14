"""
Headless Firefox automation to start a Kaggle Jupyter Server session and return the JWT proxy URL.
Flow: edit page → Run menu → Kaggle Jupyter Server → Start Session → extract VSCode URL
"""
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os, re, json, time

PROFILE     = "/data/data/com.termux/files/home/.firefox-profiles/kaggle"
GECKODRIVER = "/data/data/com.termux/files/usr/bin/geckodriver"
CREDS_FILE  = os.path.join(os.path.dirname(__file__), ".kaggle_creds.json")

def _get_driver(headless=True):
    os.environ["DISPLAY"] = ":0"
    service = Service(GECKODRIVER)
    options = Options()
    options.add_argument("-profile")
    options.add_argument(PROFILE)
    if headless:
        options.add_argument("--headless")
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)
    return webdriver.Firefox(service=service, options=options)

CC_PREFIX = "cc-"  # only notebooks with this prefix are managed by this tool

def _get_active_slug():
    """Return slug of most-recently-run cc- notebook, or empty string if none found."""
    try:
        creds = json.load(open(CREDS_FILE))
        import requests
        r = requests.get(
            "https://api.kaggle.com/v1/kernels/list",
            headers={"Authorization": f"Bearer {creds['key']}", "Accept": "application/json"},
            params={"user": creds["username"], "pageSize": 50},
            timeout=10,
        )
        if r.ok:
            kernels = r.json()
            cc_kernels = [k for k in kernels if k.get("ref", "").split("/")[-1].startswith(CC_PREFIX)]
            if not cc_kernels:
                print(f"[selenium] No notebooks with '{CC_PREFIX}' prefix found. Rename your notebook to start with '{CC_PREFIX}'.")
                return ""
            latest = max(cc_kernels, key=lambda k: k.get("lastRunTime", ""))
            ref = latest.get("ref", "")
            slug = ref.split("/")[1] if "/" in ref else ref
            print(f"[selenium] Active notebook: {slug}")
            return slug
    except Exception as e:
        print(f"[selenium] slug lookup failed: {e}")
    return ""

def _click_by_text(driver, text, timeout=10):
    # Try multiple XPath strategies for React SPAs
    xpaths = [
        f"//*[normalize-space(text())='{text}']",
        f"//*[normalize-space(.)='{text}']",
        f"//button[contains(.,'{text}')]",
        f"//li[contains(.,'{text}')]",
        f"//span[contains(.,'{text}')]",
    ]
    last_err = None
    for xpath in xpaths:
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", el)
            driver.execute_script("arguments[0].click();", el)  # JS click bypasses overlays
            return el
        except Exception as e:
            last_err = e
    raise last_err

def _extract_url(page_source):
    m = re.search(
        r"https://kkb-production\.jupyter-proxy\.kaggle\.net/k/[^\"'\s\\<>]+",
        page_source
    )
    if m:
        url = m.group(0).rstrip("/")
        return url if url.endswith("/proxy") else url + "/proxy"
    return None

def fetch_jwt_url(kernel_slug=None, headless=True):
    """
    Start Kaggle Jupyter Server session and return JWT proxy URL.
    If session already running, returns URL immediately.
    """
    if not os.path.exists(PROFILE):
        print("[selenium] No saved login. Run kaggle_login.py first.")
        return None

    try:
        creds = json.load(open(CREDS_FILE))
        username = creds.get("username", "")
    except Exception:
        username = ""

    if not kernel_slug:
        kernel_slug = _get_active_slug()
    if not kernel_slug:
        print("[selenium] Could not determine active kernel slug.")
        return None

    edit_url = f"https://www.kaggle.com/code/{username}/{kernel_slug}/edit"
    print(f"[selenium] Opening {edit_url}")

    driver = None
    try:
        driver = _get_driver(headless=headless)
        driver.set_page_load_timeout(60)
        driver.get(edit_url)
        print("[selenium] Waiting for page to load...")
        time.sleep(12)  # Kaggle's notebook SPA takes a while

        # Case 1: session already running — URL in page HTML
        url = _extract_url(driver.page_source)
        if url:
            print(f"[selenium] Session already running, got URL.")
            return url

        # Case 2: need to start session via Run → Kaggle Jupyter Server → Start Session
        print("[selenium] No active session. Starting via Run menu...")

        # Debug: print visible top-level text to understand page state
        try:
            els = driver.find_elements(By.XPATH, "//button | //li[@role='menuitem'] | //a[@role='menuitem']")
            visible = [e.text.strip() for e in els if e.text.strip()][:20]
            print(f"[selenium] Visible elements: {visible}")
        except Exception:
            pass

        # Click Run menu
        try:
            _click_by_text(driver, "Run", timeout=15)
            print("[selenium] Clicked Run menu")
        except Exception as e:
            # Save screenshot for debugging
            driver.save_screenshot("/data/data/com.termux/files/home/Kaggle-Claude-Notebook/debug_screenshot.png")
            print(f"[selenium] Failed to click Run: {e}")
            print("[selenium] Screenshot saved to debug_screenshot.png")
            return None
        time.sleep(2)

        # Click Kaggle Jupyter Server in dropdown
        try:
            _click_by_text(driver, "Kaggle Jupyter Server", timeout=8)
            print("[selenium] Clicked Kaggle Jupyter Server")
        except Exception as e:
            driver.save_screenshot("/data/data/com.termux/files/home/Kaggle-Claude-Notebook/debug_screenshot.png")
            print(f"[selenium] Failed to click Kaggle Jupyter Server: {e}")
            return None
        time.sleep(2)

        # Click Start Session button in sidebar
        try:
            _click_by_text(driver, "Start Session", timeout=10)
            print("[selenium] Clicked Start Session")
        except Exception as e:
            driver.save_screenshot("/data/data/com.termux/files/home/Kaggle-Claude-Notebook/debug_screenshot.png")
            print(f"[selenium] Failed to click Start Session: {e}")
            return None
        print("[selenium] Waiting for session to start (up to 3 min)...")

        # Poll page source for JWT URL (session takes a while to start)
        for _ in range(36):  # 36 x 5s = 3 minutes
            time.sleep(5)
            url = _extract_url(driver.page_source)
            if url:
                print(f"[selenium] Session started, got URL.")
                return url
            print("[selenium] Still waiting...")

        print("[selenium] Timed out waiting for session.")
        return None

    except Exception as e:
        print(f"[selenium] Error: {e}")
        return None
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    url = fetch_jwt_url()
    if url:
        print("URL:", url)
    else:
        print("Failed.")
