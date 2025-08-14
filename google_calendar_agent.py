# Agentic workflow to manage Google calendar events

import os
import json
import logging

# import google.generativeai as genai
from google import genai
from google.genai import types
from google.genai.types import Tool
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
model_name = "gemini-2.5-flash"

# --------------------------------------------------------------
# Step 1: Define the data models for each stage
# --------------------------------------------------------------

class KeyValuePair(BaseModel):
    key: str = Field(description="Key of the key-value pair")
    value: str = Field(description="Value of the key-value pair")

class EmailAddress(BaseModel):
    email: str = Field(description="Email address of the attendee")

class EventDateTime(BaseModel):
    """
    Represents the date and time of a Google Calendar event.
    """
    dateTime: Optional[datetime] = Field(
        None,
        description=(
            "The time, as a combined date-time value (formatted according to RFC3339). "
            "A time zone offset is required unless a time zone is explicitly specified in timeZone."
        ),
    )
    timeZone: Optional[str] = Field(
        None,
        description=(
            "The time zone in which the time is specified (formatted as an IANA Time Zone Database name, e.g. 'Europe/Zurich'). "
            "For recurring events this field is required and specifies the time zone in which the recurrence is expanded. "
            "For single events this field is optional and indicates a custom time zone for the event start/end."
        ),
    ) 

class CalendarEvent(BaseModel):
  """Using the event description determine if it a calendar event"""
  description: str = Field(description="Text describing the event ")
  is_calendar_event: bool = Field(description="Whether this text describes a calendar event") 
  confidence_score: float = Field(description="Confidence score between 0 and 1")

class CalendarRequestType(BaseModel):
  """Determine if the Calendar Request is for a new event, modification of an existing event, or deletion of an existing event"""
  description: str = Field(description="Text describing the event ")
  event_type: Literal["new_event", "modify_event", "delete_event", "other"] = Field(
    description="Type of calendar event - new_event, modify_event, delete_event, other"
  )
  confidence_score: float = Field(description="Confidence score between 0 and 1")

class NewEventDetails(BaseModel):
  """Details for creating a new calendar event"""
  summary: str = Field(description="Summary of the event")
  location: str = Field(description="Location of the event")
  description: str = Field(description="Description of the event")
  start: EventDateTime = Field(description="Start time object with fields dateTime and timeZone")
  end: EventDateTime = Field(description="End time object with fields dateTime and timeZone")
  recurrence: list[str] = Field(default=[], description="Recurrence rules")
  attendees: list[EmailAddress] = Field(
    description="List of attendee objects with fields email"
  )

# TODO: Determine if this data model is needed
class ModifyEventDetails(BaseModel):
  """Details for creating a new calendar event"""
  summary: Optional[str] = Field(default=None, description="Summary of the event")
  location: Optional[str] = Field(description="Location of the event")
  description: Optional[str] = Field(description="Description of the event")
  start: Optional[EventDateTime] = Field(description="Start time object with fields dateTime and timeZone")
  end: Optional[EventDateTime] = Field(default=None, description="End time object with fields dateTime and timeZone")
  recurrence: Optional[list[str]] = Field(default=[], description="Recurrence rules")
  attendees: Optional[list[EmailAddress]] = Field(
    description="List of attendee objects with fields email"
  )

class EventsListParameters(BaseModel):
  """Parameters for listing events"""
  calendarId: str = Field(description="Calendar ID")
  timeMin: Optional[datetime] = Field(default=None, description="Start time")
  timeMax: Optional[datetime] = Field(default=None, description="End time")
  singleEvents: bool = Field(default=False, description="Whether to return single events")
  orderBy: Optional[str] = Field(default=None, description="Order by") 
  q: Optional[str] = Field(default=None, description="Query")

class CalendarResponse(BaseModel):
    """Final response format"""

    success: bool = Field(description="Whether the operation was successful")
    message: str = Field(description="User-friendly response message")
    calendar_link: Optional[str] = Field(description="Calendar link if applicable")

# Invoke the GenAI (Gemini) model and return its response
def run_model(model_name, contents, config):    
    response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=config
    )
    return response

# --------------------------------------------------------------
# Step 2: Define the functions to process the calendar events
# --------------------------------------------------------------

# Check if the user's description is a calendar event
def check_if_calendar_event(description: str) -> CalendarEvent:
  """Check if the description is a calendar event"""
  logger.info("Checking if the description is a calendar event")
  logger.debug(f"Input text: {description}")
  
  config = types.GenerateContentConfig(
    system_instruction = f"""You are a calendar event manager. 
      Determine if the incoming request is for a calendar event or not.
      Return a boolean response along with a confidence score between 0 and 1.
    """,
    response_mime_type = "application/json",
    response_schema = CalendarEvent
  )
  
  contents = [
    types.Content(
      role="user", parts=[types.Part(text=description)]
    )
  ]
  
  response = run_model(model_name, contents, config)
  response_json = json.loads(response.candidates[0].content.parts[0].text)

  logger.info(
    f"Extraction complete - Is calendar event: {response_json["is_calendar_event"]}, Confidence: {response_json["confidence_score"]:.2f}"
  )

  return response_json  

# Determine the type of calendar request - new_event, modify_event, delete_event, other
def determine_calendar_request_type(description: str) -> CalendarRequestType:
  """Determine the type of calendar request: new_event, modify_event, delete_event, other"""
  logger.info("Determining the type of calendar request")
  logger.debug(f"Input text: {description}")
  
  config = types.GenerateContentConfig(
    system_instruction = f"""You are a calendar event manager. 
      Determine if the incoming request is a calendar event request.
      If so, determine the type of request: new_event, modify_event, delete_event, other.
      In each case, extract the description of the event without the name of the action to take.
      Return the type of the request along with a confidence score between 0 and 1.
    """,
    response_mime_type = "application/json",
    response_schema = CalendarRequestType
  )
  
  contents = [
    types.Content(
      role="user", parts=[types.Part(text=description)]
    )
  ]

  response = run_model(model_name, contents, config)
  response_json = json.loads(response.candidates[0].content.parts[0].text)

  logger.info(
    f"Extraction complete - Is calendar event: {response_json["event_type"]}, Confidence: {response_json["confidence_score"]:.2f}"
  )

  return response_json

# Get a list of calendar events given the user's description
def get_calendar_events(credentials, calendar_id, description: str) -> CalendarResponse:
  """Get a list of calendar events"""
  logger.info("Getting a list of calendar events")
  logger.debug(f"Input text: {description}")
  
  today = datetime.now()
  date_context = f"Today is {today.strftime('%A, %B %d, %Y')}."

  config = types.GenerateContentConfig(
        system_instruction = f"""You are an expert Google calendar manager. 
        Given the {date_context} build a JSON object to fetch the Google calendar events referenced to in the description.
        If no start date is specified then use today at 12:00 AM as timeMin. 
        Do not create a default timeMax. Only populate timeMax if the description specifies an end date.
        The q field should contain the text from the description that would be in the summary of the Google calendar event. 
        Return ONLY the relevant fields from the following list in JSON format:
        - calendarId: string
        - timeMin: datetime
        - timeMax: datetime
        - singleEvents: bool
        - orderBy: string
        - q: string
        Do not include any other fields or properties.
        """,
        response_mime_type = "application/json",
        response_schema = EventsListParameters
    )

  contents = [
    types.Content(
      role="user", parts=[types.Part(text=description)]
    )
  ] 

  response = run_model(model_name, contents, config)
  response_json = json.loads(response.candidates[0].content.parts[0].text)
  logger.info(f"Events List Parameters: {response_json}")

  return response_json

# Create a new calendar event
def create_new_event(credentials, calendar_id, description: str) -> CalendarResponse:
  """Create a new calendar event"""
  logger.info("Creating a new calendar event")
  logger.debug(f"Input text: {description}")

  today = datetime.now()
  date_context = f"Today is {today.strftime('%A, %B %d, %Y')}."

  config = types.GenerateContentConfig(
        system_instruction = f"""You are a calendar event manager. 
        Given the {date_context} create a new calendar event based on the description.
        Return ONLY these exact fields in JSON format:
        - summary: string
        - location: string  
        - description: string
        - start: object with dateTime and timeZone
        - end: object with dateTime and timeZone
        - recurrence: array of strings
        - attendees: array of objects with email field
        - reminders: object with useDefault and overrides
        Do not include any other fields or properties.
        """,
        response_mime_type = "application/json",
        response_schema = NewEventDetails
    )

  contents = [
    types.Content(
      role="user", parts=[types.Part(text=description)]
    )
  ] 

  response = run_model(model_name, contents, config)
  response_json = json.loads(response.candidates[0].content.parts[0].text)

  logger.info(f"New calendar event: {response_json}")

  # Use the Google Calendar API to create the event
  try: 
    service = build("calendar", "v3", credentials=credentials)
    event = service.events().insert(calendarId=calendar_id, body=response_json).execute()
    logger.info(f"New calendar event created: {event.get('htmlLink')}")
  except HttpError as error:
    logger.error(f"An error occurred: {error}")
    return CalendarResponse(
      success=False,
      message=f"An error occurred: {error}",
      calendar_link=None
    )

  # Generate response
  return CalendarResponse(
    success=True,
    message=f"New calendar event '{response_json["summary"]}' created for {response_json["start"]["dateTime"]} with {response_json["attendees"]}",
    calendar_link=event.get('htmlLink')
  )

# Delete an existing calendar event identified by its ID
def delete_event_by_id(credentials, calendar_id, event_id: str) -> CalendarResponse:
  """Delete an existing calendar event by ID"""
  logger.info("Deleting an existing calendar event by ID")
  logger.info(f"Input text: {event_id}")
  
  try:
    service = build("calendar", "v3", credentials=credentials)
    service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    logger.info(f"Event {event_id} deleted")
  except HttpError as error:
    logger.error(f"An error occurred: {error}")
    return CalendarResponse(
      success=False,
      message=f"An error occurred: {error}",
      calendar_link=None
    )
  
  # Generate response
  return CalendarResponse(
    success=True,
    message=f"Event {event_id} deleted",
    calendar_link=None
  )
  
# Delete one or more calendar events given the user's description
def delete_event(credentials, calendar_id, description: str, all: bool = False) -> CalendarResponse:
  """Delete an existing calendar event"""
  logger.info("Deleting an existing calendar event")
  logger.info(f"Input text: {description}")

  # Get a list of events that match the description
  # Note: Only future events are searched while fetching the list of events

  # Get the events list parameters
  events_list_parameters = get_calendar_events(credentials, calendar_id, description)
  logger.info(f"Events List Parameters: {events_list_parameters}")

  # Get the events
  try:
    service = build("calendar", "v3", credentials=credentials)
    events_result = service.events().list(
      calendarId=events_list_parameters["calendarId"], 
      timeMin=events_list_parameters["timeMin"],
      timeMax=events_list_parameters["timeMax"],
      singleEvents=events_list_parameters["singleEvents"],
      orderBy=events_list_parameters["orderBy"],
      q=events_list_parameters["q"]
    ).execute()
    events = events_result.get('items', [])
    logger.info(f"Found {len(events)} event(s)")
  except HttpError as error:
    logger.error(f"An error occurred: {error}")
    return CalendarResponse(
      success=False,
      message=f"An error occurred: {error}",
      calendar_link=None
    )
  
  # Confirm that the user wants to delete the event(s)
  if (len(events) > 0):
    print(f"About to delete the following {len(events)} event(s):")
    for event in events:
      print(f"Event {event['id']}: {event['summary']} from {event['start']['dateTime']} to {event['end']['dateTime']}")
    print("Are you sure you want to delete these events? (y/n)")
    confirm = input()
    if confirm.lower() != 'y':
      return CalendarResponse(
        success=False,
        message="User did not confirm deletion of events",
        calendar_link=None
      ) 
  
  # Delete the events
  calResponseMessage = ""

  if all:
    for event in events:
      calResponse = delete_event_by_id(credentials, calendar_id, event['id'])
      if calResponse.success:
        calResponseMessage += f"Event {event['id']}: {event['summary']} from {event['start']['dateTime']} to {event['end']['dateTime']} deleted\n"
      else:
         calResponseMessage += f"Event {event['id']}: deletion error {calResponse.message}\n"
  else:
    calResponse = delete_event_by_id(credentials, calendar_id, events[0]['id'])
    if calResponse.success:
      calResponseMessage += f"Event {event['id']}: {event['summary']} from {event['start']['dateTime']} to {event['end']['dateTime']} deleted\n"
    else:
      calResponseMessage += f"Event {event['id']}: deletion error {calResponse.message}\n"

  return CalendarResponse(
    success=True,
    message=calResponseMessage,
    calendar_link=None
  )

# Modify (update)an existing calendar event given the user's description
def modify_event(credentials, calendar_id, description: str) -> CalendarResponse:
  """Modify an existing calendar event"""
  logger.info("Modifying an existing calendar event")
  logger.debug(f"Input text: {description}")

  # Get the events list parameters
  events_list_parameters = get_calendar_events(credentials, calendar_id, description)
  logger.info(f"Events List Parameters: {events_list_parameters}")
  event_calendarId = events_list_parameters["calendarId"]
  event_timeMin = events_list_parameters["timeMin"] if "timeMin" in events_list_parameters else None
  event_timeMax = events_list_parameters["timeMax"] if "timeMax" in events_list_parameters else None
  event_singleEvents = events_list_parameters["singleEvents"] if "singleEvents" in events_list_parameters else False
  event_orderBy = events_list_parameters["orderBy"] if "orderBy" in events_list_parameters else None
  event_q = events_list_parameters["q"] if "q" in events_list_parameters else None

  # Get a list of events that match the description of the event to modify
  try:
    service = build("calendar", "v3", credentials=credentials)
    events_result = service.events().list(
      calendarId=event_calendarId, 
      timeMin=event_timeMin,
      timeMax=event_timeMax,
      singleEvents=event_singleEvents,
      orderBy=event_orderBy,
      q=event_q
    ).execute()
    events = events_result.get('items', [])
    logger.info(f"Found {len(events)} event(s)")
    if len(events) == 0:
      return CalendarResponse(
        success=False,
        message=f"ERROR: No events found for the description '{description}'",
        calendar_link=None
      )
    elif len(events) > 1:
      return CalendarResponse(
        success=False,
        message=f"ERROR: Multiple events found for the description '{description}'. Please make the description more specific.",
        calendar_link=None
      )
    else:
      event = events[0]
      logger.info(f"Event to modify: {event['id']}: {event['summary']} from {event['start']['dateTime']} to {event['end']['dateTime']}")
  except HttpError as error:
    logger.error(f"An error occurred: {error}")
    return CalendarResponse(
      success=False,
      message=f"An error occurred: {error}",
      calendar_link=None
    )

  # Determine the event update parameters given the user'sdescription and the event object
  today = datetime.now()
  date_context = f"Today is {today.strftime('%A, %B %d, %Y')}."

  config = types.GenerateContentConfig(
        system_instruction = f"""You are a Google Calendar manager well versed in the Google Calendar API. 
        The user is requesting a modification to an existing calendar event '{event}' given that the date
        context is '{date_context}'. Starting with the current calendar event, create a JSON object (whose fields
        are below) to modify the calendar event based on the description provided by the user. Update ONLY the fields
        that are to be modified. 
        Return ONLY the fields that are to be modified in JSON format:
        - summary: string
        - location: string  
        - description: string
        - start: object with dateTime and timeZone
        - end: object with dateTime and timeZone
        - recurrence: array of strings
        - attendees: array of objects with email field
        - reminders: object with useDefault and overrides
        Do not include any other fields or properties.
        """,
        response_mime_type = "application/json",
        response_schema = NewEventDetails
    )

  contents = [
    types.Content(
      role="user", parts=[types.Part(text=description)]
    )
  ] 

  response = run_model(model_name, contents, config)
  response_json = json.loads(response.candidates[0].content.parts[0].text)

  logger.info(f"Update calendar event: {response_json}")

  # Modify the event
  try:
    service = build("calendar", "v3", credentials=credentials)
    event = service.events().patch(calendarId=calendar_id, eventId=event['id'], body=response_json).execute()
    logger.info(f"Event {event['id']} successfully modified")
  except HttpError as error:
    logger.error(f"An error occurred while modifying the event ({event['id']}): {error}")
    return CalendarResponse(
      success=False,
      message=f"An error occurred while modifying the event ({event['id']}): {error}",
      calendar_link=None
    )

  # Return the response
  return CalendarResponse(
    success=True,
    message=f"Event {events[0]['id']}: {events[0]['summary']} from {events[0]['start']['dateTime']} to {events[0]['end']['dateTime']} modified",
    calendar_link=None
  )

# ---------------------------------------------------------------------------------
# Step 3: Define the function to process the calendar request provided by the user
# ---------------------------------------------------------------------------------

def process_calendar_request(credentials, calendar_id, user_input: str) -> Optional[CalendarResponse]:
  """Process an incoming calendar request"""
  logger.info("Processing calendar request {user_input}")

  # Check if the request is a calendar event or not
  is_calendar_event = check_if_calendar_event(user_input)

  if is_calendar_event["is_calendar_event"] and is_calendar_event["confidence_score"] > 0.7:
    calendar_request_type = determine_calendar_request_type(user_input)
  else:
    logger.warning("Calendar request type not supported")
    return None

  logger.info(f"Calendar request type: {calendar_request_type}")

  if (calendar_request_type["event_type"] == "new_event" and calendar_request_type["confidence_score"] > 0.7):
    return create_new_event(credentials, calendar_id, calendar_request_type["description"])
  elif (calendar_request_type["event_type"] == "modify_event" and calendar_request_type["confidence_score"] > 0.7):
    return modify_event(credentials, calendar_id, calendar_request_type["description"])
  elif (calendar_request_type["event_type"] == "delete_event" and calendar_request_type["confidence_score"] > 0.7):
    return delete_event(credentials, calendar_id, calendar_request_type["description"])
  else:
    logger.warning("Calendar request type not supported")
    return None
  
# --------------------------------------------------------------
# Step 4: Define the main function to run the calendar agent
# --------------------------------------------------------------

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

    # Prompt user for event description
    print("\n=== Google Calendar Agent===")
    print("Please describe the Google calendar event you want to the agent to create, modify, or delete.")
    print("Example: 'Schedule a meeting with John (john@email.com) tomorrow at 2 PM for 1 hour'")
    print("Type 'quit' to exit.\n")
    
    while True:
        event_description = input("Enter event description: ").strip()
        
        if event_description.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
            
        if not event_description:
            print("Please enter a valid event description.")
            continue
            
        print(f"\nProcessing: {event_description}")
        result = process_calendar_request(creds, 'primary', event_description)
        
        if result and result.success:
            print(f"✅ Successfully executed event: {result.message}")
        else:
            print("❌ Failed to execute event: {result.message} Please try again with a clearer description.")
        
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
  main()