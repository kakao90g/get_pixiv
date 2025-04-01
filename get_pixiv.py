import logging
import os
import sys
import json
import tkinter as tk
from tkinter import ttk, messagebox
from contextlib import redirect_stdout
from io import StringIO
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, InvalidSessionIdException, NoSuchWindowException
import time
import random
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import threading
import webbrowser
import subprocess

# Version constant
VERSION = "1.03"

# Suppress WebDriver Manager logs
os.environ['WDM_LOG'] = '0'

# Suppress urllib3 "Connection pool is full" INFO logs
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.FileHandler("output.log", mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger()

# Global variables
TIMEOUT = 20
COOKIE_FILE = "pixiv_cookies.json"
save_folder_base = "pixiv_images"
headers = {
    "Referer": "https://www.pixiv.net/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
}

class CustomDialog(tk.Toplevel):
    def __init__(self, parent, title, message, buttons=None, link=None):
        super().__init__(parent)
        self.parent = parent
        self.grab_set()
        self.title(title)
        self.resizable(False, False)
        tk.Label(self, text=message, justify="center", wraplength=280).pack(pady=10)
        if link:
            link_label = tk.Label(self, text=link, fg="blue", cursor="hand2", wraplength=280)
            link_label.pack(pady=5)
            link_label.bind("<Button-1>", lambda e: webbrowser.open(link))
        if buttons is None:
            buttons = [("OK", self.on_close)]
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        for text, command in buttons:
            tk.Button(btn_frame, text=text, command=command, width=10).pack(side="left", padx=2)
        self.update_idletasks()
        width = max(300, self.winfo_width())
        height = self.winfo_height()
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.update()
        self.lift()
        self.focus_force()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.destroy()

class PixivDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"get pixiv")
        self.driver = None
        self.is_headless = True
        self.cookies = []
        self.cookies_valid = False
        self.user_id = ""
        self.target_count = 0
        self.total_pages = 0
        self.log_handler = None
        self.stop_download = False
        self.fetch_complete = False
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount("https://", HTTPAdapter(max_retries=retries))
        self.show_browser_var = tk.BooleanVar(value=False)
        self.setup_ui()
        self.load_cookies()
        self.root.update_idletasks()
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = screen_width - window_width - 150
        y = 100
        self.root.geometry(f"+{x}+{y}")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        # pixiv Cookies Frame
        cookie_frame = ttk.LabelFrame(self.root, text="pixiv Cookies")
        cookie_frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(cookie_frame, text="Cookie String:").grid(row=0, column=0, padx=5, pady=5)
        self.cookie_entry = ttk.Entry(cookie_frame, width=50)
        self.cookie_entry.grid(row=0, column=1, padx=(5, 0), pady=5)
        self.clear_cookie_entry_button = ttk.Button(cookie_frame, text="Clear", command=self.clear_cookie_entry)
        self.clear_cookie_entry_button.grid(row=0, column=2, padx=0, pady=5)
        self.paste_cookie_button = ttk.Button(cookie_frame, text="Paste", command=self.paste_cookie)
        self.paste_cookie_button.grid(row=0, column=3, padx=(0, 5), pady=5)

        self.save_cookie_button = ttk.Button(cookie_frame, text="Save Cookies", command=self.save_cookie_string, width=15)
        self.save_cookie_button.grid(row=1, column=0, columnspan=2, pady=5)

        self.verify_cookies_button = ttk.Button(cookie_frame, text="Verify Cookies", command=self.verify_cookies, width=15)
        self.verify_cookies_button.grid(row=2, column=0, columnspan=2, pady=5)
        self.verify_cookies_button.config(state="disabled")

        self.clear_cookie_button = ttk.Button(cookie_frame, text="Clear Cookies", command=self.clear_cookies, state="disabled", width=15)
        self.clear_cookie_button.grid(row=3, column=0, columnspan=2, pady=5)
        
        # Options Frame
        options_frame = ttk.LabelFrame(self.root, text="Options")
        options_frame.pack(padx=10, pady=5, fill="x")

        ttk.Checkbutton(options_frame, text="Show browser", variable=self.show_browser_var).grid(row=0, column=0, padx=5, pady=5)
        self.about_button = ttk.Button(options_frame, text="About", command=self.show_about)
        self.about_button.grid(row=0, column=1, padx=5, pady=5)

        # Search User ID Frame
        user_frame = ttk.LabelFrame(self.root, text="Search User ID")
        user_frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(user_frame, text="User ID:").grid(row=0, column=0, padx=5, pady=5)
        self.user_id_entry = ttk.Entry(user_frame)
        self.user_id_entry.grid(row=0, column=1, padx=(5, 0), pady=5)
        self.clear_user_button = ttk.Button(user_frame, text="Clear", command=self.clear_user_id)
        self.clear_user_button.grid(row=0, column=2, padx=0, pady=5)
        self.paste_user_button = ttk.Button(user_frame, text="Paste", command=self.paste_user_id)
        self.paste_user_button.grid(row=0, column=3, padx=(0, 5), pady=5)

        self.search_button = ttk.Button(user_frame, text="Search", command=self.search_user_id, state="disabled")
        self.search_button.grid(row=1, column=0, columnspan=2, pady=5)

        # Download Artworks Frame
        download_frame = ttk.LabelFrame(self.root, text="Download Artworks")
        download_frame.pack(padx=10, pady=5, fill="x")

        self.artwork_label = ttk.Label(download_frame, text="Artworks: 0")
        self.artwork_label.grid(row=0, column=0, columnspan=4, padx=5, pady=5)

        self.download_button = ttk.Button(download_frame, text="Download All", command=self.start_download, state="disabled", width=15)
        self.download_button.grid(row=1, column=0, padx=5, pady=5)

        self.download_page_button = ttk.Button(download_frame, text="Download Page", command=self.start_download_page, state="disabled", width=15)
        self.download_page_button.grid(row=2, column=0, padx=5, pady=5)

        # Frame for page dropdown and label
        page_frame = ttk.Frame(download_frame)
        page_frame.grid(row=2, column=1, padx=0, pady=5, sticky="w")
        self.page_combo = ttk.Combobox(page_frame, values=[""], width=5, state="disabled")
        self.page_combo.pack(side=tk.LEFT)
        self.page_label = ttk.Label(page_frame, text="of 0 pages")
        self.page_label.pack(side=tk.LEFT, padx=(2, 0))

        self.download_url_button = ttk.Button(download_frame, text="Download URL", command=self.start_download_url, state="disabled", width=15)
        self.download_url_button.grid(row=3, column=0, padx=5, pady=5)

        self.url_entry = ttk.Entry(download_frame, width=45)
        self.url_entry.grid(row=3, column=1, padx=0, pady=5)
        self.clear_url_button = ttk.Button(download_frame, text="Clear", command=self.clear_url)
        self.clear_url_button.grid(row=3, column=2, padx=0, pady=5)
        self.paste_url_button = ttk.Button(download_frame, text="Paste", command=self.paste_url)
        self.paste_url_button.grid(row=3, column=3, padx=0, pady=5)

        self.stop_button = ttk.Button(download_frame, text="Stop", command=self.stop_download_process, state="disabled", width=15)
        self.stop_button.grid(row=4, column=0, pady=5)

        # Log Frame
        log_frame = ttk.LabelFrame(self.root, text="Log")
        log_frame.pack(padx=10, pady=5, fill="both", expand=True)

        self.log_text = tk.Text(log_frame, height=10, width=90, state="disabled")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, padx=5, pady=5, fill="both", expand=True)
        scrollbar.pack(side=tk.RIGHT, fill="y")

        self.progress_bar = ttk.Progressbar(self.root, length=200, mode="determinate")
        self.progress_bar.pack(padx=10, pady=(5, 10))

        self.log_handler = TextHandler(self.log_text)
        logger.addHandler(self.log_handler)

    def show_about(self):
        about_window = tk.Toplevel(self.root)
        about_window.title("About")
        about_window.resizable(False, False)
        about_window.transient(self.root)
        about_window.grab_set()

        about_text = f"get pixiv v{VERSION}\nA Pixiv artwork downloader.\nLicense: MIT\n© 2025 @kakao90g\nSupport this project: "
        static_label = tk.Label(about_window, text=about_text, justify="center")
        static_label.pack(pady=5)

        paypal_url = "https://paypal.me/kakao90g"
        link_label = tk.Label(about_window, text=paypal_url, fg="blue", cursor="hand2", justify="center")
        link_label.pack()
        link_label.bind("<Button-1>", lambda e: webbrowser.open_new_tab(paypal_url))

        check_button = tk.Button(about_window, text="Check for Updates", command=self.check_for_updates)
        check_button.pack(pady=5)

        about_window.update_idletasks()
        about_width = 300
        about_height = 150
        app_width = self.root.winfo_width()
        app_height = self.root.winfo_height()
        app_x = self.root.winfo_x()
        app_y = self.root.winfo_y()
        about_x = app_x + (app_width - about_width) // 2
        about_y = app_y + (app_height - about_height) // 2
        about_window.geometry(f"{about_width}x{about_height}+{about_x}+{about_y}")

    def check_for_updates(self):
        url = "https://github.com/kakao90g/get_pixiv/releases"
        try:
            response = self.session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            latest_tag = soup.find("span", class_="Label--success", string="Latest")
            if not latest_tag:
                raise ValueError("Could not find 'Latest' tag")
            version_link = latest_tag.find_previous("a", class_="Link--primary")
            if not version_link:
                raise ValueError("Could not find version link")
            latest_version = version_link.text.strip().split("v")[-1]
            current_version = VERSION
            if latest_version == current_version:
                CustomDialog(self.root, "Update Check", "Version is up to date.")
            elif tuple(map(int, latest_version.split("."))) > tuple(map(int, current_version.split("."))):
                self.show_update_dialog(latest_version)
            else:
                CustomDialog(self.root, "Update Check", "Version is up to date.")
        except Exception as e:
            logger.error(f"Failed to check for updates: {str(e)}")
            CustomDialog(self.root, "Update Check", "Unable to check for updates.")

    def show_update_dialog(self, new_version):
        current_exe = sys.executable if getattr(sys, "frozen", False) else None
        if not current_exe:
            CustomDialog(self.root, "Update Check", 
                        "Please download the latest release from:",
                        link="https://github.com/kakao90g/get_pixiv/releases")
            return

        updater_path = os.path.join(os.path.dirname(current_exe), "updater.exe")
        github_link = "https://github.com/kakao90g/get_pixiv/releases"

        def run_updater():
            subprocess.Popen([updater_path, new_version])
            self.on_closing()

        def on_no(parent_dialog):
            parent_dialog.destroy()
            CustomDialog(self.root, "Update",
                        "Please download from:",
                        link=github_link)

        if os.path.exists(updater_path):
            update_dialog = CustomDialog(self.root, "Update Available",
                                        f"New version v{new_version} is available.\nDo you want to run the updater now?",
                                        buttons=[("Yes", run_updater), 
                                                 ("No", lambda: on_no(update_dialog))])
        else:
            def download_and_run():
                try:
                    updater_url = f"https://github.com/kakao90g/get_pixiv/releases/latest/download/updater.exe"
                    response = self.session.get(updater_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30, stream=True)
                    response.raise_for_status()
                    with open(updater_path, "wb") as f:
                        f.write(response.content)
                    if os.path.getsize(updater_path) > 0:
                        run_updater()
                    else:
                        raise ValueError("Updater download is empty")
                except Exception as e:
                    logger.error(f"Failed to download updater: {str(e)}")
                    CustomDialog(self.root, "Update Error",
                                "Failed to download updater. Please get it from:",
                                link=github_link)

            update_dialog = CustomDialog(self.root, "Update Available",
                                        f"New version v{new_version} is available.\nDo you want to download and run the updater now?",
                                        buttons=[("Yes", download_and_run), 
                                                 ("No", lambda: on_no(update_dialog))])

    def save_cookie_string(self):
        cookie_string = self.cookie_entry.get().strip()
        if not cookie_string:
            logger.error("No cookie string provided. Please enter a cookie string.")
            return

        try:
            if cookie_string.startswith('['):
                self.cookies = json.loads(cookie_string)
                if not all(isinstance(c, dict) and "name" in c and "value" in c for c in self.cookies):
                    raise ValueError("Invalid JSON cookie format.")
            else:
                cookie_parts = [c for c in cookie_string.split("; ") if "=" in c]
                if not cookie_parts:
                    raise ValueError("Cookie string must contain at least one 'name=value' pair.")
                self.cookies = [dict(name=c.split("=", 1)[0], value=c.split("=", 1)[1], domain=".pixiv.net")
                                for c in cookie_parts]

            if not self.cookies:
                raise ValueError("No valid cookies parsed from the string.")

            with open(COOKIE_FILE, "w") as f:
                json.dump(self.cookies, f)
            headers["Cookie"] = "; ".join(f"{c['name']}={c['value']}" for c in self.cookies)
            self.cookies_valid = True
            self.clear_cookie_button.config(state="normal")
            self.search_button.config(state="normal")
            self.download_url_button.config(state="normal")
            self.verify_cookies_button.config(state="normal")
            logger.info("Cookies saved successfully!")
            self.cookie_entry.delete(0, tk.END)
        except Exception as e:
            logger.error(f"Failed to process cookie string: {e}")

    def clear_cookies(self):
        if os.path.exists(COOKIE_FILE):
            os.remove(COOKIE_FILE)
        if self.driver:
            self.driver.quit()
            self.driver = None
        self.cookies = []
        self.cookies_valid = False
        self.user_id = ""
        self.target_count = 0
        self.total_pages = 0
        self.fetch_complete = False
        self.clear_cookie_button.config(state="disabled")
        self.search_button.config(state="disabled")
        self.download_button.config(state="disabled")
        self.download_page_button.config(state="disabled")
        self.download_url_button.config(state="disabled")
        self.user_id_entry.delete(0, tk.END)
        self.url_entry.delete(0, tk.END)
        self.artwork_label.config(text="Artworks: 0")
        self.page_label.config(text="of 0 pages")
        self.page_combo.config(state="normal")
        self.page_combo.set("")
        self.page_combo.config(state="disabled")
        self.progress_bar["value"] = 0
        logger.info("Cookies cleared.")

    def save_cookies(self):
        with open(COOKIE_FILE, "w") as f:
            json.dump(self.cookies, f)

    def load_cookies(self):
        if os.path.exists(COOKIE_FILE):
            with open(COOKIE_FILE, "r") as f:
                self.cookies = json.load(f)
            
            headers["Cookie"] = "; ".join(f"{c['name']}={c['value']}" for c in self.cookies)
            self.cookies_valid = True
            self.clear_cookie_button.config(state="normal")
            self.search_button.config(state="normal")
            self.download_url_button.config(state="normal")
            self.verify_cookies_button.config(state="normal")
            logger.info("Cookies loaded from file.")
        else:
            logger.info("No cookie file found. Please enter a cookie string.")

    def verify_cookies(self):
        if not self.cookies:
            logger.error("No cookies available to verify. Please enter a cookie string.")
            return

        user_id = None
        for cookie in self.cookies:
            if cookie["name"] == "__utmv":
                value = cookie["value"]
                match = re.search(r"user_id=(\d+)", value)
                if match:
                    user_id = match.group(1)
                    break
        
        if not user_id:
            logger.error("Could not extract user ID from cookies. Using default URL.")
            url = "https://www.pixiv.net/en/"
        else:
            url = f"https://www.pixiv.net/en/users/{user_id}"

        logger.info("Verifying cookies...")
        self.verify_cookies_button.config(state="disabled")
        
        driver = self.restart_driver(None, force_headless=False)
        if not driver:
            logger.error("Could not initialize browser for cookie verification.")
            self.verify_cookies_button.config(state="normal")
            return

        try:
            driver.get(url)
            try:
                WebDriverWait(driver, 5).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/login.php')]")),
                        EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Login')]"))
                    )
                )
                logger.warning("Cookies need a refresh, please enter a new one.")
            except TimeoutException:
                logger.info("Cookies are still valid.")
        except Exception as e:
            logger.error(f"Error verifying cookies: {e}")
        finally:
            driver.quit()
            self.verify_cookies_button.config(state="normal")

    def search_user_id(self):
        self.user_id = self.user_id_entry.get()
        if not self.user_id.isdigit():
            logger.error("Invalid User ID. Please enter a valid number.")
            return

        self.search_button.config(state="disabled")
        self.download_button.config(state="disabled")
        self.download_page_button.config(state="disabled")
        self.download_url_button.config(state="disabled")
        self.verify_cookies_button.config(state="disabled")
        logger.info(f"Searching for User ID: {self.user_id}")
        self.driver = self.restart_driver(self.driver, force_headless=None)
        if not self.driver:
            logger.error("Search aborted: Could not initialize browser.")
            self.search_button.config(state="normal")
            self.download_url_button.config(state="normal")
            self.verify_cookies_button.config(state="normal")
            return
        
        self.driver.get(f"https://www.pixiv.net/en/users/{self.user_id}")
        threading.Thread(target=self.fetch_artwork_count_and_pages, daemon=True).start()

    def clear_user_id(self):
        self.user_id_entry.delete(0, tk.END)

    def paste_user_id(self):
        try:
            clipboard_text = self.root.clipboard_get()
            self.user_id_entry.delete(0, tk.END)
            self.user_id_entry.insert(0, clipboard_text)
        except tk.TclError:
            pass

    def clear_cookie_entry(self):
        self.cookie_entry.delete(0, tk.END)

    def paste_cookie(self):
        try:
            clipboard_text = self.root.clipboard_get()
            self.cookie_entry.delete(0, tk.END)
            self.cookie_entry.insert(0, clipboard_text)
        except tk.TclError:
            pass

    def clear_url(self):
        self.url_entry.delete(0, tk.END)

    def paste_url(self):
        try:
            clipboard_text = self.root.clipboard_get()
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, clipboard_text)
        except tk.TclError:
            pass

    def fetch_artwork_count_and_pages(self):
        error_occurred = False
        try:
            if not self.cookies_valid:
                logger.error("Cookies are not validated. Please save valid cookies first.")
                return
            if not self.driver or not self.is_session_valid(self.driver):
                logger.error("Browser session invalid or closed. Aborting search.")
                self.fetch_complete = False
                self.root.after(0, self.reset_ui)
                return
            base_url = f"https://www.pixiv.net/en/users/{self.user_id}"
            self.driver.get(base_url)
            WebDriverWait(self.driver, TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            h2_tag = soup.find("h2", string="Illustrations and Manga")
            if h2_tag and (span_tag := h2_tag.find_next("span")) and span_tag.text.isdigit():
                self.target_count = int(span_tag.text)
                logger.info(f"User found. Total artworks available: {self.target_count}")
                self.artwork_label.config(text=f"Artworks: {self.target_count}")
            else:
                logger.error("Invalid User ID or no artworks found.")
                return

            artworks_url = f"https://www.pixiv.net/en/users/{self.user_id}/artworks"
            self.driver.get(artworks_url)
            WebDriverWait(self.driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/artworks/')]")))
            logger.info("Checking for pages... Please wait.")
            self.total_pages = self.get_total_pages()
            logger.info(f"Found {self.total_pages} pages of artworks.")
            self.page_label.config(text=f"of {self.total_pages} pages")
            self.page_combo.config(state="normal")
            self.page_combo["values"] = [str(i) for i in range(1, self.total_pages + 1)]
            self.page_combo.set("1")
            self.fetch_complete = True
        except (TimeoutException, WebDriverException, InvalidSessionIdException) as e:
            logger.error(f"Search interrupted: {str(e)}")
            error_occurred = True
            self.fetch_complete = False
        except Exception as e:
            logger.error(f"Unexpected error fetching artwork count or pages: {str(e)}")
            error_occurred = True
            self.fetch_complete = False
        finally:
            if self.driver and self.is_session_valid(self.driver):
                if error_occurred or self.is_headless:
                    self.driver.quit()
                    self.driver = None
            self.search_button.config(state="normal")
            self.download_url_button.config(state="normal")
            if self.fetch_complete:
                self.download_button.config(state="normal")
                self.download_page_button.config(state="normal")

    def get_total_pages(self):
        page_num = 1
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            try:
                WebDriverWait(self.driver, TIMEOUT).until(
                    EC.presence_of_element_located((By.XPATH, "//nav[contains(@class, 'sc-xhhh7v-0')]"))
                )
                broad_xpath = (
                    "//a[.//svg[@viewBox='0 0 10 8' and @width='16' and @height='16']] | "
                    "//a[contains(@href, '?p=" + str(page_num + 1) + "')]"
                )
                candidates = self.driver.find_elements(By.XPATH, broad_xpath)
                if not candidates:
                    break

                next_button = None
                for cand in candidates:
                    href = cand.get_attribute("href")
                    if href and f"?p={page_num + 1}" in href:
                        next_button = cand
                        break

                if not next_button:
                    break

                self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                time.sleep(1)
                current_url = self.driver.current_url
                next_button.click()
                WebDriverWait(self.driver, TIMEOUT).until(lambda d: d.current_url != current_url)
                page_num += 1
            except (TimeoutException, WebDriverException):
                break
        return page_num

    def start_download(self):
        self.stop_download = False
        self.download_button.config(state="disabled")
        self.download_page_button.config(state="disabled")
        self.download_url_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.search_button.config(state="disabled")
        self.verify_cookies_button.config(state="disabled")
        self.progress_bar["value"] = 0
        self.save_folder = os.path.join(save_folder_base, f"pixiv_{self.user_id}_images")
        os.makedirs(self.save_folder, exist_ok=True)
        self.driver = self.restart_driver(self.driver, force_headless=None)
        if not self.driver:
            logger.error("Download aborted: Could not initialize browser.")
            self.reset_ui()
            return
        threading.Thread(target=self.download_all, daemon=True).start()

    def start_download_page(self):
        page_str = self.page_combo.get()
        self.stop_download = False
        self.download_button.config(state="disabled")
        self.download_page_button.config(state="disabled")
        self.download_url_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.search_button.config(state="disabled")
        self.verify_cookies_button.config(state="disabled")
        self.progress_bar["value"] = 0
        self.save_folder = os.path.join(save_folder_base, f"pixiv_{self.user_id}_images")
        os.makedirs(self.save_folder, exist_ok=True)
        self.driver = self.restart_driver(self.driver, force_headless=None)
        if not self.driver:
            logger.error("Download aborted: Could not initialize browser.")
            self.reset_ui()
            return
        threading.Thread(target=self.download_page, args=(int(page_str),), daemon=True).start()

    def start_download_url(self):
        artwork_url = self.url_entry.get().strip()
        if not artwork_url or not re.match(r"https://www\.pixiv.net/en/artworks/\d+", artwork_url):
            logger.error("Invalid or empty artwork URL. Please enter a valid Pixiv artwork URL (e.g., https://www.pixiv.net/en/artworks/12345678).")
            self.download_url_button.config(state="normal")
            return

        self.stop_download = False
        self.download_button.config(state="disabled")
        self.download_page_button.config(state="disabled")
        self.download_url_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.search_button.config(state="disabled")
        self.verify_cookies_button.config(state="disabled")
        self.progress_bar["value"] = 0
        artwork_id = artwork_url.split('/')[-1]
        self.save_folder = os.path.join(save_folder_base, f"pixiv_artwork_{artwork_id}_images")
        os.makedirs(self.save_folder, exist_ok=True)
        self.driver = self.restart_driver(self.driver, force_headless=not self.show_browser_var.get())
        if not self.driver:
            logger.error("Download aborted: Could not initialize browser.")
            self.reset_ui()
            return
        
        self.driver.get(artwork_url)
        threading.Thread(target=self.download_url, args=(artwork_url,), daemon=True).start()

    def stop_download_process(self):
        self.stop_download = True
        self.root.after(1000, self.reset_ui)

    def reset_ui(self):
        self.download_button.config(state="normal" if self.fetch_complete else "disabled")
        self.download_page_button.config(state="normal" if self.fetch_complete else "disabled")
        self.download_url_button.config(state="normal" if self.cookies_valid else "disabled")
        self.stop_button.config(state="disabled")
        self.search_button.config(state="normal")
        self.verify_cookies_button.config(state="normal" if self.cookies_valid else "disabled")
        self.progress_bar["value"] = 0

    def download_all(self):
        self.start_time = time.time()
        self.processed_count = 0
        self.downloaded_count = 0
        self.skipped_count = 0
        if not self.driver or not self.is_session_valid(self.driver):
            logger.error("Browser session invalid or closed. Aborting download.")
            self.root.after(0, self.reset_ui)
            return
        session_valid = [True]
        artwork_links_seen = set()
        page_num = 1
        failed_urls = []
        failed_downloads = []

        try:
            artworks_url = f"https://www.pixiv.net/en/users/{self.user_id}/artworks"
            if not self.stop_download and session_valid[0]:
                try:
                    self.driver.get(artworks_url)
                    WebDriverWait(self.driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/artworks/')]")))
                except (TimeoutException, WebDriverException, InvalidSessionIdException):
                    logger.info(f"Stopping process on Page {page_num}: Browser window closed or timed out")
                    session_valid[0] = False
                    self.root.after(0, self.reset_ui)
                    return
                if self.stop_download:
                    logger.info(f"Session interrupted. Stopping process on Page {page_num}.")
                    self.root.after(0, self.reset_ui)
                    return

            while session_valid[0] and not self.stop_download:
                page_url = f"{artworks_url}?p={page_num}"
                if not self.is_session_valid(self.driver):
                    logger.info(f"Stopping process on Page {page_num}: Browser window closed")
                    break
                try:
                    self.driver.get(page_url)
                    WebDriverWait(self.driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/artworks/')]")))
                except (TimeoutException, WebDriverException, InvalidSessionIdException):
                    logger.info(f"Stopping process on Page {page_num}: Browser window closed or timed out")
                    break

                if self.stop_download:
                    break

                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                try:
                    WebDriverWait(self.driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, "//nav[contains(@class, 'sc-xhhh7v-0')]")))
                except (TimeoutException, WebDriverException, InvalidSessionIdException):
                    logger.info(f"Stopping process on Page {page_num}: Browser window closed or timed out")
                    break

                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                page_linked = set()
                for link in soup.find_all("a", href=re.compile(r"/en/artworks/\d+$")):
                    full_url = "https://www.pixiv.net" + link["href"]
                    if full_url not in artwork_links_seen:
                        page_linked.add(full_url)
                        artwork_links_seen.add(full_url)
                logger.info(f"Page {page_num}: Found {len(page_linked)} new artworks (Total so far: {len(artwork_links_seen)})")

                page_progress = 0
                page_start_time = time.time()
                processed_urls = set()
                for artwork_url in page_linked:
                    if not session_valid[0] or self.stop_download:
                        for remaining_url in page_linked - processed_urls:
                            failed_urls.append((remaining_url, page_num, "Session interrupted"))
                        break

                    image_urls = self.get_image_urls(artwork_url, self.driver, session_valid)
                    if not image_urls:
                        if not session_valid[0]:
                            failed_urls.append((artwork_url, page_num, "Session interrupted"))
                            for remaining_url in page_linked - processed_urls - {artwork_url}:
                                failed_urls.append((remaining_url, page_num, "Session interrupted"))
                            break
                        failed_urls.append((artwork_url, page_num, "Failed to extract image URLs"))
                        processed_urls.add(artwork_url)
                        continue

                    all_skipped = True
                    for image_url in image_urls:
                        if self.stop_download:
                            break
                        filename = image_url.split("/")[-1]
                        save_path = os.path.join(self.save_folder, filename)
                        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                            logger.info(f"Skipped: {save_path} already exists")
                            continue

                        all_skipped = False
                        for attempt in range(5):
                            if self.stop_download:
                                break
                            try:
                                image_data = self.session.get(image_url, headers=headers, timeout=10).content
                                with open(save_path, "wb") as file:
                                    file.write(image_data)
                                logger.info(f"Downloaded: {save_path}")
                                break
                            except Exception as e:
                                if attempt == 4:
                                    failed_downloads.append((image_url, artwork_url, page_num, str(e)))
                                time.sleep(random.uniform(1, 3))

                    if self.stop_download:
                        for remaining_url in page_linked - processed_urls:
                            failed_urls.append((remaining_url, page_num, "Session interrupted"))
                        break

                    self.processed_count += 1
                    processed_urls.add(artwork_url)
                    if all_skipped:
                        self.skipped_count += 1
                    else:
                        self.downloaded_count += 1

                    page_progress += 1
                    elapsed = time.time() - page_start_time
                    elapsed_str = f"{int(elapsed // 60):02d}:{int(elapsed % 60):02d}"
                    percent = int((page_progress / len(page_linked)) * 100)
                    speed = elapsed / page_progress if page_progress > 0 else 0
                    logger.info(f"Downloading Page {page_num}: {percent}% {page_progress}/{len(page_linked)} [{elapsed_str}, {speed:.2f}s/artwork]")
                    logger.info(f"Processed artworks: {self.processed_count}/{self.target_count}")
                    self.progress_bar["value"] = (self.processed_count / self.target_count) * 100
                    self.root.update_idletasks()

                if not session_valid[0] or self.stop_download:
                    break

                logger.info(f"Returning to artworks list: {page_url}")
                if not self.is_session_valid(self.driver):
                    logger.info(f"Stopping process on Page {page_num}: Browser window closed")
                    break
                try:
                    self.driver.get(page_url)
                    WebDriverWait(self.driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/artworks/')]")))
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    WebDriverWait(self.driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, "//nav[contains(@class, 'sc-xhhh7v-0')]")))
                except (TimeoutException, WebDriverException, InvalidSessionIdException):
                    logger.info(f"Stopping process on Page {page_num}: Browser window closed or timed out")
                    break

                next_found = False
                for attempt in range(3):
                    if self.stop_download:
                        break
                    try:
                        broad_xpath = (
                            "//a[.//svg[@viewBox='0 0 10 8' and @width='16' and @height='16']] | "
                            "//a[contains(@href, '?p=" + str(page_num + 1) + "')]"
                        )
                        candidates = self.driver.find_elements(By.XPATH, broad_xpath)
                        if not candidates:
                            raise TimeoutException("No candidates found")

                        next_button = None
                        for cand in candidates:
                            href = cand.get_attribute("href")
                            if href and f"?p={page_num + 1}" in href:
                                next_button = cand
                                break

                        if not next_button:
                            raise TimeoutException("No suitable 'Next' button found")

                        self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                        time.sleep(1)
                        current_url = self.driver.current_url
                        next_button.click()
                        WebDriverWait(self.driver, TIMEOUT).until(lambda d: d.current_url != current_url)
                        page_num += 1
                        next_found = True
                        logger.info(f"Found 'Next' button on Page {page_num - 1}, proceeding.")
                        time.sleep(random.uniform(2, 4))
                        break
                    except (TimeoutException, WebDriverException, InvalidSessionIdException):
                        if attempt == 2:
                            logger.info(f"No 'Next' button found on Page {page_num}. End of pagination.")
                            next_found = False
                        time.sleep(random.uniform(1, 3))

                if not next_found:
                    break

        except Exception as e:
            logger.error(f"Unexpected error in download_all: {str(e)}")
        finally:
            if failed_urls:
                logger.info("Failed artworks:")
                for url, page, error in failed_urls:
                    logger.info(f"  {url} (Page {page}): {error}")
            if failed_downloads:
                logger.info("Failed downloads:")
                for image_url, artwork_url, page, error in failed_downloads:
                    logger.info(f"  {image_url} from {artwork_url} (Page {page}): {error}")
            self.print_summary(self.processed_count, self.target_count, self.downloaded_count, self.skipped_count, self.start_time)
            if self.driver and self.is_session_valid(self.driver):
                try:
                    self.driver.quit()
                except Exception:
                    pass
            self.driver = None
            self.root.after(0, self.reset_ui)

    def download_page(self, page_num):
        self.start_time = time.time()
        self.processed_count = 0
        self.downloaded_count = 0
        self.skipped_count = 0
        if not self.driver or not self.is_session_valid(self.driver):
            logger.error("Browser session invalid or closed. Aborting download.")
            self.root.after(0, self.reset_ui)
            return
        session_valid = [True]
        artwork_links_seen = set()
        failed_urls = []
        failed_downloads = []

        try:
            artworks_url = f"https://www.pixiv.net/en/users/{self.user_id}/artworks?p={page_num}"
            if not self.stop_download and session_valid[0]:
                try:
                    self.driver.get(artworks_url)
                    WebDriverWait(self.driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/artworks/')]")))
                except (TimeoutException, WebDriverException, InvalidSessionIdException):
                    logger.info(f"Stopping process on Page {page_num}: Browser window closed or timed out")
                    session_valid[0] = False
                    self.root.after(0, self.reset_ui)
                    return
                if self.stop_download:
                    logger.info(f"Session interrupted. Stopping process on Page {page_num}.")
                    self.root.after(0, self.reset_ui)
                    return

            if self.stop_download:
                logger.info(f"Session interrupted. Stopping process on Page {page_num}.")
                return

            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            try:
                WebDriverWait(self.driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, "//nav[contains(@class, 'sc-xhhh7v-0')]")))
            except (TimeoutException, WebDriverException, InvalidSessionIdException):
                logger.info(f"Stopping process on Page {page_num}: Browser window closed or timed out")
                return

            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            page_linked = set()
            for link in soup.find_all("a", href=re.compile(r"/en/artworks/\d+$")):
                full_url = "https://www.pixiv.net" + link["href"]
                if full_url not in artwork_links_seen:
                    page_linked.add(full_url)
                    artwork_links_seen.add(full_url)
            logger.info(f"Page {page_num}: Found {len(page_linked)} new artworks (Total so far: {len(artwork_links_seen)})")

            page_progress = 0
            page_start_time = time.time()
            processed_urls = set()
            for artwork_url in page_linked:
                if not session_valid[0] or self.stop_download:
                    for remaining_url in page_linked - processed_urls:
                        failed_urls.append((remaining_url, page_num, "Session interrupted"))
                    break

                image_urls = self.get_image_urls(artwork_url, self.driver, session_valid)
                if not image_urls:
                    if not session_valid[0]:
                        failed_urls.append((artwork_url, page_num, "Session interrupted"))
                        for remaining_url in page_linked - processed_urls - {artwork_url}:
                            failed_urls.append((remaining_url, page_num, "Session interrupted"))
                        break
                    failed_urls.append((artwork_url, page_num, "Failed to extract image URLs"))
                    processed_urls.add(artwork_url)
                    continue

                all_skipped = True
                for image_url in image_urls:
                    if self.stop_download:
                        break
                    filename = image_url.split("/")[-1]
                    save_path = os.path.join(self.save_folder, filename)
                    if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                        logger.info(f"Skipped: {save_path} already exists")
                        continue

                    all_skipped = False
                    for attempt in range(5):
                        if self.stop_download:
                            break
                        try:
                            image_data = self.session.get(image_url, headers=headers, timeout=10).content
                            with open(save_path, "wb") as file:
                                file.write(image_data)
                            logger.info(f"Downloaded: {save_path}")
                            break
                        except Exception as e:
                            if attempt == 4:
                                failed_downloads.append((image_url, artwork_url, page_num, str(e)))
                            time.sleep(random.uniform(1, 3))

                if self.stop_download:
                    for remaining_url in page_linked - processed_urls:
                        failed_urls.append((remaining_url, page_num, "Session interrupted"))
                    break

                self.processed_count += 1
                processed_urls.add(artwork_url)
                if all_skipped:
                    self.skipped_count += 1
                else:
                    self.downloaded_count += 1

                page_progress += 1
                elapsed = time.time() - page_start_time
                elapsed_str = f"{int(elapsed // 60):02d}:{int(elapsed % 60):02d}"
                percent = int((page_progress / len(page_linked)) * 100)
                speed = elapsed / page_progress if page_progress > 0 else 0
                logger.info(f"Downloading Page {page_num}: {percent}% {page_progress}/{len(page_linked)} [{elapsed_str}, {speed:.2f}s/artwork]")
                self.progress_bar["value"] = (self.processed_count / len(page_linked)) * 100
                self.root.update_idletasks()

        except Exception as e:
            logger.error(f"Unexpected error in download_page: {str(e)}")
        finally:
            if failed_urls:
                logger.info("Failed artworks:")
                for url, page, error in failed_urls:
                    logger.info(f"  {url} (Page {page}): {error}")
            if failed_downloads:
                logger.info("Failed downloads:")
                for image_url, artwork_url, page, error in failed_downloads:
                    logger.info(f"  {image_url} from {artwork_url} (Page {page}): {error}")
            self.print_summary(self.processed_count, len(page_linked) if 'page_linked' in locals() else 0, self.downloaded_count, self.skipped_count, self.start_time)
            if self.driver and self.is_session_valid(self.driver):
                try:
                    self.driver.quit()
                except Exception:
                    pass
            self.driver = None
            self.root.after(0, self.reset_ui)

    def download_url(self, artwork_url):
        self.start_time = time.time()
        self.processed_count = 0
        self.downloaded_count = 0
        self.skipped_count = 0
        if not self.driver or not self.is_session_valid(self.driver):
            logger.error("Browser session invalid or closed. Aborting download.")
            self.root.after(0, self.reset_ui)
            return
        session_valid = [True]
        failed_urls = []
        failed_downloads = []

        try:
            logger.info(f"Processing artwork URL: {artwork_url}")
            if not self.stop_download and session_valid[0]:
                image_urls = self.get_image_urls(artwork_url, self.driver, session_valid)
                if not image_urls:
                    if not session_valid[0]:
                        failed_urls.append((artwork_url, 1, "Session interrupted"))
                        logger.info("Session interrupted. Stopping process.")
                    else:
                        failed_urls.append((artwork_url, 1, "Failed to extract image URLs"))
                    return

                all_skipped = True
                for image_url in image_urls:
                    if self.stop_download:
                        break
                    filename = image_url.split("/")[-1]
                    save_path = os.path.join(self.save_folder, filename)
                    if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                        logger.info(f"Skipped: {save_path} already exists")
                        continue

                    all_skipped = False
                    for attempt in range(5):
                        if self.stop_download:
                            break
                        try:
                            image_data = self.session.get(image_url, headers=headers, timeout=10).content
                            with open(save_path, "wb") as file:
                                file.write(image_data)
                            logger.info(f"Downloaded: {save_path}")
                            break
                        except Exception as e:
                            if attempt == 4:
                                failed_downloads.append((image_url, artwork_url, 1, str(e)))
                            time.sleep(random.uniform(1, 3))

                if self.stop_download:
                    failed_urls.append((artwork_url, 1, "Session interrupted"))
                    logger.info("Session interrupted. Stopping process.")
                    return

                self.processed_count += 1
                if all_skipped:
                    self.skipped_count += 1
                else:
                    self.downloaded_count += 1

                elapsed = time.time() - self.start_time
                elapsed_str = f"{int(elapsed // 60):02d}:{int(elapsed % 60):02d}"
                logger.info(f"Processed artwork: 100% 1/1 [{elapsed_str}]")
                self.progress_bar["value"] = 100
                self.root.update_idletasks()

        except (TimeoutException, WebDriverException, InvalidSessionIdException) as e:
            logger.info(f"Stopping process for {artwork_url}: {str(e)}")
            session_valid[0] = False
        except Exception as e:
            logger.error(f"Unexpected error in download_url: {str(e)}")
            logger.info("Session interrupted. Stopping process.")
        finally:
            if failed_urls:
                logger.info("Failed artworks:")
                for url, page, error in failed_urls:
                    logger.info(f"  {url}: {error}")
            if failed_downloads:
                logger.info("Failed downloads:")
                for image_url, artwork_url, page, error in failed_downloads:
                    logger.info(f"  {image_url} from {artwork_url}: {error}")
            self.print_summary(self.processed_count, 1, self.downloaded_count, self.skipped_count, self.start_time)
            if self.driver and self.is_session_valid(self.driver):
                try:
                    self.driver.quit()
                except Exception:
                    pass
            self.driver = None
            self.root.after(0, self.reset_ui)

    def restart_driver(self, existing_driver=None, force_headless=None):
        # If force_headless is None, respect the show_browser_var toggle
        if force_headless is None:
            desired_headless = not self.show_browser_var.get()
        else:
            # If force_headless is explicitly set, it takes precedence
            desired_headless = force_headless
        
        if existing_driver and self.is_session_valid(existing_driver):
            if self.is_headless == desired_headless:
                return existing_driver
            else:
                try:
                    existing_driver.quit()
                except Exception:
                    pass
        
        options = webdriver.ChromeOptions()
        options.add_argument('--log-level=3')
        self.is_headless = desired_headless
        if self.is_headless:
            options.add_argument('--headless=new')
        
        try:
            with redirect_stdout(StringIO()):
                new_driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            new_driver.get("https://www.pixiv.net")
            for cookie in self.cookies:
                try:
                    new_driver.add_cookie(cookie)
                except Exception:
                    logger.error("Browser window closed during cookie setup.")
                    new_driver.quit()
                    return None
            return new_driver
        except Exception as e:
            logger.exception(f"Unexpected error initializing ChromeDriver: {e}")
            return None

    def is_session_valid(self, driver):
        try:
            driver.current_url
            return True
        except (InvalidSessionIdException, NoSuchWindowException):
            return False

    def get_image_urls(self, artwork_url, driver, session_valid_ref):
        for attempt in range(3):
            if self.stop_download or not self.is_session_valid(driver):
                logger.info(f"Stopping process for {artwork_url}: Session interrupted (window closed or stopped)")
                session_valid_ref[0] = False
                return []

            try:
                driver.get(artwork_url)
                WebDriverWait(driver, TIMEOUT).until(
                    lambda d: d.find_elements(By.CSS_SELECTOR, "div[aria-label='Preview']") or 
                            d.find_elements(By.TAG_NAME, "img")
                )
                time.sleep(2)
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, "html.parser")

                page_count = 1
                if preview_div := soup.find("div", {"aria-label": "Preview"}):
                    spans = preview_div.find_all("span")
                    for span in spans:
                        if "/" in span.text:
                            page_count = int(span.text.split("/")[1])
                            logger.info(f"Detected {page_count} pages from Preview div for {artwork_url}")
                            break
                    else:
                        logger.info(f"No page count found in Preview div spans for {artwork_url}")

                if img_match := re.search(r"https://i\.pximg\.net/img-original/img/\d{4}/\d{2}/\d{2}/\d{2}/\d{2}/\d{2}/(\d+_p\d+\.(png|jpg|jpeg|gif))", page_source):
                    base_url = img_match.group(0).rsplit("_p", 1)[0]
                    ext = img_match.group(2).split(".")[-1]
                else:
                    illust_id = artwork_url.split("/")[-1]
                    if meta_tag := soup.find("meta", property="og:image"):
                        if "i.pximg.net" in meta_tag["content"]:
                            if date_match := re.search(r"img/(\d{4}/\d{2}/\d{2}/\d{2}/\d{2}/\d{2})", meta_tag["content"]):
                                date_path = date_match.group(1)
                                base_url = f"https://i.pximg.net/img-original/img/{date_path}/{illust_id}"
                                ext = "png"
                            else:
                                logger.error(f"No date path found in og:image for {artwork_url}")
                                return []
                        else:
                            logger.debug(f"og:image found but no usable pximg.net URL for {artwork_url}")
                            return []
                    else:
                        logger.error(f"No valid image URL pattern found for {artwork_url}")
                        return []

                image_urls = [f"{base_url}_p{i}.{ext}" for i in range(page_count)]
                logger.info(f"Generated {len(image_urls)} image URLs for {artwork_url}")
                return image_urls

            except (TimeoutException, WebDriverException, InvalidSessionIdException) as e:
                if isinstance(e, InvalidSessionIdException) or isinstance(e, NoSuchWindowException):
                    logger.info(f"Stopping process for {artwork_url}: Browser window closed")
                    session_valid_ref[0] = False
                    return []
                if attempt < 2:
                    logger.info(f"Retrying {artwork_url} (attempt {attempt + 2}/3): {str(e)}")
                    time.sleep(random.uniform(2, 4))
                    continue
                logger.error(f"Failed to get URLs for {artwork_url} after 3 attempts: {str(e)}")
                return []
            except Exception as e:
                logger.error(f"Unexpected error for {artwork_url}: {str(e)}")
                session_valid_ref[0] = False
                return []

    def print_summary(self, processed_count, target_count, downloaded_count, skipped_count, start_time):
        total_time = time.time() - start_time
        time_str = f"{int(total_time // 60):02d}:{int(total_time % 60):02d}"
        logger.info(f"Total artworks processed: {processed_count}/{target_count} ({downloaded_count} downloaded, {skipped_count} skipped) in {time_str}")

    def on_closing(self):
        self.stop_download = True
        time.sleep(1)

        try:
            self.session.close()
        except Exception as e:
            logger.error(f"Error closing requests session: {e}")

        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None

        self.root.after(500, self.final_exit)

    def final_exit(self):
        logger.info("Gracefully exiting.")
        logger.info("")
        if self.log_handler in logger.handlers:
            logger.removeHandler(self.log_handler)
        self.root.destroy()

class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        try:
            msg = self.format(record)
            self.text_widget.config(state="normal")
            self.text_widget.insert(tk.END, msg + "\n")
            self.text_widget.see(tk.END)
            self.text_widget.config(state="disabled")
        except tk.TclError:
            pass

if __name__ == "__main__":
    root = tk.Tk()
    app = PixivDownloaderApp(root)
    root.mainloop()