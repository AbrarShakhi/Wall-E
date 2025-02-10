import json
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
import os
import sys
from pathlib import Path




def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# Loading and saving profiles logic
def load_profiles():
    """Load the profiles from the JSON file."""
    try:
        with open('profiles.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

def save_profiles(profiles):
    """Save the updated profiles to the JSON file."""
    try:
        with open('profiles.json', 'w') as file:
            json.dump(profiles, file, indent=4)
    except Exception as e:
        print(f"Error saving profiles: {e}")


# Profile Management Screens
class ProfileManagementScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)

        layout.add_widget(Label(text="Profile Management", font_size=24, size_hint_y=None, height=50))

        create_button = Button(text="Create Profile", size_hint_y=None, height=50)
        create_button.bind(on_press=self.go_create_profile)
        layout.add_widget(create_button)

        view_button = Button(text="View Profiles", size_hint_y=None, height=50)
        view_button.bind(on_press=self.go_view_profiles)
        layout.add_widget(view_button)

        back_button = Button(text="Back to Main Menu", size_hint_y=None, height=50)
        back_button.bind(on_press=self.go_home)
        layout.add_widget(back_button)

        self.add_widget(layout)

    def go_create_profile(self, instance):
        self.manager.current = "create_profile"

    def go_view_profiles(self, instance):
        self.manager.current = "view_profiles"

    def go_home(self, instance):
        self.manager.current = "home"

class CreateProfileScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)

        layout.add_widget(Label(text="Create Profile", font_size=24, size_hint_y=None, height=40))

        self.fields = {}
        field_names = [
            "Student Name",
            "Student ID",
            "Portal Password",
            "Student Email",
            "Advisor Email"
        ]

        # Create TextInput fields for each profile attribute
        for name in field_names:
            self.fields[name] = TextInput(hint_text=name, multiline=False)
            layout.add_widget(self.fields[name])

        self.message_label = Label(text="", color=(1, 0, 0, 1), size_hint_y=None, height=30)
        layout.add_widget(self.message_label)

        save_button = Button(text="Save Profile", size_hint_y=None, height=50)
        save_button.bind(on_press=self.save_profile)
        layout.add_widget(save_button)

        back_button = Button(text="Back to Management", size_hint_y=None, height=50)
        back_button.bind(on_press=self.go_back_to_management)
        layout.add_widget(back_button)

        self.add_widget(layout)

    def go_back_to_management(self, instance):
        self.manager.current = "profile_management"

    def save_profile(self, instance):
        # Access values for each profile field
        profile_data = {
            "student_name": self.fields["Student Name"].text.strip(),
            "student_id": self.fields["Student ID"].text.strip(),
            "portal_password": self.fields["Portal Password"].text.strip(),
            "student_email": self.fields["Student Email"].text.strip(),
            "advisor_email": self.fields["Advisor Email"].text.strip(),
        }

        if not profile_data["student_email"].endswith("@std.ewubd.edu"):
            self.message_label.text = "Invalid student email! Must use @std.ewubd.edu"
            return

        # Check if all fields are filled
        if not all(profile_data.values()):
            self.message_label.text = "All fields are required!"
            return

        profiles = load_profiles()

        if profiles:
            largest_key = max(int(key) for key in profiles.keys())  # Get the largest numeric key
            new_key = str(largest_key + 1)
        else:
            new_key = "1"

        profiles[new_key] = profile_data
        save_profiles(profiles)

        self.message_label.text = "Profile saved successfully!"

        # Trigger dropdown refresh
        seat_finder = self.manager.get_screen('seat_finder')
        seat_finder.load_dropdowns()

        # Clear all fields after saving
        for field in self.fields.values():
            field.text = ""

class ViewProfilesScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)

        layout.add_widget(Label(text="View Profiles", font_size=24, size_hint_y=None, height=50))

        self.scroll_view = ScrollView()
        self.profiles_list = BoxLayout(orientation="vertical", size_hint_y=None)
        self.scroll_view.add_widget(self.profiles_list)
        layout.add_widget(self.scroll_view)

        back_button = Button(text="Back to Management", size_hint_y=None, height=50)
        back_button.bind(on_press=self.go_back_to_management)
        layout.add_widget(back_button)

        self.add_widget(layout)

    def go_back_to_management(self, instance):
        self.manager.current = "profile_management"

    def on_enter(self):
        self.update_profiles()

    def update_profiles(self):
        profiles = load_profiles()
        self.profiles_list.clear_widgets()

        if not profiles:
            self.profiles_list.add_widget(Label(text="No profiles found.", size_hint_y=None, height=30))
            return

        # Adjusting height based on number of profiles
        self.profiles_list.height = len(profiles) * 60  # Each profile is 60px high

        for key, profile in profiles.items():
            student_name = profile.get('student_name', 'N/A')
            student_id = profile.get('student_id', 'N/A')

            profile_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height=50, spacing=10)

            profile_info = Label(
                text=f"{student_name} ({student_id})",
                size_hint_x=0.6,
                halign="left",
                valign="middle"
            )
            profile_info.bind(size=profile_info.setter('text_size'))
            profile_layout.add_widget(profile_info)

            edit_icon = Button(
                size_hint=(None, None),
                size=(50, 50),
                background_normal=get_resource_path("Icons/edit_icon.png")
            )
            edit_icon.bind(on_press=lambda instance, k=key: self.edit_profile(k))
            profile_layout.add_widget(edit_icon)

            delete_icon = Button(
                size_hint=(None, None),
                size=(50, 50),
                background_normal=get_resource_path("Icons/delete_icon.png")
            )
            delete_icon.bind(on_press=lambda instance, k=key: self.show_delete_confirmation(k))
            profile_layout.add_widget(delete_icon)

            self.profiles_list.add_widget(profile_layout)

    def show_delete_confirmation(self, key):
        """Prompt the user to confirm deletion."""
        profiles = load_profiles()
        if key not in profiles:
            return

        content = BoxLayout(orientation="vertical", spacing=10, padding=10)
        content.add_widget(Label(text="Are you sure you want to delete this profile?"))

        buttons = BoxLayout(size_hint_y=None, height=50, spacing=10)
        yes_button = Button(text="Yes", size_hint_x=0.5)
        no_button = Button(text="No", size_hint_x=0.5)
        buttons.add_widget(yes_button)
        buttons.add_widget(no_button)
        content.add_widget(buttons)

        popup = Popup(
            title="Confirm Deletion",
            content=content,
            size_hint=(0.8, 0.4),
            auto_dismiss=False,
        )

        yes_button.bind(on_press=lambda instance: self.confirm_delete(key, popup))
        no_button.bind(on_press=popup.dismiss)

        popup.open()

    def confirm_delete(self, key, popup):
        profiles = load_profiles()
        if key in profiles:
            del profiles[key]
            save_profiles(profiles)

            # Refresh dropdowns in the seat finder screen
            seat_finder = self.manager.get_screen('seat_finder')
            seat_finder.load_dropdowns()

            self.update_profiles()
        popup.dismiss()

    def edit_profile(self, key):
        profile = load_profiles().get(key, {})
        if profile:
            self.manager.get_screen("edit_profile").set_profile(key, profile)
            self.manager.current = "edit_profile"


class EditProfileScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)

        layout.add_widget(Label(text="Edit Profile", font_size=24, size_hint_y=None, height=40))

        self.fields = {}
        field_names = ["Student Name", "Student ID", "Portal Password", "Student Email", "Advisor Email"]

        for name in field_names:
            self.fields[name] = TextInput(hint_text=name, multiline=False)
            layout.add_widget(self.fields[name])

        save_button = Button(text="Save Changes", size_hint_y=None, height=50)
        save_button.bind(on_press=self.save_profile)
        layout.add_widget(save_button)


        back_button = Button(text="Back to Profiles", size_hint_y=None, height=50)
        back_button.bind(on_press=self.go_back_to_profiles)
        layout.add_widget(back_button)

        self.add_widget(layout)
        self.profile_key = None

    def set_profile(self, key, profile_data):
        self.profile_key = key
        for name, field in self.fields.items():
            field.text = profile_data.get(name.lower().replace(" ", "_"), "")

    def save_profile(self, instance):
        updated_profile = {name.lower().replace(" ", "_"): field.text.strip() for name, field in self.fields.items()}
        profiles = load_profiles()
        profiles[self.profile_key] = updated_profile
        save_profiles(profiles)
        self.manager.current = "view_profiles"

        if not updated_profile["student_email"].endswith("@std.ewubd.edu"):
            self.show_error("Invalid student email! Must use @std.ewubd.edu")
            return

        # Refresh dropdowns in the seat finder screen
        seat_finder = self.manager.get_screen('seat_finder')
        seat_finder.load_dropdowns()

    def go_back_to_profiles(self, instance):
        self.manager.current = "view_profiles"


# Run the application
if __name__ == "__main__":
    from kivy.app import App
    from kivy.uix.screenmanager import ScreenManager

    class ProfileApp(App):
        def build(self):
            sm = ScreenManager()
            sm.add_widget(ProfileManagementScreen(name="profile_management"))
            sm.add_widget(CreateProfileScreen(name="create_profile"))
            sm.add_widget(ViewProfilesScreen(name="view_profiles"))
            sm.add_widget(EditProfileScreen(name="edit_profile"))
            return sm

    ProfileApp().run()
