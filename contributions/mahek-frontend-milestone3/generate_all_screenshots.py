import os
import sys
import time
import subprocess
import requests

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

py = "C:\\Users\\A2A\\Python311\\python.exe"

print("[1] Starting Backend...")
backend = subprocess.Popen([py, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"])
for _ in range(30):
    try:
        if requests.get("http://127.0.0.1:8000/health", timeout=1).status_code == 200:
            print("Backend ready.")
            break
    except Exception:
        time.sleep(0.5)

print("[2] Starting Streamlit Frontend...")
frontend = subprocess.Popen([
    py, "-m", "streamlit", "run", "app.py",
    "--server.port", "8501",
    "--server.headless", "true"
])
for _ in range(40):
    try:
        if requests.get("http://localhost:8501", timeout=1).status_code == 200:
            print("Frontend ready.")
            break
    except Exception:
        time.sleep(0.5)

time.sleep(6)

screenshot_dir = os.path.abspath("Internship_Report/screenshots")
os.makedirs(screenshot_dir, exist_ok=True)

chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--window-size=1600,1100")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")

driver = webdriver.Chrome(options=chrome_options)
driver.set_window_size(1600, 1100)

try:
    print("[3] Loading dashboard...")
    driver.get("http://localhost:8501")
    time.sleep(10)  # Wait for full streamlit rendering

    def save(name):
        path = os.path.join(screenshot_dir, name)
        driver.save_screenshot(path)
        print(f"Captured: {name} ({os.path.getsize(path)} bytes)")

    # Helper function to click tab by text
    def click_tab_by_text(label_part):
        curr_tabs = driver.find_elements(By.CSS_SELECTOR, "[role='tab'], [data-baseweb='tab']")
        for t in curr_tabs:
            if label_part.lower() in t.text.lower():
                driver.execute_script("arguments[0].scrollIntoView(true);", t)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", t)
                time.sleep(3)
                return True
        return False

    def click_button_by_text(label_part):
        btns = driver.find_elements(By.TAG_NAME, "button")
        for b in btns:
            if label_part.lower() in b.text.lower():
                driver.execute_script("arguments[0].scrollIntoView(true);", b)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", b)
                time.sleep(3)
                return True
        return False

    # 1. Capture Leads Management
    print("\n--- 1. Capturing Leads Management ---")
    click_tab_by_text("Leads Management")
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1.5)
    save("fig2_leads_management.png")

    # Capture Subtab: Active Prospects Directory
    print("Capturing Leads Directory table...")
    click_tab_by_text("Active Prospects Directory")
    driver.execute_script("window.scrollTo(0, 200);")
    time.sleep(1.5)
    save("fig2b_leads_directory.png")

    # 2. Capture Lead Intelligence & Scoring
    print("\n--- 2. Capturing Lead Intelligence & Scoring ---")
    click_tab_by_text("Lead Intelligence")
    time.sleep(2)
    # Trigger AI profiling & scoring
    click_button_by_text("Compute Qualification Score")
    time.sleep(2)
    click_button_by_text("Generate AI Company Profile Analysis")
    time.sleep(3)
    driver.execute_script("window.scrollTo(0, 180);")
    time.sleep(1.5)
    save("fig3_lead_intelligence.png")

    # Scroll to qualification score hero
    driver.execute_script("window.scrollTo(0, 480);")
    time.sleep(1.5)
    save("fig4_lead_scoring.png")

    # 3. Capture Outreach Studio
    print("\n--- 3. Capturing Outreach Studio ---")
    click_tab_by_text("Outreach Studio")
    time.sleep(2)
    click_button_by_text("Generate Personalized Email")
    time.sleep(3)
    driver.execute_script("window.scrollTo(0, 120);")
    time.sleep(1.5)
    save("fig5_outreach_studio.png")

    # Scroll to email preview / editor
    driver.execute_script("window.scrollTo(0, 480);")
    time.sleep(1.5)
    save("fig6_ai_email_generator.png")

    # 4. Capture Executive Dashboard
    print("\n--- 4. Capturing Executive Dashboard ---")
    click_tab_by_text("Executive Dashboard")
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1.5)
    save("fig1_main_dashboard.png")

    # Scroll down on executive dashboard to capture charts and leaderboard
    driver.execute_script("window.scrollTo(0, 450);")
    time.sleep(1.5)
    save("fig1b_dashboard_analytics.png")

    print("\nAll real screenshots captured successfully!")

finally:
    driver.quit()
    backend.terminate()
    frontend.terminate()
    print("Terminated server processes.")
