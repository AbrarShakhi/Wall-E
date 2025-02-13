import os
import pickle
import base64
import json
import sys
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart




# OAuth 2.0 Scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# Default email template (fallback if files are missing)
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
    """Get absolute path to resource, works for dev and PyInstaller."""
    if getattr(sys, 'frozen', False):  # Check if the app is running as a built executable
        base_path = sys._MEIPASS  # Use the temporary directory created by PyInstaller
    else:
        base_path = os.path.abspath(".")  # Use the current working directory in development
    return os.path.join(base_path, relative_path)

def get_persistent_dir():
    """Get platform-specific persistent directory for storing data (aligned with email_template_manager)."""
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

def load_template(template_type):
    """Load a specific template (default or edited) from persistent storage."""
    file_path = get_file_path(f"{template_type}_email_template.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return DEFAULT_TEMPLATE  # Fallback to default if file is missing/corrupt

def load_active_template():
    """Load the active template based on settings.json (aligned with email_template_manager)."""
    settings_path = get_file_path("settings.json")
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r') as f:
                settings = json.load(f)
            return load_template(settings.get("active", "default"))
        except (json.JSONDecodeError, IOError):
            pass
    return load_template("default")  # Fallback to default template

def get_persistent_token_path(student_email):
    """Get a persistent path for storing the token file, using the same directory as email_template_manager."""
    app_dir = get_persistent_dir()  # Use the same persistent directory as email_template_manager
    return os.path.join(app_dir, f"token_{student_email}.pickle")

def get_credentials(student_email):
    """Get OAuth 2.0 credentials for a specific student email."""
    creds = None
    token_path = get_persistent_token_path(student_email)  # Use persistent token path

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
    try:
        # Load the active email template
        template = load_active_template()

        # Format subject and body with placeholders
        subject = template['subject'].format(course_code=course_code, section=section)
        body = template['body'].format(
            course_code=course_code,
            section=section,
            student_name=student_name,
            student_id=student_id
        )

        # Create the email message
        message = MIMEMultipart()
        message['From'] = student_email
        message['To'] = advisor_email
        message['Subject'] = subject

        # Attach the email body
        message.attach(MIMEText(body, 'plain'))

        # Encode the message in base64
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

        # Get OAuth 2.0 credentials for the student's email
        creds = get_credentials(student_email)

        # Build the Gmail API service
        service = build('gmail', 'v1', credentials=creds)

        # Send the email
        service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()

    except Exception as e:
        print(f"Error: {e}")