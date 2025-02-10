from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
import json


DEFAULT_TEMPLATE = {
    'subject': "{course_code} Add Request",
    'body': """Hi Advisor,

I want to add {course_code} section {section}. 

Thanks for your time.

Sincerely Yours,
{student_name},
{student_id}"""
}


def load_templates():
    try:
        with open('email_templates.json', 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'default': DEFAULT_TEMPLATE}


def save_templates(templates):
    try:
        with open('email_templates.json', 'w') as file:
            json.dump(templates, file, indent=4)
    except Exception as e:
        print(f"Error saving templates: {e}")


def load_active_template():
    try:
        templates = load_templates()
        active_template = templates.get('active', DEFAULT_TEMPLATE)
        return active_template
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading active template: {e}")
        return DEFAULT_TEMPLATE


def save_active_template(template):
    try:
        templates = load_templates()
        templates['active'] = template
        save_templates(templates)
    except Exception as e:
        print(f"Error saving active template: {e}")


class ViewTemplateScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", padding=20, spacing=10)

        self.subject_label = Label(
            text="Subject: ",
            size_hint_y=None,
            height=50,
            font_size=16,
            halign="center",
        )
        layout.add_widget(self.subject_label)

        self.body_input = TextInput(
            text="",
            readonly=True,
            size_hint_y=0.8,
            background_color=(0.2, 0.2, 0.2, 1),
            foreground_color=(1, 1, 1, 1),
            font_size=16,
            halign="left",
            multiline=True,
        )
        layout.add_widget(self.body_input)

    def on_enter(self):
        active_template = load_active_template()
        self.subject_label.text = f"Subject: {active_template['subject']}"
        self.body_input.text = active_template['body']


class EmailTemplateScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)

        self.subject_input = TextInput(size_hint_y=None, height=50, multiline=False, background_color=(1, 1, 1, 1), foreground_color=(0, 0, 0, 1))
        layout.add_widget(Label(text="Subject:"))
        layout.add_widget(self.subject_input)

        self.body_input = TextInput(size_hint_y=None, height=200, multiline=True, background_color=(1, 1, 1, 1), foreground_color=(0, 0, 0, 1))
        layout.add_widget(Label(text="Body:"))
        layout.add_widget(self.body_input)

        # Add Save Edited Email button
        save_button = Button(text="Save Edited Email", size_hint_y=None, height=50)
        save_button.bind(on_press=self.save_edited_email)
        layout.add_widget(save_button)

        # Add Set Edited Template as Active button
        self.set_active_button = Button(text="Set Edited Template as Active", size_hint_y=None, height=50, background_color=(1, 1, 1, 1))
        self.set_active_button.bind(on_press=self.set_as_active)
        layout.add_widget(self.set_active_button)

        # Add Set Default Template as Active button
        self.set_default_button = Button(text="Set Default Template as Active", size_hint_y=None, height=50, background_color=(0.5, 0.5, 0.5, 1))
        self.set_default_button.bind(on_press=self.set_default_as_active)
        layout.add_widget(self.set_default_button)

        # Add Go Back button
        go_back_button = Button(text="Back to Main Menu", size_hint_y=None, height=50)
        go_back_button.bind(on_press=self.go_back)
        layout.add_widget(go_back_button)

        self.add_widget(layout)

    def on_enter(self):
        # Load templates and determine the active one
        templates = load_templates()
        active_template = templates.get("active", DEFAULT_TEMPLATE)

        # Set the text fields to display the default template (if no active template is set)
        default_template = templates.get("default", DEFAULT_TEMPLATE)
        self.subject_input.text = default_template['subject']
        self.body_input.text = default_template['body']

        # Update button appearances based on the active template
        if active_template == default_template:
            self.set_active_button.background_color = (1, 1, 1, 1)  # Normal
            self.set_default_button.background_color = (0.5, 0.5, 0.5, 1)  # Grayed out
        else:
            self.set_active_button.background_color = (0.5, 0.5, 0.5, 1)  # Grayed out
            self.set_default_button.background_color = (1, 1, 1, 1)  # Normal

    def save_edited_email(self, instance):
        edited_email = {
            'subject': self.subject_input.text.strip(),
            'body': self.body_input.text.strip()
        }
        # Save the edited template and set it as the active template
        templates = load_templates()
        templates['active'] = edited_email
        save_templates(templates)

    def set_as_active(self, instance):
        # Set the edited template as active
        edited_email = {
            'subject': self.subject_input.text.strip(),
            'body': self.body_input.text.strip()
        }
        templates = load_templates()
        templates['active'] = edited_email
        save_templates(templates)

        # Update button appearances
        self.set_active_button.background_color = (0.5, 0.5, 0.5, 1)  # Grayed out
        self.set_default_button.background_color = (1, 1, 1, 1)  # Normal

    def set_default_as_active(self, instance):
        # Set the default template as active
        templates = load_templates()
        templates['active'] = templates.get('default', DEFAULT_TEMPLATE)
        save_templates(templates)

        # Update button appearances
        self.set_active_button.background_color = (1, 1, 1, 1)  # Normal
        self.set_default_button.background_color = (0.5, 0.5, 0.5, 1)  # Grayed out

    def go_back(self, instance):
        self.manager.current = 'home'


class EmailTemplateManagerScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical", spacing=10, padding=10)

        view_button = Button(text="View Templates", size_hint_y=None, height=50)
        view_button.bind(on_press=self.view_templates)
        layout.add_widget(view_button)

        edit_button = Button(text="Edit Template", size_hint_y=None, height=50)
        edit_button.bind(on_press=self.edit_templates)
        layout.add_widget(edit_button)

        self.add_widget(layout)

    def view_templates(self, instance):
        self.manager.current = 'view_templates'

    def edit_templates(self, instance):
        self.manager.current = 'edit_template'


class EmailTemplateApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(EmailTemplateManagerScreen(name="email_template_manager"))
        sm.add_widget(ViewTemplateScreen(name="view_templates"))
        sm.add_widget(EmailTemplateScreen(name="edit_template"))
        return sm


if __name__ == '__main__':
    EmailTemplateApp().run()
