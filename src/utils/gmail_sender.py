import os
import base64
import json

from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API scope
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def authenticate_gmail_api():
    """Authenticate and return the Gmail API service."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret_659735247013-iflua8501cas916u3q56dvfbascbgv8u.apps.googleusercontent.com.json',
                SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    #{"token": "", "refresh_token": "", "token_uri": "", "client_id": "", "client_secret": "", "scopes": [""], "universe_domain": "", "account": "", "expiry": ""}
    service = build('gmail', 'v1', credentials=creds)
    return service

def create_message(sender, to, cc, subject, message_text):
    """Create MIME message with To and CC support, encoded for Gmail API."""
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    if cc:
        message['cc'] = cc
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw}

def send_alert_email(to_email, cc_emails, incident_json):
    """Send alert email with CC recipients."""
    service = authenticate_gmail_api()

    subject = "🚨 Helpdesk Incident Alert"
    message_text = f"An incident has been reported:\n\n{json.dumps(incident_json, indent=2)}"

    message = create_message(
        sender='me',
        to=to_email,
        cc=', '.join(cc_emails),
        subject=subject,
        message_text=message_text
    )

    sent = service.users().messages().send(userId='me', body=message).execute()
    print(f"✅ Message sent! ID: {sent['id']}")
import datetime
import os
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scope to manage calendar events and create Meet links
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def authenticate_calendar_api():
    """Authenticate and return the Google Calendar API service."""
    token_path = 'token_calendar.json'
#{"token": "", "refresh_token": "", "token_uri": "https://oauth2.googleapis.com/token", "client_id": "", "client_secret": "", "scopes": ["https://www.googleapis.com/auth/calendar.events"], "universe_domain": "googleapis.com", "account": "", "expiry": "2025-04-17T10:24:41.187644Z"}
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret_659735247013-iflua8501cas916u3q56dvfbascbgv8u.apps.googleusercontent.com.json',
                SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)
    return service


def create_crisis_meeting(event_summary, description, start_time, end_time, attendee_emails):
    """Create a Google Calendar event with a Meet link and send invites."""
    service = authenticate_calendar_api()

    event = {
        'summary': event_summary,
        'description': description,
        'start': {
            'dateTime': start_time,
            'timeZone': 'Africa/Casablanca',
        },
        'end': {
            'dateTime': end_time,
            'timeZone': 'Africa/Casablanca',
        },
        'attendees': [{'email': email} for email in attendee_emails],
        'conferenceData': {
            'createRequest': {
                'requestId': 'crisis-meeting-001',
                'conferenceSolutionKey': {
                    'type': 'hangoutsMeet'
                }
            }
        },
        'reminders': {
            'useDefault': True,
        }
    }

    event_result = service.events().insert(
        calendarId='primary',
        body=event,
        conferenceDataVersion=1,  
        sendUpdates='all'
    ).execute()

    print(f"✅ Event created: {event_result.get('htmlLink')}")
    print(f"📎 Google Meet link: {event_result['conferenceData']['entryPoints'][0]['uri']}")


# if __name__ == '__main__':
#     print("🚀 Creating crisis meeting...")

#     create_crisis_meeting(
#         event_summary="🚨 Crisis Meeting: Ticketing System Down",
#         description="Urgent crisis meeting to discuss resolution steps for the Casablanca station issue.",
#         start_time="2025-04-16T10:00:00",  # YYYY-MM-DDTHH:MM:SS
#         end_time="2025-04-16T11:00:00",
#         attendee_emails=[
#             "rhita.amouzigh2@gmail.com",
#             "salaharfi52@gmail.com",
#         ]
#     )


# # ---- Run a test ---
#     print("🚀 Script started")

#     incident = {
#         "priority": "High",
#         "contact": "ONCF Helpdesk",
#         "summary": "Ticketing system failure at Casablanca station."
#     }

#     # Main recipient
#     to = "rhita.amouzigh2@gmail.com"

#     # People in CC
#     cc = [
#         "salaharfi52@gmail.com",
#         "drakn3342@gmail.com"
#     ]

#     send_alert_email(to, cc, incident)
