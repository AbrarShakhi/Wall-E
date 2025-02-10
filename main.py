from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from user_profile_manager import ProfileManagementScreen, CreateProfileScreen, ViewProfilesScreen, EditProfileScreen
from search_seat import SeatFinderScreen
from email_template_manager import EmailTemplateScreen, ViewTemplateScreen
from auto_update import AutoUpdater



class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)

        layout.add_widget(Label(text="Welcome to Wall-E", font_size=24, size_hint_y=None, height=50))

        manage_profiles_button = Button(text="Profile Manager", size_hint_y=None, height=50)
        manage_profiles_button.bind(on_press=self.go_to_profile_management)
        layout.add_widget(manage_profiles_button)

        seat_finder_button = Button(text="Seat Finder", size_hint_y=None, height=50)
        seat_finder_button.bind(on_press=self.go_to_seat_finder)
        layout.add_widget(seat_finder_button)

        # Adding the Email Template Manager button
        email_template_button = Button(text="Email Template Manager", size_hint_y=None, height=50)
        email_template_button.bind(on_press=self.go_to_email_template_manager)
        layout.add_widget(email_template_button)

        exit_button = Button(text="Exit", size_hint_y=None, height=50)
        exit_button.bind(on_press=self.exit_app)
        layout.add_widget(exit_button)

        self.add_widget(layout)

    def go_to_profile_management(self, instance):
        """Switch to the 'profile_management' screen."""
        self.manager.current = "profile_management"

    def go_to_seat_finder(self, instance):
        """Switch to the 'seat_finder' screen."""
        self.manager.current = "seat_finder"

    def go_to_email_template_manager(self, instance):
        """Switch to the 'email_template_manager' screen."""
        self.manager.current = "email_template_manager"

    def exit_app(self, instance):
        """Exit the app."""
        App.get_running_app().stop()


class ProfileApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(ProfileManagementScreen(name="profile_management"))
        sm.add_widget(CreateProfileScreen(name="create_profile"))
        sm.add_widget(ViewProfilesScreen(name="view_profiles"))
        sm.add_widget(EditProfileScreen(name="edit_profile"))
        sm.add_widget(SeatFinderScreen(name="seat_finder"))
        sm.add_widget(EmailTemplateScreen(name="email_template_manager"))
        sm.add_widget(ViewTemplateScreen(name="view_templates"))
        sm.add_widget(EmailTemplateScreen(name="edit_template"))
        self.updater = AutoUpdater(self)
        self.updater.check_for_updates()

        return sm

if __name__ == '__main__':
    ProfileApp().run()
