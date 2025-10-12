Qobuz Discord RPC Synchronizer (GUI)

A desktop GUI application for Windows that automatically sets your Discord Rich Presence (RPC) status to the music you're currently playing on the Qobuz desktop client.

This project provides a graphical interface and continuous development on the foundation of the original command-line script.
✨ Features

    GUI Application: Easy-to-use graphical interface for simple control.

    Automatic Status: Synchronizes your Discord status with the currently playing track on Qobuz.

    Dynamic Album Art: Fetches album artwork from the iTunes public API for a richer presence display.

    Built-in Update Check: Notifies you when a new version is available directly within the application.

    Windows Only: Designed specifically to integrate with the Qobuz Windows desktop client.

💻 Installation & Usage (End User)

The simplest way to use this application is by downloading and running the compiled Windows executable (.exe). No Python installation is required for end-users.
Prerequisites

    Qobuz Desktop Application must be running.

    Discord Desktop Application must be running.

    In Discord, go to User Settings → Activity Privacy and ensure "Display current activity as a status message" is enabled.

Steps

    Go to the Releases page on GitHub.

    Download the latest compiled executable file (e.g., qobuz_rpc_gui.exe).

    Double-click the downloaded executable to launch the GUI.

    Click the "Start RPC" button within the application window.

The application will now run in the background, continuously monitoring Qobuz and updating your Discord status.

    Note: Closing the main GUI window will automatically stop the RPC connection.

🛠️ Developer Setup (From Source)

If you wish to run the script directly from Python source code, you must manually install the required libraries.
Required Python Packages

pip install pypresence psutil pywin32 requests packaging

Running the Script

python qobuz_rpc_gui.py

💖 Credits and Original Work

This project is a continuation of the original proof-of-concept command-line script created by Lockna.

We extend our sincere thanks to Lockna for providing the foundational script and logic for this Rich Presence synchronizer.

    Original Creator: Lockna

    Original Repository: Lockna/qobuz-rpc

If you encounter any problem with the program, please feel free to open a GitHub Issue.
✅ Future TODO

    Implement proper time remaining/elapsed counter (Requires a robust way to determine track duration/progress).

    Refine the album art caching logic.

    Explore support for other operating systems (macOS/Linux via different window tracking methods).