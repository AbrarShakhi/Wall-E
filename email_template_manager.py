import os
import json
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput



# Default email template
DEFAULT_TEMPLATE = {
    'subject': "{course_code} Add Request",
    'body': """Hi Advisor,

I want to add {course_code} section {section}. 

Thanks for your time.

Sincerely Yours,
{student_name},
{student_id}"""
}


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
    return os.path.join(get_persistent_dir(), filename)


def initialize_default_template():
    """Ensure default template file exists."""
    default_path = get_file_path("default_email_template.json")
    if not os.path.exists(default_path):
        with open(default_path, 'w') as f:
            json.dump(DEFAULT_TEMPLATE, f, indent=4)


def load_template(template_type):
    """Load a specific template (default or edited)."""
    file_path = get_file_path(f"{template_type}_email_template.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return DEFAULT_TEMPLATE


def save_template(template, template_type):
    """Save a template as default or edited."""
    file_path = get_file_path(f"{template_type}_email_template.json")
    with open(file_path, 'w') as f:
        json.dump(template, f, indent=4)


def load_active_template():
    """Load the active template based on user selection."""
    settings_path = get_file_path("settings.json")
    if os.path.exists(settings_path):
        with open(settings_path, 'r') as f:
            settings = json.load(f)
        return load_template(settings.get("active", "default"))
    return load_template("default")


def set_active_template(template_type):
    """Set the active template (default or edited)."""
    settings_path = get_file_path("settings.json")
    with open(settings_path, 'w') as f:
        json.dump({"active": template_type}, f)


class ViewTemplateScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", padding=20, spacing=10)

        self.subject_label = Label(text="Subject: ", size_hint_y=None, height=50, font_size=16, halign="center")
        layout.add_widget(self.subject_label)

        self.body_input = TextInput(text="", readonly=True, size_hint_y=0.8, background_color=(0.2, 0.2, 0.2, 1),
                                    foreground_color=(1, 1, 1, 1), font_size=16, halign="left", multiline=True)
        layout.add_widget(self.body_input)

        back_button = Button(text="Back", size_hint_y=None, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, 'current', 'home'))
        layout.add_widget(back_button)

        self.add_widget(layout)

    def on_enter(self):
        active_template = load_active_template()
        self.subject_label.text = f"Subject: {active_template['subject']}"
        self.body_input.text = active_template['body']


class EmailTemplateManagerScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)

        view_button = Button(text="View Templates", size_hint_y=None, height=50)
        view_button.bind(on_press=lambda x: setattr(self.manager, 'current', 'view_templates'))
        layout.add_widget(view_button)

        edit_button = Button(text="Edit Template", size_hint_y=None, height=50)
        edit_button.bind(on_press=lambda x: setattr(self.manager, 'current', 'edit_template'))
        layout.add_widget(edit_button)

        self.add_widget(layout)


class EmailTemplateScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)

        self.subject_input = TextInput(size_hint_y=None, height=50, multiline=False)
        layout.add_widget(Label(text="Subject:"))
        layout.add_widget(self.subject_input)

        self.body_input = TextInput(size_hint_y=None, height=200, multiline=True)
        layout.add_widget(Label(text="Body:"))
        layout.add_widget(self.body_input)

        # Add message label
        self.message_label = Label(text="", color=(1, 0, 0, 1), size_hint_y=None, height=30)
        layout.add_widget(self.message_label)

        save_button = Button(text="Save Edited Email", size_hint_y=None, height=50)
        save_button.bind(on_press=self.save_edited_email)
        layout.add_widget(save_button)

        self.set_default_button = Button(text="Use Default Template", size_hint_y=None, height=50)
        self.set_default_button.bind(on_press=lambda x: self.update_active_template("default"))
        layout.add_widget(self.set_default_button)

        self.set_edited_button = Button(text="Use Edited Template", size_hint_y=None, height=50)
        self.set_edited_button.bind(on_press=lambda x: self.update_active_template("edited"))
        layout.add_widget(self.set_edited_button)

        back_button = Button(text="Back", size_hint_y=None, height=50)
        back_button.bind(on_press=lambda x: setattr(self.manager, 'current', 'home'))
        layout.add_widget(back_button)

        self.add_widget(layout)

    def update_active_template(self, template_type):
        set_active_template(template_type)
        self.set_default_button.disabled = template_type == "default"
        self.set_edited_button.disabled = template_type == "edited"

    def on_enter(self):
        active_template = load_active_template()
        self.subject_input.text = active_template['subject']
        self.body_input.text = active_template['body']
        self.message_label.text = ""  # Clear any previous message

    def save_edited_email(self, instance):
        edited_email = {'subject': self.subject_input.text.strip(), 'body': self.body_input.text.strip()}
        save_template(edited_email, "edited")
        self.message_label.text = "Template saved successfully!"


class EmailTemplateApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(EmailTemplateManagerScreen(name="email_template_manager"))
        sm.add_widget(ViewTemplateScreen(name="view_templates"))
        sm.add_widget(EmailTemplateScreen(name="edit_template"))
        return sm


if __name__ == '__main__':
    initialize_default_template()
    EmailTemplateApp().run()
