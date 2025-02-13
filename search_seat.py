import json
import os
import time
import threading
from datetime import datetime, timedelta
from functools import partial
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.scrollview import ScrollView
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from department_mapping import get_department_mapping
from semester_mapping import get_semester_mapping
from user_profile_manager import load_profiles
from auto_email import send_email





def calculate_available_seats(seat_data):
    try:
        current_enrollment, total_capacity = map(int, seat_data.split('/'))
        return total_capacity - current_enrollment, seat_data
    except ValueError:
        return None, None

def get_persistent_dir():
    """Get platform-specific persistent directory for storing data."""
    if os.name == "nt":  # Windows
        base_dir = os.getenv('APPDATA')
    elif os.name == "posix":  # macOS/Linux
        base_dir = os.path.expanduser('~/.local/share')
    else:
        base_dir = os.path.abspath(".")

    app_dir = os.path.join(base_dir, "Wall-E App")
    os.makedirs(app_dir, exist_ok=True)
    return app_dir

def get_file_path(filename):
    """Get full path to a file in the persistent directory."""
    return os.path.join(get_persistent_dir(), filename)


class AlarmManager:
    def __init__(self):
        self.alarms = []
        self.seat_finder = None
        self.load_alarms()

    def load_alarms(self):
        """Load alarms from alarms.json in the persistent directory."""
        self.alarms = []
        alarms_path = get_file_path("alarms.json")
        if os.path.exists(alarms_path):
            try:
                with open(alarms_path, 'r') as f:
                    content = f.read()
                    if content.strip():
                        raw_alarms = json.loads(content)
                        self.alarms = [a for a in raw_alarms if self.validate_alarm(a)]
            except (json.JSONDecodeError, KeyError):
                with open(alarms_path, 'w') as f:
                    json.dump([], f)

    def validate_alarm(self, alarm):
        required_keys = ['time', 'course', 'section', 'department', 'semester', 'profile']
        return all(key in alarm for key in required_keys)

    def save_alarms(self):
        clean_alarms = []
        for alarm in self.alarms:
            clean_alarm = alarm.copy()
            clean_alarm.pop('clock_event', None)
            clean_alarms.append(clean_alarm)
        alarms_path = get_file_path("alarms.json")
        with open(alarms_path, 'w') as f:
            json.dump(clean_alarms, f, indent=2)

    def add_alarm(self, alarm_data):
        self.alarms.append(alarm_data)
        self.save_alarms()
        self.schedule_alarm(alarm_data)

    def delete_alarm(self, alarm_data):
        if alarm_data in self.alarms:
            if 'clock_event' in alarm_data:
                Clock.unschedule(alarm_data['clock_event'])
            self.alarms.remove(alarm_data)
            self.save_alarms()

    def schedule_alarm(self, alarm):
        now = datetime.now()
        try:
            target_time = datetime.strptime(alarm['time'], "%H:%M").time()
            alarm_datetime = datetime.combine(now.date(), target_time)
            if alarm_datetime < now:
                alarm_datetime += timedelta(days=1)
            delay = (alarm_datetime - now).total_seconds()
            alarm['clock_event'] = Clock.schedule_once(
                lambda dt: self.trigger_alarm(alarm),
                delay
            )
        except ValueError:
            pass

    def trigger_alarm(self, alarm):
        if self.seat_finder:
            self.seat_finder.trigger_auto_search(alarm)


class TimerPopup(Popup):
    def __init__(self, seat_finder, **kwargs):
        super().__init__(**kwargs)
        self.seat_finder = seat_finder
        self.alarm_manager = seat_finder.alarm_manager
        self.title = "Manage Alarms"
        self.size_hint = (0.9, 0.7)
        main_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        scroll = ScrollView()
        self.alarm_list = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.alarm_list.bind(minimum_height=self.alarm_list.setter('height'))
        self.refresh_alarm_list()
        scroll.add_widget(self.alarm_list)
        main_layout.add_widget(Label(text="Active Alarms:", size_hint_y=None, height=30))
        main_layout.add_widget(scroll)
        main_layout.add_widget(Label(text="Add New Alarm:", size_hint_y=None, height=30))
        time_grid = GridLayout(cols=4, spacing=10, size_hint_y=None, height=50)
        self.hour_spinner = Spinner(text='08', values=[f"{i:02d}" for i in range(1, 13)], size_hint=(None, None),
                                    width=100)
        self.minute_spinner = Spinner(text='00', values=[f"{i:02d}" for i in range(60)], size_hint=(None, None),
                                      width=100)
        self.ampm_spinner = Spinner(text='AM', values=['AM', 'PM'], size_hint=(None, None), width=100)
        time_grid.add_widget(self.hour_spinner)
        time_grid.add_widget(Label(text=':'))
        time_grid.add_widget(self.minute_spinner)
        time_grid.add_widget(self.ampm_spinner)
        main_layout.add_widget(time_grid)
        days_grid = GridLayout(cols=7, spacing=5, size_hint_y=None, height=50)
        self.repeat_days = {}
        for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']:
            btn = ToggleButton(text=day, group=day, size_hint_x=None, width=70)
            self.repeat_days[day] = btn
            days_grid.add_widget(btn)
        main_layout.add_widget(Label(text="Repeat Days:", size_hint_y=None, height=30))
        main_layout.add_widget(days_grid)
        btn_layout = GridLayout(cols=2, spacing=10, size_hint_y=None, height=50)
        btn_layout.add_widget(Button(text='Add Alarm', on_press=self.add_alarm))
        btn_layout.add_widget(Button(text='Close', on_press=self.dismiss))
        main_layout.add_widget(btn_layout)
        self.content = main_layout

    def refresh_alarm_list(self):
        self.alarm_list.clear_widgets()
        for alarm in self.alarm_manager.alarms:
            item = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
            time_str = alarm['time']
            days_str = ', '.join(alarm.get('repeat', [])) or 'Once'
            item.add_widget(Label(text=f"{time_str} ({days_str})", halign='left'))
            btn_box = BoxLayout(size_hint_x=None, width=150, spacing=5)
            btn_box.add_widget(
                Button(text='Delete', size_hint_x=None, width=70, on_press=lambda x, a=alarm: self.delete_alarm(a)))
            item.add_widget(btn_box)
            self.alarm_list.add_widget(item)

    def add_alarm(self, instance):
        try:
            hour = int(self.hour_spinner.text)
            minute = int(self.minute_spinner.text)
            period = self.ampm_spinner.text
            if period == 'PM' and hour != 12:
                hour += 12
            elif period == 'AM' and hour == 12:
                hour = 0
            alarm_time = f"{hour:02d}:{minute:02d}"
            repeat_days = [day for day, toggle in self.repeat_days.items() if toggle.state == 'down']
            alarm_data = {
                'time': alarm_time,
                'repeat': repeat_days,
                'course': self.seat_finder.course_input.text,
                'section': self.seat_finder.section_input.text,
                'department': self.seat_finder.selected_department,
                'semester': self.seat_finder.selected_semester,
                'profile': self.seat_finder.selected_profile
            }
            self.alarm_manager.add_alarm(alarm_data)
            self.refresh_alarm_list()
        except Exception as e:
            self.seat_finder.show_popup("Error", str(e))

    def delete_alarm(self, alarm):
        self.alarm_manager.delete_alarm(alarm)
        self.refresh_alarm_list()


class SeatFinderScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.auto_email_enabled = False
        self.layout = BoxLayout(orientation="vertical", spacing=10, padding=10)

        self.create_ui()
        self.alarm_manager = AlarmManager()
        self.alarm_manager.seat_finder = self
        self.search_active = False

        def on_enter(self):
            """Refresh dropdowns when the screen becomes active"""
            self.load_dropdowns()

    def create_ui(self):
        self.layout.add_widget(Label(text="Seat Finder", font_size=24, size_hint_y=None, height=50))
        self.profile_dropdown = DropDown()
        self.profile_button = Button(text="Select Profile", size_hint_y=None, height=40)
        self.profile_button.bind(on_release=self.profile_dropdown.open)
        self.layout.add_widget(self.profile_button)
        self.department_dropdown = DropDown()
        self.department_button = Button(text="Select Department", size_hint_y=None, height=40)
        self.department_button.bind(on_release=self.department_dropdown.open)
        self.layout.add_widget(self.department_button)
        self.semester_dropdown = DropDown()
        self.semester_button = Button(text="Select Semester", size_hint_y=None, height=40)
        self.semester_button.bind(on_release=self.semester_dropdown.open)
        self.layout.add_widget(self.semester_button)
        self.course_input = TextInput(hint_text="Course Code", size_hint_y=None, height=40)
        self.layout.add_widget(self.course_input)
        self.section_input = TextInput(hint_text="Section", size_hint_y=None, height=40)
        self.layout.add_widget(self.section_input)
        self.auto_email_toggle = Button(text="Auto Email: OFF", size_hint_y=None, height=40)
        self.auto_email_toggle.bind(on_press=self.toggle_auto_email)
        self.layout.add_widget(self.auto_email_toggle)
        self.timer_button = Button(text="Set Timer", size_hint_y=None, height=40)
        self.timer_button.bind(on_press=self.show_timer_popup)
        self.layout.add_widget(self.timer_button)
        self.search_button = Button(text="Search Now", size_hint_y=None, height=40)
        self.search_button.bind(on_press=self.start_search)
        self.layout.add_widget(self.search_button)
        self.back_button = Button(text="Back to Main Menu", size_hint_y=None, height=40)
        self.back_button.bind(on_press=self.go_back)
        self.layout.add_widget(self.back_button)
        self.add_widget(self.layout)
        self.load_dropdowns()

    def load_dropdowns(self):
        profiles = load_profiles()
        self.profile_dropdown.clear_widgets()
        for profile in profiles.values():
            btn = Button(text=profile['student_name'], size_hint_y=None, height=40)
            btn.bind(on_release=lambda x, p=profile: self.select_profile(p))
            self.profile_dropdown.add_widget(btn)
        self.department_dropdown.clear_widgets()
        for dept in get_department_mapping():
            btn = Button(text=dept, size_hint_y=None, height=40)
            btn.bind(on_release=lambda x, d=dept: self.select_department(d))
            self.department_dropdown.add_widget(btn)
        self.semester_dropdown.clear_widgets()
        for sem in get_semester_mapping():
            btn = Button(text=sem, size_hint_y=None, height=40)
            btn.bind(on_release=lambda x, s=sem: self.select_semester(s))
            self.semester_dropdown.add_widget(btn)

    def select_profile(self, profile):
        self.selected_profile = profile
        self.profile_button.text = profile['student_name']
        self.profile_dropdown.dismiss()

    def select_department(self, department):
        self.selected_department = department
        self.department_button.text = department
        self.department_dropdown.dismiss()

    def select_semester(self, semester):
        self.selected_semester = semester
        self.semester_button.text = semester
        self.semester_dropdown.dismiss()

    def toggle_auto_email(self, instance):
        self.auto_email_enabled = not self.auto_email_enabled
        instance.text = f"Auto Email: {'ON' if self.auto_email_enabled else 'OFF'}"

    def show_timer_popup(self, instance):
        if self.validate_fields():
            TimerPopup(self).open()
        else:
            self.show_popup("Error", "Please fill all fields first!")

    def validate_fields(self):
        return all([
            hasattr(self, 'selected_profile'),
            hasattr(self, 'selected_department'),
            hasattr(self, 'selected_semester'),
            self.course_input.text.strip(),
            self.section_input.text.strip()
        ])

    def start_search(self, instance):
        if not self.validate_fields():
            self.show_popup("Error", "Please fill all fields!")
            return
        if self.search_active:
            self.show_popup("Info", "Search already in progress!")
            return

        self.search_active = True
        threading.Thread(target=self.perform_search_thread, daemon=True).start()

    def perform_search_thread(self):
        try:
            driver = webdriver.Chrome()
            driver.get("https://portal.ewubd.edu/")
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "username")))
            driver.find_element(By.ID, "username").send_keys(self.selected_profile['student_id'])
            driver.find_element(By.ID, "pass").send_keys(self.selected_profile['portal_password'])
            first = int(driver.find_element(By.ID, "lblFirstNo").text)
            second = int(driver.find_element(By.ID, "lblSecondNo").text)
            driver.find_element(By.ID, "lblcaptchaAnswer").send_keys(str(first + second))
            driver.find_element(By.ID, "submit").click()
            WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//a[.//strong[text()='Offered Courses']]"))).click()
            time.sleep(2)
            Select(driver.find_element(By.XPATH, "//select[@data-ng-model='filterDepartmentId']")) \
                .select_by_visible_text(self.selected_department)
            Select(driver.find_element(By.XPATH, "//select[@data-ng-model='filterSemesterId']")) \
                .select_by_visible_text(self.selected_semester)
            driver.find_element(By.XPATH, "//a[contains(text(), 'Show Offered Courses')]").click()
            time.sleep(3)
            seats_found = False
            seat_info = ""
            for row in driver.find_elements(By.XPATH, "//tbody/tr"):
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 6 and cells[0].text.strip() == self.course_input.text.strip() \
                        and cells[1].text.strip() == self.section_input.text.strip():
                    seats = cells[5].text.strip()
                    available_seats, _ = calculate_available_seats(seats)
                    if available_seats and available_seats > 0:
                        seats_found = True
                        seat_info = f"Found seats: {seats}"
                        Clock.schedule_once(partial(self.handle_success, seat_info))
                        if self.auto_email_enabled:
                            self.send_email()
                    break
            if not seats_found:
                seat_info = "No available seats found"
                Clock.schedule_once(partial(self.show_popup, "Result", seat_info))
        except Exception as e:
            Clock.schedule_once(partial(self.show_popup, "Error", f"Search failed: {str(e)}"))
        finally:
            self.search_active = False
            if 'driver' in locals():
                driver.quit()

    def handle_success(self, seat_info, dt):
        if seat_info:  # Add this check
            self.show_popup("Success", seat_info)
            self.clear_all_alarms()
            self.reset_fields()
        else:
            self.show_popup("Error", "No seat information found.")

    def clear_all_alarms(self):
        for alarm in self.alarm_manager.alarms[:]:
            if 'clock_event' in alarm:
                Clock.unschedule(alarm['clock_event'])
            self.alarm_manager.delete_alarm(alarm)
        self.alarm_manager.save_alarms()

    def reset_fields(self):
        self.course_input.text = ""
        self.section_input.text = ""

    def trigger_auto_search(self, alarm):
        if not self.search_active:
            self.search_active = True
            threading.Thread(target=partial(self.auto_search_thread, alarm), daemon=True).start()

    def auto_search_thread(self, alarm):
        try:
            self.selected_profile = alarm['profile']
            self.selected_department = alarm['department']
            self.selected_semester = alarm['semester']
            self.course_input.text = alarm['course']
            self.section_input.text = alarm['section']
            result = self.perform_search_thread()
            if result and "available" in result.lower():
                Clock.schedule_once(partial(self.handle_success, result))
        except Exception as e:
            Clock.schedule_once(partial(self.show_popup, "Error", str(e)))
        finally:
            self.search_active = False

    def send_email(self):
        def email_thread():
            try:
                send_email(
                    self.selected_profile['student_name'],
                    self.selected_profile['student_email'],
                    self.selected_profile['advisor_email'],
                    self.course_input.text,
                    self.section_input.text,
                    self.selected_profile['student_id']
                )
                Clock.schedule_once(lambda dt: self.show_popup("Email Sent", "Notification sent!"))
            except Exception as e:
                Clock.schedule_once(lambda dt: self.show_popup("Email Failed", str(e)))

        threading.Thread(target=email_thread, daemon=True).start()

    def show_popup(self, title, message, dt=None):
        content = BoxLayout(orientation='vertical', spacing=10)
        content.add_widget(Label(text=message))
        Popup(title=title, content=content, size_hint=(0.8, 0.4)).open()

    def go_back(self, instance):
        self.manager.current = 'home'