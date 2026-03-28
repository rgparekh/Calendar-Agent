# Using the Google Calendar API create new calendar events, extract events by name, and delete events

import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

cal_event = {
  'summary': 'Flight to Chicago',
  'location': 'San Francisco International Airport, CA',
  'description': 'Traveling to Chicago to drop Jash off at UIUC',
  'start': {
    'dateTime': '2025-08-14T20:00:00-07:00',
    'timeZone': 'America/Los_Angeles',
  },
  'end': {
    'dateTime': '2025-08-15T05:45:00-07:00',
    'timeZone': 'America/Los_Angeles',
  },
  'recurrence': [
  ],
  'attendees': [
    {'email': 'rgparekh@hotmail.com'},
  ],
  'reminders': {
    'useDefault': False,
    'overrides': [
      {'method': 'email', 'minutes': 24 * 60},
      {'method': 'popup', 'minutes': 10},
    ],
  },
}

def create_event(credentials, calendar_id, cal_event):
  """Create a new calendar event"""

  try:
    service = build("calendar", "v3", credentials=credentials)

    event = service.events().insert(calendarId=calendar_id, body=cal_event).execute()
    print('Event created: %s' % (event.get('htmlLink')))
  except HttpError as error:
    print(f"An error occurred: {error}")

  return event

def get_event_by_name(credentials, calendar_id, event_name):
  """Get event(s) by name"""

  try:
    service = build("calendar", "v3", credentials=credentials)

    # Get upto 10 events in the future (starting now)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=now,
        maxResults=10,
        singleEvents=True,
        orderBy='startTime',
        q=event_name  # Filter by event name (summary)
    ).execute()
    events = events_result.get('items', [])
    print(f"Found {len(events)} events for {event_name}")

    for event in events:
      print(f"Event: {event['id']} - {event['summary']} - {event['start']['dateTime']} - {event['end']['dateTime']}")
    return events
  except HttpError as error:
    print(f"An error occurred: {error}")
    return None

def delete_event(credentials, calendar_id, event_id):
  """Delete an event"""
  try:
    service = build("calendar", "v3", credentials=credentials)
    service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    print(f"Deleted event: {event_id}")
    return True
  except HttpError as error:
    print(f"An error occurred: {error}")
    return False

def main():
  """Create a new calendar event"""

  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

    # Create the event
    new_event = create_event(creds, 'primary', cal_event)
    print(f"Successfully created event: {new_event.get('htmlLink')} ")

    # Get event(s) by name
    events_list = get_event_by_name(creds, 'primary', 'Flight to Chicago')
    print(f"Found {len(events_list)} events for {cal_event['summary']}")
    for event in events_list:
      print(f"Event: {event['summary']} - {event['start']['dateTime']} - {event['end']['dateTime']}")

    # Delete events in the events_list
    for event in events_list:
      if delete_event(creds, 'primary', event['id']):
        print(f"Deleted event: {event['id']} - {event['summary']}")
      else:
        print(f"Failed to delete event: {event['id']} - {event['summary']}")

if __name__ == "__main__":
  main()