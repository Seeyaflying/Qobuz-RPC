# Qobuz Discord RPC Synchronizer (GUI)

A **desktop GUI application** for Windows that automatically sets your Discord Rich Presence (RPC) status to the music you're currently playing on the **Qobuz desktop client**.

This project provides a graphical interface and continuous development on the foundation of the original command-line script.

---

## ✨ Features

* **GUI Application:** Easy-to-use graphical interface for simple control.
* **Automatic Status:** Synchronizes your Discord status with the currently playing track on Qobuz.
* **Dynamic Album Art:** Fetches album artwork from the iTunes public API for a richer presence display.
* **Built-in Update Check:** Notifies you when a new version is available directly within the application.
* **Windows Only:** Designed specifically to integrate with the Qobuz Windows desktop client.

---

## 💻 Installation & Usage (End User)

The simplest way to use this application is by downloading and running the compiled Windows executable (`.exe`). **No Python installation is required for end-users.**

### Prerequisites

1.  **Qobuz Desktop Application** must be running.
2.  **Discord Desktop Application** must be running.
3.  In Discord, go to **User Settings** $\rightarrow$ **Activity Privacy** and ensure **"Display current activity as a status message"** is enabled.

### Steps

1.  Download the latest executable directly from the [**GitHub Releases page**](https://github.com/Seeyaflying/Qobuz-RPC/releases/latest).
2.  Download the latest compiled executable file (e.g., `qobuz_rpc_gui.exe`).
3.  **Double-click** the downloaded executable to launch the GUI.
4.  Click the **"Start RPC"** button within the application window.

The application will now run in the background, continuously monitoring Qobuz and updating your Discord status.

> **Note:** Closing the main GUI window will automatically stop the RPC connection.

---
## 🛑 Important: Windows Security Warning (SmartScreen)

Because this application is new and maintained by a small group of independent developers, **Windows Defender SmartScreen** has not yet built a positive reputation for it. This is a common issue for new software.

**Your app is safe to use.** You may see a temporary warning when you first download or run the installer.

### How to Safely Bypass the SmartScreen Warning

If you see a blue window titled **"Windows protected your PC,"** follow these two steps to complete the installation:

1.  Click the **"More info"** text link, located beneath the main message.
2.  A new button will appear on the right. Click **"Run anyway"** to launch the installer.

### Our Plan to Resolve This Permanently

We are actively working to establish trust and resolve this warning for all future users by:

* Submitting the file to Microsoft for review as a false positive.
* Acquiring a **Code Signing Certificate** to verify our identity as the publisher and instantly boost reputation.

### This is a temporary inconvenience, and we appreciate your support! If you have any concerns, please contact our support channel at **turtlehavengames@gmail.com**.


## 🛠️ Developer Setup (From Source)

If you wish to run the script directly from Python source code, you must manually install the required libraries.

### Required Python Packages

pip install pypresence psutil pywin32 requests packaging

### Running the Script
python qobuz_rpc_gui.py

## 💖 Credits and Original Work

This project is a continuation of the original proof-of-concept command-line script created by **Lockna**.

We extend our sincere thanks to **Lockna** for providing the foundational script and logic for this Rich Presence synchronizer.

* **Original Creator:** Lockna
* **Original Repository:** [Lockna/qobuz-rpc](https://github.com/Lockna/qobuz-rpc)

If you encounter any problem with the program, please feel free to open a GitHub Issue.

---

## ✅ Future TODO

* Implement proper time remaining/elapsed counter (Requires a robust way to determine track duration/progress).
* Refine the album art caching logic.
* Explore support for other operating systems (macOS/Linux via different window tracking methods).