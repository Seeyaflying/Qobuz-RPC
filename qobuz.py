# --- Nuitka Build Configuration (Hints) ---
# nuitka-project: --standalone
# nuitka-project: --msvc=latest
# nuitka-project: --windows-console-mode=disable
# nuitka-project: --enable-plugin=tk-inter
# nuitka-project: --include-package=pypresence
# nuitka-project: --include-package=requests
# nuitka-project: --include-package=psutil
# nuitka-project: --include-package=packaging
# nuitka-project: --company-name="Seeyaflying"
# nuitka-project: --product-name="Qobuz-RPC"
# nuitka-project: --file-description="Discord Rich Presence for Qobuz"
# nuitka-project: --file-version=1.0.0
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

# --- 1. Versioning and Update Configuration ---
LOCAL_VERSION = "1.0.1"
VERSION_URL = "https://raw.githubusercontent.com/Seeyaflying/Qobuz-RPC/main/latest_version.txt"
DOWNLOAD_URL = "https://github.com/Seeyaflying/Qobuz-RPC/releases/latest"
HTTP_HEADERS = {'User-Agent': f'Qobuz-RPC-Sync/{LOCAL_VERSION} (Windows)'}

# --- External Windows and RPC Libraries ---
try:
    from pypresence import Presence
    import psutil
    import ctypes
    import win32gui
    import win32process
except ImportError:
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
else:
    RPC_AVAILABLE = True
    try:
        GetWindowText = ctypes.windll.user32.GetWindowTextW
        GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
        IsWindowVisible = ctypes.windll.user32.IsWindowVisible
    except AttributeError:
        RPC_AVAILABLE = False

CLIENT_ID = "928957672907227147"
QOBUZ_PROCESS_NAME = "Qobuz.exe"


# --- 2. UPDATE LOGIC ---

def fetch_latest_version(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=HTTP_HEADERS, timeout=5)
            response.raise_for_status()
            return response.text.strip()
        except requests.exceptions.RequestException:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    return None


def check_for_updates_logic(local_version, version_url, download_url):
    remote_version_str = fetch_latest_version(version_url)
    if remote_version_str is None:
        return {"status": "error", "message": "Update check failed (Network Error)."}
    try:
        local = parse_version(local_version)
        remote = parse_version(remote_version_str)
        if remote > local:
            message = (f"🚨 UPDATE AVAILABLE! 🚨\n\nYour version: v{local_version}\n"
                       f"Latest version: v{remote_version_str}\n\n"
                       f"Download here:\n{download_url}")
            return {"status": "update", "message": message, "remote_version": remote_version_str}
        return {"status": "ok", "message": f"Running latest version (v{local_version})."}
    except Exception:
        return {"status": "error", "message": "Update check failed (Parsing Error)."}


# --- 3. RPC SYNCHRONIZER THREAD ---

class RPCSynchronizer(threading.Thread):
    def __init__(self, app_instance, client_id):
        super().__init__()
        self.app = app_instance
        self.client_id = client_id
        self._stop_event = threading.Event()
        self.rpc = None
        self.art_cache = {}

    def fetch_album_art_and_duration(self, song_title, artist_name):
        search_term = f"{song_title} {artist_name}"
        url = f"https://itunes.apple.com/search?term={search_term}&entity=song&limit=1"
        try:
            response = requests.get(url, headers=HTTP_HEADERS, timeout=5)
            response.raise_for_status()
            data = response.json()
            if data.get('resultCount', 0) > 0 and data['results']:
                result = data['results'][0]
                art_url = result.get('artworkUrl100', None)
                if art_url:
                    return art_url.replace('100x100bb', '512x512bb'), result.get('trackTimeMillis', None)
        except Exception as e:
            print(f"iTunes API Error: {e}")
        return None, None

    def stop(self):
        self._stop_event.set()
        if self.rpc:
            try:
                self.rpc.clear()
                self.rpc.close()
            except:
                pass
        self.app.update_status("Stopped")

    def get_qobuz_handle(self):
        try:
            qobuz_pids = [proc.info['pid'] for proc in psutil.process_iter(['name', 'pid']) if
                          proc.info['name'] == QOBUZ_PROCESS_NAME]
            if not qobuz_pids: return None

            def get_hwnds_for_pid(pid):
                hwnds = []

                def callback(hwnd, hwnds):
                    try:
                        _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                        if found_pid == pid and IsWindowVisible(hwnd): hwnds.append(hwnd)
                    except:
                        pass
                    return True

                win32gui.EnumWindows(callback, hwnds)
                return hwnds

            for pid in qobuz_pids:
                hwnds = get_hwnds_for_pid(pid)
                if hwnds: return hwnds[0]
            return None
        except:
            return None

    def get_window_title_by_handle(self, hwnd):
        try:
            length = GetWindowTextLength(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            GetWindowText(hwnd, buff, length + 1)
            return buff.value
        except:
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
            messagebox.showerror("RPC Error", f"Discord connection failed. Is it running?")
            return

        last_title = ""
        while not self._stop_event.is_set():
            qobuz_handle = self.get_qobuz_handle()
            if qobuz_handle is None:
                if last_title != "":
                    self.rpc.clear()
                    self.app.update_status("Qobuz Closed. Listening...")
                    last_title = ""
                time.sleep(5);
                continue

            current_title = self.get_window_title_by_handle(qobuz_handle)
            if current_title and current_title != last_title:
                last_title = current_title
                if last_title.strip() == 'Qobuz':
                    self.rpc.clear()
                    self.app.update_status("Qobuz: Idle/Paused")
                else:
                    try:
                        title_parts = last_title.rsplit(' - ', 1)
                        song_title = title_parts[0].strip()
                        artist_name = title_parts[1].strip() if len(title_parts) > 1 else "Unknown Artist"

                        art_url = self.art_cache.get(last_title, (None, None))[0]
                        if not art_url:
                            self.app.update_status(f"Searching art for '{song_title}'...")
                            art_url, dur = self.fetch_album_art_and_duration(song_title, artist_name)
                            if art_url: self.art_cache[last_title] = (art_url, dur)

                        self.rpc.update(
                            details=song_title,
                            state=f"by {artist_name}",
                            large_image=art_url if art_url else "qobuz",
                            large_text=f"{song_title} - {artist_name}",
                            small_image="qobuz_icon",
                            small_text="Qobuz Player"
                        )
                        self.app.update_status(f"Playing: {song_title}")
                    except:
                        pass
            time.sleep(1)


# --- 4. TKINTER GUI ---

class QobuzRPCApp:
    def __init__(self, master):
        self.master = master
        master.title(f"Qobuz RPC (v{LOCAL_VERSION})")
        master.geometry("550x450")
        master.configure(bg='#36393F')
        master.protocol("WM_DELETE_WINDOW", self.on_close)

        self.rpc_thread = None
        self.running = False

        # Colors & Fonts
        self.color_text = '#FFFFFF'
        self.color_status_ok = '#43B581'
        self.color_status_fail = '#F04747'

        # UI Elements
        tk.Label(master, text="Qobuz Discord RPC", bg='#36393F', fg=self.color_text, font=('Inter', 18, 'bold')).pack(
            pady=20)

        self.status_var = tk.StringVar(value="Ready to Start")
        self.status_label = tk.Label(master, textvariable=self.status_var, bg='#36393F', fg=self.color_status_ok,
                                     font=('Inter', 12, 'bold'))
        self.status_label.pack(pady=10)

        self.start_button = tk.Button(master, text="Start RPC", command=self.start_rpc, width=15, bg='#7289DA',
                                      fg=self.color_text)
        self.start_button.pack(pady=5)

        self.stop_button = tk.Button(master, text="Stop RPC", command=self.stop_rpc, width=15, bg='#F04747',
                                     fg=self.color_text, state=tk.DISABLED)
        self.stop_button.pack(pady=5)

        tk.Button(master, text="Check for Updates", command=self.check_for_updates, bg='#40444B',
                  fg=self.color_text).pack(side=tk.BOTTOM, pady=20)

        # Initial check
        threading.Thread(target=self._check_for_updates_async, daemon=True).start()

    def update_status(self, message, color=None):
        self.status_var.set(message)
        if color: self.status_label.config(fg=color)

    def _check_for_updates_async(self):
        info = check_for_updates_logic(LOCAL_VERSION, VERSION_URL, DOWNLOAD_URL)
        self.master.after(0, lambda: messagebox.showinfo("Update", info["message"]) if info[
                                                                                           "status"] == "update" else None)

    def check_for_updates(self):
        threading.Thread(target=self._check_for_updates_async, daemon=True).start()

    def start_rpc(self):
        self.rpc_thread = RPCSynchronizer(self, CLIENT_ID)
        self.rpc_thread.daemon = True
        self.rpc_thread.start()
        self.running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

    def stop_rpc(self):
        if self.rpc_thread: self.rpc_thread.stop()
        self.running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def on_close(self):
        self.stop_rpc()
        self.master.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    app = QobuzRPCApp(root)
    root.mainloop()