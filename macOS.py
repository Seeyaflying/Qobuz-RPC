import tkinter as tk
from tkinter import messagebox
import threading
import time
import os
import requests
import subprocess  # New dependency for macOS AppleScript execution
from packaging.version import parse as parse_version

# --- 1. Versioning and Update Configuration ---
LOCAL_VERSION = "1.0.0"
# GitHub links (configured to your repo: Seeyaflying/Qobuz-RPC)
VERSION_URL = "https://raw.githubusercontent.com/Seeyaflying/Qobuz-RPC/main/latest_version.txt"
DOWNLOAD_URL = "https://github.com/Seeyaflying/Qobuz-RPC/releases/latest"
# -------------------------------------------

# --- External Libraries ---
try:
    from pypresence import Presence
    import psutil
    # Removed: ctypes, win32gui, win32process (Windows only)
except ImportError:
    # Handle missing dependencies gracefully
    RPC_AVAILABLE = False
    print("Warning: Missing required libraries. RPC functionality disabled.")


    # Define stubs to prevent immediate crash during import
    class Presence:
        def __init__(self, client_id): pass

        def connect(self): print("RPC connection stub.")

        def update(self, **kwargs): pass

        def clear(self): pass

        def close(self): pass
else:
    RPC_AVAILABLE = True

# Discord Application Client ID for Qobuz (Hardcoded)
CLIENT_ID = "928957672907227147"
QOBUZ_APPLICATION_NAME = "Qobuz"  # Changed from Qobuz.exe to Qobuz for macOS


# --- 2. ROBUST UPDATE CHECKING LOGIC (Unchanged) ---

def fetch_latest_version(url, max_retries=3):
    """Fetches the latest version string from the remote URL with retries."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.text.strip()
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    return None


def check_for_updates_logic(local_version, version_url, download_url):
    """Compares versions and returns a status dictionary."""
    remote_version_str = fetch_latest_version(version_url)

    if remote_version_str is None:
        return {"status": "error", "message": "Update check failed (Network Error)."}

    try:
        local = parse_version(local_version)
        remote = parse_version(remote_version_str)

        if remote > local:
            message = (
                f"🚨 UPDATE AVAILABLE! 🚨\n\n"
                f"Your version: v{local_version}\n"
                f"Latest version: v{remote_version_str}\n\n"
                f"Please download the new executable from the GitHub repository:\n"
                f"{download_url}"
            )
            return {"status": "update", "message": message, "remote_version": remote_version_str}

        return {"status": "ok", "message": f"Running latest version (v{local_version})."}

    except Exception:
        return {"status": "error", "message": "Update check failed (Parsing Error)."}


# -------------------------------------------

# --- 3. RPC SYNCHRONIZER THREAD (MODIFIED FOR MACOS) ---

class RPCSynchronizer(threading.Thread):
    """Handles the Discord RPC connection and background track title monitoring."""

    def __init__(self, app_instance, client_id):
        super().__init__()
        self.app = app_instance
        self.client_id = client_id
        self._stop_event = threading.Event()
        self.rpc = None
        self.start_time = None
        # Cache stores (song title - artist) -> (art_url, duration_ms) mapping
        self.art_cache = {}

    def fetch_album_art_and_duration(self, song_title, artist_name):
        """
        Queries the iTunes public search API for the album art URL and track duration.
        Returns: (art_url: str or None, duration_ms: int or None)
        """
        search_term = f"{song_title} {artist_name}"
        url = f"https://itunes.apple.com/search?term={search_term}&entity=song&limit=1"

        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()

            if data.get('resultCount', 0) > 0 and data['results']:
                result = data['results'][0]
                art_url = result.get('artworkUrl100', None)
                duration_ms = result.get('trackTimeMillis', None)

                if art_url:
                    # Replace the size component for a higher quality image
                    large_art_url = art_url.replace('100x100bb', '512x512bb')
                    return large_art_url, duration_ms
        except requests.exceptions.RequestException as e:
            self.app.update_status(f"Qobuz: Art search failed (API Error)", color=self.app.color_status_fail)
            print(f"Failed to fetch art/duration from iTunes (Request Error): {e}")
        except Exception as e:
            self.app.update_status(f"Qobuz: Art search failed (Parse Error)", color=self.app.color_status_fail)
            print(f"Failed to process art/duration response: {e}")

        return None, None

    def stop(self):
        """Signals the thread to stop and clears RPC."""
        self._stop_event.set()
        if self.rpc:
            try:
                self.rpc.clear()
                self.rpc.close()
            except Exception as e:
                print(f"Error while closing RPC: {e}")
        self.app.update_status("Stopped")

    # --- MACOS SPECIFIC TRACKING FUNCTION ---
    def get_qobuz_track_info_macos(self):
        """
        Uses AppleScript to check if Qobuz is running and get the current track info.
        Returns: The title string ("Song Title - Artist Name"), "Qobuz" (if running but paused), or None (if not running).
        """
        # AppleScript to get current track and artist, or "Qobuz" if running but idle
        applescript = f'''
        tell application "{QOBUZ_APPLICATION_NAME}"
            if it is running then
                try
                    set trackName to name of current track
                    set artistName to artist of current track
                    return trackName & " - " & artistName
                on error
                    # Running but not playing (idle/paused)
                    return "{QOBUZ_APPLICATION_NAME}"
                end try
            else
                return ""
            end if
        end tell
        '''
        try:
            process = subprocess.Popen(['osascript', '-e', applescript],
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       text=True)
            # Use a short timeout for responsiveness
            stdout, stderr = process.communicate(timeout=2)

            if process.returncode != 0:
                # osascript failed (e.g., app is not open, or permission issue)
                if "Application isn't running" in stderr:
                    return None  # Not running
                # Return 'Qobuz' as a fallback if the app is running but AppleScript failed
                return QOBUZ_APPLICATION_NAME

            title = stdout.strip()
            if not title:
                return None  # Not running or script failed silently

            return title

        except subprocess.TimeoutExpired:
            print("AppleScript command timed out.")
            return None
        except Exception as e:
            print(f"AppleScript execution failed: {e}")
            return None

    # Removed: get_qobuz_handle and get_window_title_by_handle

    def run(self):
        """The main execution loop for the thread."""
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
            print(f"RPC Connection Failed: {e}")
            return

        last_title = ""

        while not self._stop_event.is_set():

            # --- MACOS TRACKING REPLACEMENT ---
            current_title = self.get_qobuz_track_info_macos()

            if current_title is None:
                # Qobuz application is not running
                if last_title != "":
                    self.rpc.clear()
                    self.app.update_status("Qobuz Closed. Listening...")
                    last_title = ""
                self.start_time = None
                time.sleep(5)
                continue

            # Skip None check, as get_qobuz_track_info_macos should return a string or None

            if current_title != last_title:
                last_title = current_title

                # Check if the title is just 'Qobuz' (idle/paused)
                if last_title.strip() == QOBUZ_APPLICATION_NAME:
                    self.rpc.clear()
                    self.app.update_status("Qobuz: Idle/Paused")
                    self.start_time = None

                else:
                    # Playing music! Attempt to parse "Song Title - Artist Name"
                    try:
                        title_parts = last_title.rsplit(' - ', 1)

                        song_title = title_parts[0].strip()
                        artist_name = title_parts[1].strip() if len(title_parts) > 1 else "Unknown Artist"

                        # --- Dynamic Album Art Logic ---
                        cache_key = last_title
                        art_url = self.art_cache.get(cache_key, (None, None))[0]

                        if art_url is None:
                            self.app.update_status(f"Qobuz: Searching for album art for '{song_title}'...")
                            art_url, duration_ms = self.fetch_album_art_and_duration(song_title, artist_name)
                            if art_url:
                                self.art_cache[cache_key] = (art_url, duration_ms)  # Cache result

                        self.start_time = None
                        large_image_asset = art_url if art_url else "qobuz"

                        # Update Discord Rich Presence
                        self.rpc.update(
                            details=song_title,
                            state=f"by {artist_name}",
                            large_image=large_image_asset,
                            large_text=f"{song_title} - {artist_name}",
                            small_image="qobuz_icon",
                            small_text="Qobuz Player"
                        )

                        self.app.update_status(f"Qobuz: Playing '{song_title}'")

                    except Exception as e:
                        self.rpc.clear()
                        self.app.update_status(f"Qobuz: Runtime Error", color=self.app.color_status_fail)
                        print(f"RPC Update failed: {e}")
                        self.start_time = None

            time.sleep(1)

        # Final cleanup when loop ends
        try:
            if self.rpc:
                self.rpc.clear()
                if self.rpc.sock:
                    self.rpc.close()
        except Exception:
            pass


# --- 4. TKINTER GUI CLASS (Unchanged) ---

class QobuzRPCApp:
    """The main Tkinter application class for the GUI."""

    def __init__(self, master):
        self.master = master
        master.title(f"Qobuz Discord RPC Synchronizer (v{LOCAL_VERSION})")
        master.geometry("550x450")
        master.resizable(False, False)
        master.configure(bg='#36393F')

        master.protocol("WM_DELETE_WINDOW", self.on_close)

        self.rpc_thread = None
        self.running = False

        # --- Styling ---
        self.font_main = ('Inter', 12)
        self.font_status = ('Inter', 14, 'bold')
        self.color_text = '#FFFFFF'
        self.color_status_ok = '#43B581'
        self.color_status_fail = '#F04747'
        self.color_button_start = '#7289DA'
        self.color_button_stop = '#F04747'
        self.color_input_bg = '#40444B'

        # --- Frames ---
        self.main_frame = tk.Frame(master, bg=master['bg'], padx=20, pady=20)
        self.main_frame.pack(fill='both', expand=True)

        self.main_frame.grid_columnconfigure(0, weight=1)
        row_idx = 0

        # --- Simple Instructions Label ---
        tk.Label(self.main_frame,
                 text="Qobuz Discord Rich Presence",
                 bg=master['bg'], fg=self.color_text, font=('Inter', 18, 'bold')
                 ).grid(row=row_idx, column=0, pady=(0, 5), sticky='ew');
        row_idx += 1

        tk.Label(self.main_frame,
                 text="Click Start RPC to track Qobuz on Discord.",
                 bg=master['bg'], fg='#C0C4CC', font=('Inter', 12)
                 ).grid(row=row_idx, column=0, pady=(0, 20), sticky='ew');
        row_idx += 1

        # --- Permissions/Instructions Label ---
        tk.Label(self.main_frame, text="Discord Requirement:", bg=master['bg'], fg=self.color_text,
                 font=self.font_main).grid(row=row_idx, column=0, pady=(5, 0), sticky='ew');
        row_idx += 1
        tk.Label(self.main_frame,
                 text="Must enable 'Display current activity as a status message' in Discord's User Settings > Activity Privacy.",
                 bg=master['bg'], fg='#C0C4CC', font=('Inter', 9), wraplength=500, justify=tk.CENTER
                 ).grid(row=row_idx, column=0, sticky='ew');
        row_idx += 1

        # --- Status Label ---
        tk.Label(self.main_frame, text="Current Status:", bg=master['bg'], fg=self.color_text,
                 font=self.font_main).grid(row=row_idx, column=0, pady=(20, 5), sticky='ew');
        row_idx += 1

        self.status_var = tk.StringVar(value="Ready to Start")
        self.status_label = tk.Label(self.main_frame, textvariable=self.status_var, bg=master['bg'],
                                     fg=self.color_status_ok, font=self.font_status)
        self.status_label.grid(row=row_idx, column=0, sticky='ew');
        row_idx += 1

        # --- Buttons ---
        self.button_frame = tk.Frame(self.main_frame, bg=master['bg'], pady=20)
        self.button_frame.grid(row=row_idx, column=0, sticky='s');
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

        if not RPC_AVAILABLE:
            self.update_status("Missing Dependencies", color=self.color_status_fail)
            self.start_button.config(state=tk.DISABLED)

        # --- Version Info and Update Button ---
        version_frame = tk.Frame(self.main_frame, bg=master['bg'], pady=5)
        version_frame.grid(row=row_idx, column=0, sticky='ew');
        row_idx += 1

        tk.Label(version_frame,
                 text=f"Local Version: {LOCAL_VERSION}",
                 bg=master['bg'], fg='#C0C4CC', font=('Inter', 10)
                 ).pack(pady=(0, 5))

        tk.Button(version_frame, text="Check for Updates", command=self.check_for_updates,
                  width=25, height=1, bg='#5865F2', fg=self.color_text, font=('Inter', 11),
                  relief='flat', activebackground='#5865F2', activeforeground=self.color_text,
                  cursor="hand2").pack()
        # ----------------------------------------

        # Start update check immediately on load
        self._start_initial_update_check()

    def update_status(self, message, color=None):
        """Updates the status label text and color."""
        self.status_var.set(message)
        if color:
            self.status_label.config(fg=color)
        elif "Error" in message or "Failed" in message or "Update available" in message:
            self.status_label.config(fg=self.color_status_fail)
        elif "Playing" in message or "Connected" in message or "Found" in message or "latest version" in message:
            self.status_label.config(fg=self.color_status_ok)
        else:
            self.status_label.config(fg=self.color_text)

    # --- Update Check Methods (Unchanged) ---

    def _start_initial_update_check(self):
        """Starts the update check on application startup in a non-blocking thread."""
        self.update_status("Checking for updates...")
        threading.Thread(target=self._check_for_updates_async, daemon=True).start()

    def check_for_updates(self):
        """Called by the manual button. Starts the update check process."""
        self.update_status("Checking for updates manually...")
        threading.Thread(target=self._check_for_updates_async, daemon=True).start()

    def _check_for_updates_async(self):
        """The thread target that performs the network check and updates the GUI."""
        update_info = check_for_updates_logic(LOCAL_VERSION, VERSION_URL, DOWNLOAD_URL)
        self.master.after(0, lambda: self._handle_update_result_gui(update_info))

    def _handle_update_result_gui(self, update_info):
        """Updates GUI based on the result of the update check."""
        if update_info["status"] == "update":
            self.update_status(
                f"Update available! v{update_info['remote_version']} (Local: v{LOCAL_VERSION})",
                color=self.color_status_fail
            )
            messagebox.showinfo("Update Available", update_info["message"])
        elif update_info["status"] == "error":
            if self.status_var.get() != "Ready to Start":
                self.update_status(f"Update check failed: {update_info['message']}",
                                   color=self.color_status_fail)
        elif update_info["status"] == "ok":
            self.update_status(update_info['message'], color=self.color_status_ok)

    # --- RPC Control Methods (Unchanged) ---

    def start_rpc(self):
        """Starts the RPC background thread."""
        if self.running:
            return

        client_id_to_use = CLIENT_ID

        if not client_id_to_use.strip().isdigit():
            messagebox.showerror("Configuration Error",
                                 "The hardcoded Client ID in the script file is invalid. Please correct it.")
            return

        self.rpc_thread = RPCSynchronizer(self, client_id_to_use)
        self.rpc_thread.daemon = True
        self.rpc_thread.start()
        self.running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.update_status("Starting RPC...")

    def stop_rpc(self):
        """Stops the RPC background thread."""
        if not self.running or self.rpc_thread is None:
            return

        self.rpc_thread.stop()
        self.rpc_thread.join(timeout=2)
        self.rpc_thread = None
        self.running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.update_status("Stopped", color=self.color_text)

    def on_close(self):
        """Handles closing the application gracefully."""
        if self.running:
            self.stop_rpc()
        self.master.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    app = QobuzRPCApp(root)
    root.mainloop()