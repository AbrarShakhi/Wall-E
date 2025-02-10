import os
import requests
import shutil
import sys
import threading
import subprocess
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from packaging import version
import time
import json



# Constants
LOCAL_VERSION_FILE = "version.txt"
REMOTE_VERSION_URL = "https://raw.githubusercontent.com/sheikhhossainn/Wall-E/master/version.json"
TEMP_UPDATE_FOLDER = "temp_update"

class UpdatePopup(Popup):
    def __init__(self, title, message, callback=None, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.size_hint = (0.8, 0.4)
        self.callback = callback

        layout = BoxLayout(orientation='vertical', spacing=10)
        layout.add_widget(Label(text=message, halign='center'))

        if callback:
            btn_layout = BoxLayout(spacing=10, size_hint_y=0.4)
            btn_yes = Button(text='Update Now', on_press=self.yes)
            btn_later = Button(text='Later', on_press=self.later)
            btn_layout.add_widget(btn_yes)
            btn_layout.add_widget(btn_later)
            layout.add_widget(btn_layout)

        self.content = layout

    def yes(self, instance):
        self.dismiss()
        if self.callback:
            self.callback("now")

    def later(self, instance):
        self.dismiss()
        if self.callback:
            self.callback("later")

class AutoUpdater:
    def __init__(self, app):
        self.app = app
        self.popup = None
        self.last_update_check = 0
        self.update_check_interval = 24 * 60 * 60  # 24 hours in seconds

    def show_popup(self, title, message, callback=None):
        Clock.schedule_once(lambda dt: self._show_popup(title, message, callback))

    def _show_popup(self, title, message, callback):
        self.popup = UpdatePopup(title, message, callback)
        self.popup.open()

    def get_local_version(self):
        # First, check for an external version.txt in the app directory
        external_version_path = os.path.join(os.getcwd(), LOCAL_VERSION_FILE)
        if os.path.exists(external_version_path):
            with open(external_version_path, "r") as f:
                return f.read().strip()

        # Fallback to the bundled version.txt (for first-time runs)
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        bundled_version_path = os.path.join(base_dir, LOCAL_VERSION_FILE)
        if os.path.exists(bundled_version_path):
            with open(bundled_version_path, "r") as f:
                return f.read().strip()

        return "0.0.0"

    def check_for_updates(self):
        # Check if enough time has passed since the last update check
        current_time = time.time()
        if current_time - self.last_update_check < self.update_check_interval:
            return

        def check_thread():
            try:
                response = requests.get(REMOTE_VERSION_URL, timeout=10)
                response.raise_for_status()
                remote_data = response.json()
            except (requests.RequestException, json.JSONDecodeError) as e:
                # Log the error but don't spam the user with popups
                print(f"Update check failed: {str(e)}")
                return

            local_version = self.get_local_version()
            try:
                if version.parse(remote_data["version"]) > version.parse(local_version):
                    # Update check successful and new version available
                    self.show_popup("Update Available",
                                    f"New version {remote_data['version']} available!\nWould you like to update now?",
                                    self.handle_update_decision)
                else:
                    # Update check successful, but no new version
                    self.show_popup("Info", "You have the latest version")
            except Exception as e:
                print(f"Version comparison error: {str(e)}")

            # Update the last check time
            self.last_update_check = current_time

        # Run the check in a separate thread
        threading.Thread(target=check_thread, daemon=True).start()

    def handle_update_decision(self, decision):
        if decision == "now":
            self.show_popup("Downloading", "Starting update download...")
            threading.Thread(target=self.download_and_apply_update, daemon=True).start()
        elif decision == "later":
            self.show_popup("Info", "Update postponed.")

    def download_and_apply_update(self):
        try:
            response = requests.get(REMOTE_VERSION_URL)
            remote_data = response.json()
            download_url = remote_data["download_url"]
            new_version = remote_data["version"]

            if not os.path.exists(TEMP_UPDATE_FOLDER):
                os.makedirs(TEMP_UPDATE_FOLDER)

            # Use Clock to update UI safely
            def update_popup(message):
                self.popup.dismiss()
                self.show_popup("Downloading", message)

            Clock.schedule_once(lambda dt: update_popup("Starting download..."))

            update_file = os.path.join(TEMP_UPDATE_FOLDER, "Wall-E_new.exe")

            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded = 0

                with open(update_file, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress = downloaded / total_size * 100
                        # Update UI on the main thread
                        Clock.schedule_once(lambda dt: self.show_popup("Downloading", f"Progress: {progress:.1f}%"))

            # Batch script to replace the app
            batch_path = os.path.join(TEMP_UPDATE_FOLDER, "update.bat")
            current_exe = os.path.abspath(sys.argv[0])  # Path to the running executable
            new_exe = os.path.abspath(update_file)
            version_file_path = os.path.abspath(LOCAL_VERSION_FILE)

            with open(batch_path, 'w') as f:
                f.write('@echo off\n')
                f.write('taskkill /F /IM "Wall-E.exe"\n')  # Force-terminate the old app
                f.write('timeout /t 1 /nobreak > nul\n')
                f.write(f'del /f "{current_exe}"\n')
                f.write(f'move /y "{new_exe}" "{current_exe}"\n')
                f.write(f'echo {new_version} > "{version_file_path}"\n')
                f.write(f'start "" "{current_exe}"\n')
                f.write(f'rmdir /s /q "{TEMP_UPDATE_FOLDER}"\n')
                f.write('del "%~f0"\n')

            # Launch the batch script and exit immediately
            subprocess.Popen(
                [batch_path],
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW  # Hide the console window
            )
            sys.exit()

        except Exception as e:
            self.show_popup("Error", f"Update failed:\n{str(e)}")
            if os.path.exists(TEMP_UPDATE_FOLDER):
                shutil.rmtree(TEMP_UPDATE_FOLDER)