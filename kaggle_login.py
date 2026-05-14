"""
One-time login script. Run once with Termux:X11 open to save your Kaggle Google session.
Usage: python3 kaggle_login.py
"""
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
import os

PROFILE = "/data/data/com.termux/files/home/.firefox-profiles/kaggle"
GECKODRIVER = "/data/data/com.termux/files/usr/bin/geckodriver"

os.makedirs(PROFILE, exist_ok=True)
os.environ["DISPLAY"] = ":0"

service = Service(GECKODRIVER)
options = Options()
options.add_argument("-profile")
options.add_argument(PROFILE)
options.set_preference("dom.webdriver.enabled", False)
options.set_preference("useAutomationExtension", False)
options.set_preference("general.useragent.override",
    "Mozilla/5.0 (Android 13; Mobile; rv:120.0) Gecko/120.0 Firefox/120.0")

print("Opening Firefox with Kaggle login page...")
driver = webdriver.Firefox(service=service, options=options)
driver.get("https://www.kaggle.com/account/login")

input("\nLog in with Google in the X11 window, wait for Kaggle home to load, then press Enter here...")
driver.quit()
print("Session saved to", PROFILE)
