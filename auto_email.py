import os
import pickle
import base64
import json
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart





SCOPES = ['https://www.googleapis.com/auth/gmail.send']

DEFAULT_TEMPLATE = {
    'subject': "{course_code} Add Request",
    'body': """Hi Advisor,

I want to add {course_code} section {section}. 

Thanks for your time.

Sincerely Yours,
{student_name},
{student_id}"""
}


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller"""
    if getattr(sys, 'frozen', False):  # Check if running in a PyInstaller bundle
        base_path = sys._MEIPASS  # PyInstaller creates this temp folder for bundled files
    else:
        base_path = os.path.abspath(".")  # Use the current directory in development
    return os.path.join(base_path, relative_path)


def load_templates():
    """
    Loads all templates from the email_templates.json file.
    If the file is missing or invalid, it falls back to the default template.
    """
    try:
        templates_path = get_resource_path("email_templates.json")
        with open(templates_path, 'r') as file:
            templates = json.load(file)
            if not isinstance(templates, dict):
                raise ValueError("Invalid template format.")
            return templates
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return {'default': DEFAULT_TEMPLATE}


def load_active_template():
    """
    Loads the currently active template from email_templates.json.
    If not set, it falls back to the default template.
    """
    templates = load_templates()
    return templates.get('active', templates.get('default', DEFAULT_TEMPLATE))


def get_credentials():
    """Get OAuth 2.0 credentials."""
    creds = None
    token_path = get_resource_path("token.pickle")

    # Load token if it exists
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, prompt the user to log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_secrets_path = get_resource_path("walle_desktop_client.json")
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for future use
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    return creds


def send_email(student_name, student_email, advisor_email, course_code, section, student_id):
    """
    Sends an email to the advisor with a request to add the student to a specific course section.

    Args:
        student_name (str): The name of the student.
        student_email (str): The student's email address.
        advisor_email (str): The advisor's email address.
        course_code (str): The course code (e.g., CSE246).
        section (str): The section of the course (e.g., A).
        student_id (str): The student ID.
    """

    template = load_active_template()


    subject = template['subject'].format(course_code=course_code, section=section)
    body = template['body'].format(
        course_code=course_code,
        section=section,
        student_name=student_name,
        student_id=student_id
    )


    message = MIMEMultipart()
    message['From'] = student_email
    message['To'] = advisor_email
    message['Subject'] = subject

    message.attach(MIMEText(body, 'plain'))

    # Encode the message in base64
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

    try:
        # Get OAuth 2.0 credentials
        creds = get_credentials()

        # Build the Gmail API service
        service = build('gmail', 'v1', credentials=creds)

        # Send the email
        service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()

    except Exception as e:
        print(f"Error: {e}")