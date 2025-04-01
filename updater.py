import sys
import os
import requests
import tkinter as tk
import logging
import time
import webbrowser
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.FileHandler("output.log", mode='a'), logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger()

class CustomDialog(tk.Toplevel):
    def __init__(self, root, title, message, buttons=None, link=None):
        super().__init__(root)
        self.root = root
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
        x = (self.winfo_screenwidth() - width) // 2
        y = (self.winfo_screenheight() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.update()
        self.lift()
        self.focus_force()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.destroy()
        self.root.destroy()
        sys.exit(0)

def update_app(new_version):
    logger.info("Updater launched.")
    time.sleep(5)
    root = tk.Tk()
    root.withdraw()
    current_exe = os.path.join(os.path.dirname(sys.executable), "get_pixiv.exe")
    github_link = "https://github.com/kakao90g/get_pixiv/releases"

    def proceed():
        logger.info(f"Starting update to v{new_version}.")
        time.sleep(2)
        try:
            new_exe = os.path.join(os.path.dirname(current_exe), "get_pixiv_new.exe")
            exe_url = f"https://github.com/kakao90g/get_pixiv/releases/download/v{new_version}/get_pixiv.exe"
            response = requests.get(exe_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30, stream=True)
            response.raise_for_status()
            with open(new_exe, "wb") as f:
                f.write(response.content)
            if os.path.getsize(new_exe) <= 0:
                raise ValueError("Downloaded file is empty")
            if os.path.exists(current_exe):
                os.remove(current_exe)
            os.rename(new_exe, current_exe)
            logger.info("Download successful, starting get_pixiv.exe.")
            subprocess.Popen(current_exe)
        except Exception as e:
            logger.error(f"Update failed: {str(e)}")
            if os.path.exists(new_exe):
                os.remove(new_exe)
            CustomDialog(root, "Update Error",
                        "Download failed. Get it from:",
                        link=github_link)
        finally:
            root.destroy()
            sys.exit(0)

    def on_no(parent_dialog):
        parent_dialog.destroy()
        CustomDialog(root, "Update",
                    "Please download manually from:",
                    link=github_link)

    proceed_dialog = CustomDialog(root, "Updater",
                                 f"get pixiv will update to v{new_version}. Proceed?",
                                 buttons=[("Yes", proceed), 
                                          ("No", lambda: on_no(proceed_dialog))])
    root.mainloop()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        root = tk.Tk()
        root.withdraw()
        CustomDialog(root, "Updater Error", 
                    "Invalid arguments. Please run via get_pixiv.exe.")
        root.destroy()
        sys.exit(1)
    new_version = sys.argv[1]
    update_app(new_version)