# --- Nuitka Build Configuration (Hints) ---
# nuitka-project: --standalone
# nuitka-project: --deployment
# nuitka-project: --msvc=latest
# nuitka-project: --windows-console-mode=disable
# nuitka-project: --enable-plugin=tk-inter
# nuitka-project: --include-package=pypresence
# nuitka-project: --include-package=requests
# nuitka-project: --include-package=psutil
# nuitka-project: --include-package=packaging
# nuitka-project: --include-package=flask
# nuitka-project: --include-package=werkzeug
# nuitka-project: --company-name="Seeyaflying"
# nuitka-project: --product-name="Qobuz-RPC"
# nuitka-project: --file-description="Discord Rich Presence for Qobuz"
# nuitka-project: --file-version=1.0.1
# nuitka-project: --output-dir=dist
# nuitka-project: --remove-output
# -------------------------------------------

import tkinter as tk
from tkinter import messagebox
import threading
import time
import os
import requests
from packaging.version import parse as parse_version
from flask import Flask, request, jsonify

# --- External Windows and RPC Libraries ---
try:
    from pypresence import Presence
    import psutil
    import ctypes
    import win32gui
    import win32process

    RPC_AVAILABLE = True
    GetWindowText = ctypes.windll.user32.GetWindowTextW
    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible
except (ImportError, AttributeError):
    RPC_AVAILABLE = False
    print("Warning: Missing required libraries. RPC functionality disabled.")


    class Presence:
        def __init__(self, client_id): pass

        def connect(self): pass

        def update(self, **kwargs): pass

        def clear(self): pass

        def close(self): pass


    win32gui = None;
    win32process = None;
    psutil = None;
    ctypes = None

# --- Configuration ---
LOCAL_VERSION = "1.0.1"
VERSION_URL = "https://raw.githubusercontent.com/Seeyaflying/Qobuz-RPC/main/latest_version.txt"
DOWNLOAD_URL = "https://github.com/Seeyaflying/Qobuz-RPC/releases/latest"
CLIENT_ID = "928957672907227147"
QOBUZ_PROCESS_NAME = "Qobuz.exe"


def fetch_latest_version(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.text.strip()
        except requests.exceptions.RequestException:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    return None


def check_for_updates_logic(local_version, version_url, download_url):
    remote_version_str = fetch_latest_version(version_url)
    if not remote_version_str:
        return {"status": "error", "message": "Update check failed (Network Error)."}
    try:
        if parse_version(remote_version_str) > parse_version(local_version):
            message = (f"🚨 UPDATE AVAILABLE! 🚨\n\nYour version: v{local_version}\n"
                       f"Latest version: v{remote_version_str}\n\n"
                       f"Please download from:\n{download_url}")
            return {"status": "update", "message": message, "remote_version": remote_version_str}
        return {"status": "ok", "message": f"Running latest version (v{local_version})."}
    except Exception:
        return {"status": "error", "message": "Update check failed (Parsing Error)."}


class RPCSynchronizer(threading.Thread):
    def __init__(self, app_instance, client_id):
        super().__init__()
        self.app = app_instance
        self.client_id = client_id
        self._stop_event = threading.Event()
        self.rpc = None
        self.art_cache = {}

    def force_update_presence(self, title):
        def _update_task():
            try:
                if not self.rpc:
                    print("RPC not connected, cannot update presence.")
                    return
                if not title:
                    self.rpc.clear()
                    self.app.update_status("Qobuz: Cleared by remote")
                    return

                song_title, artist_name = (title.rsplit(' - ', 1) + ["Unknown Artist"])[:2]
                self.app.update_status(f"Qobuz: Searching for art for '{song_title}'...")
                art_url, _ = self.fetch_album_art_and_duration(song_title.strip(), artist_name.strip())

                self.rpc.update(
                    details=song_title,
                    state=f"by {artist_name}",
                    large_image=art_url or "qobuz",
                    large_text=f"{song_title} - {artist_name}",
                    small_image="qobuz_icon",
                    small_text="Qobuz Player"
                )
                self.app.update_status(f"Qobuz: Updated to '{song_title}'")
            except Exception as e:
                print(f"Force update failed: {e}")
                self.app.update_status(f"Qobuz: Update failed", color=self.app.color_status_fail)

        self.app.master.after(0, _update_task)

    def fetch_album_art_and_duration(self, song_title, artist_name):
        search_term = f"{song_title} {artist_name}"
        url = f"https://itunes.apple.com/search?term={search_term}&entity=song&limit=1"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            if data.get('resultCount', 0) > 0 and data['results']:
                result = data['results'][0]
                art_url = result.get('artworkUrl100', '').replace('100x100bb', '512x512bb')
                duration_ms = result.get('trackTimeMillis')
                return art_url, duration_ms
        except Exception as e:
            print(f"Failed to fetch art/duration from iTunes: {e}")
        return None, None

    def stop(self):
        self._stop_event.set()
        if self.rpc:
            try:
                self.rpc.clear()
                self.rpc.close()
            except Exception as e:
                print(f"Error closing RPC: {e}")
        self.app.update_status("Stopped")

    def get_qobuz_handle(self):
        try:
            for proc in psutil.process_iter(['name', 'pid']):
                if proc.info['name'] == QOBUZ_PROCESS_NAME:
                    def callback(hwnd, hwnds):
                        if win32process.GetWindowThreadProcessId(hwnd)[1] == proc.info['pid'] and IsWindowVisible(hwnd):
                            hwnds.append(hwnd)
                        return True

                    hwnds = []
                    win32gui.EnumWindows(callback, hwnds)
                    if hwnds: return hwnds[0]
        except Exception:
            return None

    def get_window_title_by_handle(self, hwnd):
        try:
            length = GetWindowTextLength(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            GetWindowText(hwnd, buff, length + 1)
            return buff.value
        except Exception:
            return None

    def run(self):
        if not RPC_AVAILABLE:
            self.app.update_status("Error: Missing Libraries", color=self.app.color_status_fail)
            return
        try:
            self.app.update_status("Connecting to Discord...")
            self.rpc = Presence(self.client_id)
            self.rpc.connect()
            self.app.update_status("Connected. Waiting for Qobuz...")
        except Exception as e:
            self.app.update_status("Connection Failed", color=self.app.color_status_fail)
            messagebox.showerror("RPC Error", f"Failed to connect to Discord: {e}. Is Discord running?")
            return

        last_title = ""
        while not self._stop_event.is_set():
            qobuz_handle = self.get_qobuz_handle()
            if qobuz_handle:
                current_title = self.get_window_title_by_handle(qobuz_handle)
                if current_title and current_title != last_title:
                    last_title = current_title
                    self.force_update_presence(last_title)
            elif last_title != "":
                last_title = ""
                self.force_update_presence(None)
            time.sleep(2)


class QobuzRPCApp:
    def __init__(self, master):
        self.master = master
        master.title(f"Qobuz Discord RPC Synchronizer (v{LOCAL_VERSION})")
        master.geometry("550x450")
        master.resizable(False, False)
        master.configure(bg='#36393F')
        master.protocol("WM_DELETE_WINDOW", self.on_close)

        self.rpc_thread = None
        self.server_thread = None
        self.running = False

        # --- Your Original Styles ---
        self.font_main = ('Inter', 12)
        self.font_status = ('Inter', 14, 'bold')
        self.color_text = '#FFFFFF'
        self.color_status_ok = '#43B581'
        self.color_status_fail = '#F04747'
        self.color_button_start = '#7289DA'
        self.color_button_stop = '#F04747'

        self.main_frame = tk.Frame(master, bg=master['bg'], padx=20, pady=20)
        self.main_frame.pack(fill='both', expand=True)
        self.main_frame.grid_columnconfigure(0, weight=1)

        row_idx = 0
        tk.Label(self.main_frame, text="Qobuz Discord Rich Presence", bg=master['bg'], fg=self.color_text,
                 font=('Inter', 18, 'bold')).grid(row=row_idx, column=0, pady=(0, 5), sticky='ew')

        row_idx += 1
        tk.Label(self.main_frame, text="Click Start RPC to track Qobuz on Discord.", bg=master['bg'], fg='#C0C4CC',
                 font=('Inter', 12)).grid(row=row_idx, column=0, pady=(0, 20), sticky='ew')

        row_idx += 1
        tk.Label(self.main_frame, text="Discord Requirement:", bg=master['bg'], fg=self.color_text,
                 font=self.font_main).grid(row=row_idx, column=0, pady=(5, 0), sticky='ew')

        row_idx += 1
        tk.Label(self.main_frame,
                 text="Must enable 'Display current activity as a status message' in Discord's User Settings > Activity Privacy.",
                 bg=master['bg'], fg='#C0C4CC', font=('Inter', 9), wraplength=500, justify=tk.CENTER).grid(row=row_idx,
                                                                                                           column=0,
                                                                                                           sticky='ew')

        row_idx += 1
        tk.Label(self.main_frame, text="Current Status:", bg=master['bg'], fg=self.color_text,
                 font=self.font_main).grid(row=row_idx, column=0, pady=(20, 5), sticky='ew')

        row_idx += 1
        self.status_var = tk.StringVar(value="Ready to Start")
        self.status_label = tk.Label(self.main_frame, textvariable=self.status_var, bg=master['bg'],
                                     fg=self.color_status_ok, font=self.font_status)
        self.status_label.grid(row=row_idx, column=0, sticky='ew')

        row_idx += 1
        self.button_frame = tk.Frame(self.main_frame, bg=master['bg'], pady=20)
        self.button_frame.grid(row=row_idx, column=0, sticky='s')

        row_idx += 1
        self.start_button = tk.Button(self.button_frame, text="Start RPC", command=self.start_rpc, width=15, height=2,
                                      bg=self.color_button_start, fg=self.color_text, font=self.font_main,
                                      relief='flat', activebackground=self.color_button_start,
                                      activeforeground=self.color_text, cursor="hand2")
        self.start_button.pack(side=tk.LEFT, padx=15)

        self.stop_button = tk.Button(self.button_frame, text="Stop RPC", command=self.stop_rpc, width=15, height=2,
                                     bg=self.color_button_stop, fg=self.color_text, font=self.font_main, relief='flat',
                                     activebackground=self.color_button_stop, activeforeground=self.color_text,
                                     state=tk.DISABLED, cursor="hand2")
        self.stop_button.pack(side=tk.LEFT, padx=15)

        version_frame = tk.Frame(self.main_frame, bg=master['bg'], pady=5)
        version_frame.grid(row=row_idx, column=0, sticky='ew')

        row_idx += 1
        tk.Label(version_frame, text=f"Local Version: {LOCAL_VERSION}", bg=master['bg'], fg='#C0C4CC',
                 font=('Inter', 10)).pack(pady=(0, 5))
        tk.Button(version_frame, text="Check for Updates", command=self.check_for_updates, width=25, height=1,
                  bg='#5865F2', fg=self.color_text, font=('Inter', 11), relief='flat', activebackground='#5865F2',
                  activeforeground=self.color_text, cursor="hand2").pack()

        self._start_initial_update_check()

    def run_server(self):
        flask_app = Flask(__name__)

        @flask_app.route('/update', methods=['POST'])
        def update_presence_route():
            if self.running and self.rpc_thread:
                data = request.get_json()
                song_title = data.get('title') if data else None
                if song_title is not None:
                    self.rpc_thread.force_update_presence(song_title)
                    return jsonify({"status": "ok"}), 200
            return jsonify({"status": "error", "message": "RPC is not running"}), 503

        @flask_app.route('/shutdown', methods=['POST'])
        def shutdown():
            os._exit(0)
            return 'Server shutting down...'

        flask_app.run(host='127.0.0.1', port=5000, debug=False)

    def start_rpc(self):
        if self.running: return
        self.running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.update_status("RPC and Server Running...")
        self.rpc_thread = RPCSynchronizer(self, CLIENT_ID)
        self.rpc_thread.daemon = True
        self.rpc_thread.start()
        self.server_thread = threading.Thread(target=self.run_server, daemon=True)
        self.server_thread.start()

    def stop_rpc(self):
        if not self.running: return
        self.running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        if self.rpc_thread: self.rpc_thread.stop()
        self.update_status("Stopped", color=self.color_text)

    def on_close(self):
        if self.running: self.stop_rpc()
        self.master.destroy()

    def update_status(self, message, color=None):
        self.status_var.set(message)
        if color:
            self.status_label.config(fg=color)
        elif any(word in message for word in ["Error", "Failed", "Update"]):
            self.status_label.config(fg=self.color_status_fail)
        elif any(word in message for word in ["Playing", "Connected", "latest", "Updated"]):
            self.status_label.config(fg=self.color_status_ok)
        else:
            self.status_label.config(fg=self.color_text)

    def _start_initial_update_check(self):
        threading.Thread(target=self._check_for_updates_async, daemon=True).start()

    def check_for_updates(self):
        threading.Thread(target=self._check_for_updates_async, daemon=True).start()

    def _check_for_updates_async(self):
        update_info = check_for_updates_logic(LOCAL_VERSION, VERSION_URL, DOWNLOAD_URL)
        self.master.after(0, lambda: self._handle_update_result_gui(update_info))

    def _handle_update_result_gui(self, update_info):
        message = update_info.get('message')
        if update_info["status"] == "update" and message:
            self.update_status(f"Update available! v{update_info.get('remote_version', '?')}",
                               color=self.color_status_fail)
            messagebox.showinfo("Update Available", message)
        elif update_info["status"] == "ok" and message and "Ready" not in self.status_var.get():
            self.update_status(message, color=self.color_status_ok)


if __name__ == '__main__':
    root = tk.Tk()
    app = QobuzRPCApp(root)
    root.mainloop()