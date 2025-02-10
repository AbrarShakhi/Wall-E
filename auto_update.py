import os
import requests
import shutil
import sys
import threading
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from packaging import version

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

    def show_popup(self, title, message, callback=None):
        Clock.schedule_once(lambda dt: self._show_popup(title, message, callback))

    def _show_popup(self, title, message, callback):
        self.popup = UpdatePopup(title, message, callback)
        self.popup.open()

    def get_local_version(self):
        # Get the correct base path for both development and built app
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS  # Use the temporary extraction directory
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        version_path = os.path.join(base_dir, LOCAL_VERSION_FILE)

        if os.path.exists(version_path):
            with open(version_path, "r") as f:
                return f.read().strip()
        return "0.0.0"

    def check_for_updates(self):
        def check_thread():
            try:
                response = requests.get(REMOTE_VERSION_URL)
                response.raise_for_status()
                remote_data = response.json()
            except Exception as e:
                self.show_popup("Error", f"Failed to check updates:\n{str(e)}")
                return

            local_version = self.get_local_version()
            if version.parse(remote_data["version"]) > version.parse(local_version):
                self.show_popup("Update Available",
                                f"New version {remote_data['version']} available!\nWould you like to update now?",
                                self.handle_update_decision)
            else:
                self.show_popup("Info", "You have the latest version")

        threading.Thread(target=check_thread, daemon=True).start()

    def handle_update_decision(self, decision):
        if decision == "now":
            self.show_popup("Downloading", "Starting update download...")
            threading.Thread(target=self.download_and_apply_update, daemon=True).start()
        elif decision == "later":
            self.show_popup("Info", "Update postponed. You can update later from the settings.")

    def download_and_apply_update(self):
        try:
            # Get latest version info
            response = requests.get(REMOTE_VERSION_URL)
            remote_data = response.json()
            download_url = remote_data["download_url"]

            # Create temp directory
            if not os.path.exists(TEMP_UPDATE_FOLDER):
                os.makedirs(TEMP_UPDATE_FOLDER)

            # Download update
            self.show_popup("Downloading", "Downloading update...")
            update_file = os.path.join(TEMP_UPDATE_FOLDER, "Wall-E.exe")  # Match your EXE name

            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded = 0

                with open(update_file, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress = downloaded / total_size * 100
                        self.show_popup("Downloading",
                                        f"Downloading update...\n{progress:.1f}% complete")

            # Replace the old executable
            self.show_popup("Updating", "Applying update...")
            shutil.move(update_file, "Wall-E.exe")

            # Schedule restart
            Clock.schedule_once(lambda dt: self.restart_app())

        except Exception as e:
            self.show_popup("Error", f"Update failed:\n{str(e)}")
            if os.path.exists(TEMP_UPDATE_FOLDER):
                shutil.rmtree(TEMP_UPDATE_FOLDER)

    def restart_app(self):
        self.show_popup("Restart Required", "Update complete!\nApplication will now restart.")

        # Platform-specific restart logic
        if sys.platform == 'win32':
            os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            os.execv(sys.executable, [sys.executable] + sys.argv)