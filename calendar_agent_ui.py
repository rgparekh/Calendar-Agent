# Simple Streamlit UI for Google Calendar Agent

import streamlit as st
import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

# Import calendar agent functions
from google_calendar_agent import (
    process_calendar_request,
    check_if_calendar_event,
    determine_calendar_request_type,
    get_calendar_events,
    get_tasks,
    create_new_event,
    create_task,
    modify_event,
    modify_task,
    delete_event,
    delete_task,
)

# Google Calendar / Tasks authentication imports
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OAuth scopes — must match google_calendar_agent.py
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
]

def get_google_credentials():
    """Get or create Google Calendar/Tasks credentials.

    If the saved refresh token is revoked or invalid (invalid_grant), we remove
    token.json and run the browser flow again instead of failing permanently.
    """
    creds = None
    force_consent_prompt = False

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        except RefreshError:
            # Revoked refresh token, wrong OAuth client, or stale token file.
            force_consent_prompt = True
            creds = None
            try:
                os.remove("token.json")
            except OSError:
                pass

    if not creds or not creds.valid:
        if not os.path.exists("credentials.json"):
            st.error("❌ credentials.json file not found. Please download it from Google Cloud Console.")
            st.stop()

        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        oauth_kwargs = {"port": 0, "access_type": "offline"}
        if force_consent_prompt:
            oauth_kwargs["prompt"] = "consent"
        creds = flow.run_local_server(**oauth_kwargs)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds

def main():
    st.set_page_config(
        page_title="Google Calendar Agent",
        page_icon="📅",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom CSS for better styling
    st.markdown("""
    <style>
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

    # Sidebar for navigation
    st.sidebar.title("Navigation")

    # Initialize page in session state
    if "page" not in st.session_state:
        st.session_state.page = "🏠 Home"

    pages = ["🏠 Home", "➕ Create", "🔍 Search", "✏️ Modify", "🗑️ Delete", "⚙️ Settings"]

    page = st.sidebar.selectbox(
        "Choose an action:",
        pages,
        index=pages.index(st.session_state.page)
    )

    # Update session state when sidebar changes
    if page != st.session_state.page:
        st.session_state.page = page
        st.rerun()

    # Check API key
    if not os.environ.get("GOOGLE_API_KEY"):
        st.error("❌ GOOGLE_API_KEY environment variable not set!")
        st.info("Please set your Google API key:")
        api_key = st.text_input("Enter your Google API Key:", type="password")
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
            st.success("✅ API key set successfully!")
            st.rerun()
        st.stop()

    # Get credentials
    try:
        creds = get_google_credentials()
        st.sidebar.success("✅ Authenticated with Google Calendar")
    except Exception as e:
        st.error(f"❌ Authentication failed: {e}")
        st.stop()

    # Fetch calendar owner name once and cache in session state
    if "calendar_owner_name" not in st.session_state:
        try:
            service = build("calendar", "v3", credentials=creds)
            calendar_info = service.calendars().get(calendarId="primary").execute()
            st.session_state.calendar_owner_name = calendar_info.get("summary", "")
        except Exception:
            st.session_state.calendar_owner_name = ""

    # Main content based on selected page
    if page == "🏠 Home":
        show_home_page(creds, st.session_state.calendar_owner_name)

    elif page == "➕ Create":
        show_create_page(creds)

    elif page == "🔍 Search":
        show_search_page(creds)

    elif page == "✏️ Modify":
        show_modify_page(creds)

    elif page == "🗑️ Delete":
        show_delete_page(creds)

    elif page == "⚙️ Settings":
        show_settings_page()

def get_upcoming_events(creds, max_results=5):
    """Fetch the next upcoming events from Google Calendar."""
    try:
        service = build("calendar", "v3", credentials=creds)
        now = datetime.now(timezone.utc).isoformat()
        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        return events_result.get("items", []), None
    except HttpError as error:
        return [], str(error)


def show_home_page(creds, owner_name=""):
    """Display the home page with overview and quick actions."""
    greeting = f"Welcome to Your Calendar Agent, {owner_name}" if owner_name else "Welcome to Your Calendar Agent"
    st.markdown(f"## 🏠 {greeting}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🚀 Quick Actions")
        if st.button("➕ Create Meeting, Event, or Task", use_container_width=True):
            st.session_state.page = "➕ Create"
            st.rerun()

        if st.button("🔍 Search", use_container_width=True):
            st.session_state.page = "🔍 Search"
            st.rerun()

    with col2:
        st.markdown("### 📊 Today's Overview")
        today = datetime.now().strftime("%A, %B %d, %Y")
        st.info(f"Today is {today}")

    st.markdown("---")
    st.markdown("### 🗓️ Upcoming Events")

    events, error = get_upcoming_events(creds, max_results=5)

    if error:
        st.error(f"❌ Could not load upcoming events: {error}")
    elif not events:
        st.info("📭 No upcoming events found.")
    else:
        for event in events:
            start_raw = event["start"].get("dateTime", event["start"].get("date", ""))
            end_raw = event["end"].get("dateTime", event["end"].get("date", ""))

            # Format datetime strings for display
            try:
                if "T" in start_raw:
                    start_dt = datetime.fromisoformat(start_raw)
                    start_str = start_dt.strftime("%a, %b %d · %I:%M %p")
                    end_dt = datetime.fromisoformat(end_raw)
                    end_str = end_dt.strftime("%I:%M %p")
                    time_str = f"{start_str} – {end_str}"
                else:
                    start_dt = datetime.fromisoformat(start_raw)
                    time_str = start_dt.strftime("%a, %b %d") + " (All day)"
            except ValueError:
                time_str = start_raw

            title = event.get("summary", "Untitled Event")
            location = event.get("location", "")
            link = event.get("htmlLink", "")
            has_attendees = len(event.get("attendees", [])) > 0
            label = "meeting" if has_attendees else "event"

            with st.container(border=True):
                title_md = f"**{title}**"
                if link:
                    title_md = f"**[{title}]({link})**"
                st.markdown(title_md)
                st.caption(
                    f"{'👥' if has_attendees else '📅'} {label.capitalize()}  ·  🕐 {time_str}"
                    + (f"  ·  📍 {location}" if location else "")
                )

    st.markdown("---")
    st.markdown("### 💡 How to Use")
    st.markdown("""
    1. **Create**: Describe a meeting (with attendees), personal event, or task in natural language
    2. **Search**: Find existing meetings, events, or tasks by description or date
    3. **Modify**: Update any meeting, event, or task by describing the change
    4. **Delete**: Remove meetings, events, or tasks with confirmation
    """)


def render_notification_controls(key_prefix: str) -> Optional[dict]:
    """Render email and popup notification controls.

    Returns a reminders dict ready for the Google Calendar API, e.g.:
        {"useDefault": False, "overrides": [{"method": "email", "minutes": 1440}]}
    Returns None when the user has not selected any notifications.
    Notifications are not supported for tasks.
    """
    st.markdown("### 🔔 Notifications")
    st.caption("Supported for meetings and events. Not available for tasks.")

    unit_to_minutes = {"minutes": 1, "hours": 60, "days": 1440}
    overrides = []

    col1, col2 = st.columns(2)

    with col1:
        email_on = st.checkbox("Email notification", key=f"{key_prefix}_email_on")
        if email_on:
            amt_col, unit_col = st.columns(2)
            with amt_col:
                email_amt = st.number_input("Amount", min_value=1, value=1, key=f"{key_prefix}_email_amt")
            with unit_col:
                email_unit = st.selectbox("Unit", ["days", "hours", "minutes"], key=f"{key_prefix}_email_unit")
            overrides.append({"method": "email", "minutes": int(email_amt * unit_to_minutes[email_unit])})

    with col2:
        popup_on = st.checkbox("Pop-up notification", key=f"{key_prefix}_popup_on")
        if popup_on:
            amt_col, unit_col = st.columns(2)
            with amt_col:
                popup_amt = st.number_input("Amount", min_value=1, value=30, key=f"{key_prefix}_popup_amt")
            with unit_col:
                popup_unit = st.selectbox("Unit", ["minutes", "hours", "days"], key=f"{key_prefix}_popup_unit")
            overrides.append({"method": "popup", "minutes": int(popup_amt * unit_to_minutes[popup_unit])})

    if overrides:
        return {"useDefault": False, "overrides": overrides}
    return None


def show_create_page(creds):
    """Page for creating new meetings, events, or tasks."""
    st.markdown("## ➕ Create Meeting, Event, or Task")
    st.markdown(
        "Describe what you want to create. The agent will automatically determine "
        "whether it's a **meeting** (with attendees), a personal **event**, or a **task**."
    )

    description = st.text_area(
        "Describe the meeting, event, or task:",
        placeholder=(
            "Examples:\n"
            "• Meeting: 'Schedule a sync with Alice (alice@co.com) and Bob (bob@co.com) on Friday at 2 PM for 1 hour'\n"
            "• Event: 'Block my calendar for deep work on Monday from 9 AM to 12 PM'\n"
            "• Task: 'Add a task to submit the Q1 report by end of this week'"
        ),
        height=140
    )

    # Quick templates
    st.markdown("### 📝 Quick Templates")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("👥 Team Meeting", use_container_width=True):
            st.session_state.create_description = (
                "Schedule a team meeting with the team (team@company.com) tomorrow at 10 AM for 1 hour"
            )
    with col2:
        if st.button("📅 Focus Block", use_container_width=True):
            st.session_state.create_description = (
                "Block my calendar for deep work on Monday from 9 AM to 12 PM"
            )
    with col3:
        if st.button("✅ Task", use_container_width=True):
            st.session_state.create_description = (
                "Add a task to review the project proposal by Friday"
            )

    # Apply template if selected
    if "create_description" in st.session_state:
        description = st.session_state.create_description
        del st.session_state.create_description

    st.markdown("---")
    reminders = render_notification_controls("create")

    if st.button("🚀 Create", type="primary", use_container_width=True):
        if not description.strip():
            st.error("❌ Please enter a description.")
        else:
            with st.spinner("Processing your request..."):
                try:
                    result = process_calendar_request(creds, "primary", description, reminders_override=reminders)
                    if result and result.success:
                        st.success("✅ Created successfully!")
                        st.markdown(f"**Message:** {result.message}")
                        if result.calendar_link:
                            st.markdown(f"**Calendar Link:** [View Event]({result.calendar_link})")
                    else:
                        msg = result.message if result else "Could not process request. Please try a clearer description."
                        st.error(f"❌ {msg}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")


def show_search_page(creds):
    """Page for searching calendar events and tasks."""
    st.markdown("## 🔍 Search Meetings, Events, and Tasks")

    col1, col2 = st.columns(2)

    with col1:
        search_query = st.text_input(
            "Search by description:",
            placeholder="e.g., team meeting, dentist, report"
        )

    with col2:
        date_option = st.selectbox(
            "Date range (for calendar items):",
            ["Today", "This Week", "This Month", "Custom Range"]
        )

    if date_option == "Custom Range":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start date:")
        with col2:
            end_date = st.date_input("End date:")
    else:
        start_date = None
        end_date = None

    include_tasks = st.checkbox("Also search tasks", value=True)

    if st.button("🔍 Search", type="primary", use_container_width=True):
        if not search_query and date_option == "Custom Range" and not start_date and not end_date:
            st.warning("⚠️ Please provide a search query or select a date range.")
        else:
            with st.spinner("Searching..."):
                # --- Calendar events (meetings + personal events) ---
                try:
                    events = get_calendar_events(creds, "primary", search_query or "all events")
                except Exception as e:
                    events = []
                    st.error(f"❌ Error searching calendar: {e}")

                if events:
                    st.markdown(f"### 📅 Calendar Items ({len(events)} found)")
                    for i, event in enumerate(events, 1):
                        start = event["start"].get("dateTime", event["start"].get("date"))
                        end = event["end"].get("dateTime", event["end"].get("date"))
                        location = event.get("location", "No location")
                        description = event.get("description", "No description")
                        has_attendees = len(event.get("attendees", [])) > 0
                        label = "Meeting" if has_attendees else "Event"

                        with st.expander(f"{i}. {'👥' if has_attendees else '📅'} [{label}] {event.get('summary', 'No title')}"):
                            st.markdown(f"**📅 Time:** {start} to {end}")
                            st.markdown(f"**📍 Location:** {location}")
                            st.markdown(f"**📝 Description:** {description}")
                            if has_attendees:
                                attendees = [a.get("email", "") for a in event.get("attendees", [])]
                                st.markdown(f"**👥 Attendees:** {', '.join(attendees)}")
                            if event.get("htmlLink"):
                                st.markdown(f"**🔗 [View in Calendar]({event['htmlLink']})**")
                elif not include_tasks:
                    st.info("📭 No calendar items found matching your criteria.")

                # --- Tasks ---
                if include_tasks:
                    try:
                        tasks = get_tasks(creds, search_query or "all tasks")
                    except Exception as e:
                        tasks = []
                        st.error(f"❌ Error searching tasks: {e}")

                    if tasks:
                        st.markdown(f"### ✅ Tasks ({len(tasks)} found)")
                        for i, task in enumerate(tasks, 1):
                            due = task.get("due", "No due date")
                            notes = task.get("notes", "No notes")
                            status = task.get("status", "needsAction")
                            status_icon = "✅" if status == "completed" else "⬜"
                            with st.expander(f"{i}. {status_icon} {task.get('title', 'Untitled Task')}"):
                                st.markdown(f"**📅 Due:** {due}")
                                st.markdown(f"**📝 Notes:** {notes}")
                                st.markdown(f"**Status:** {status}")
                    elif not events:
                        st.info("📭 No items found matching your criteria.")


def show_modify_page(creds):
    """Page for modifying existing meetings, events, or tasks."""
    st.markdown("## ✏️ Modify Meeting, Event, or Task")
    st.markdown(
        "Describe the change you want to make. The agent will determine whether the item "
        "is a **meeting**, **event**, or **task** and apply the update."
    )

    description = st.text_area(
        "Describe what to modify:",
        placeholder=(
            "Examples:\n"
            "• 'Move the Friday team meeting to 3 PM'\n"
            "• 'Change my dentist appointment location to 123 Main St'\n"
            "• 'Mark the report review task as completed'"
        ),
        height=120
    )

    st.markdown("---")
    reminders = render_notification_controls("modify")

    if st.button("✏️ Apply Modification", type="primary", use_container_width=True):
        if not description.strip():
            st.error("❌ Please enter a description.")
        else:
            with st.spinner("Applying modification..."):
                try:
                    result = process_calendar_request(creds, "primary", description, reminders_override=reminders)
                    if result and result.success:
                        st.success("✅ Modified successfully!")
                        st.markdown(f"**Message:** {result.message}")
                    else:
                        msg = result.message if result else "Could not process request."
                        st.error(f"❌ {msg}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")


def show_delete_page(creds):
    """Page for deleting meetings, events, or tasks."""
    st.markdown("## 🗑️ Delete Meeting, Event, or Task")

    st.warning("⚠️ **Warning:** This action cannot be undone!")

    description = st.text_area(
        "Describe what to delete:",
        placeholder=(
            "Examples:\n"
            "• 'Delete the team meeting scheduled for tomorrow'\n"
            "• 'Remove my dentist appointment on Friday'\n"
            "• 'Delete the task to review the Q1 report'"
        ),
        height=120
    )

    delete_all = st.checkbox("Delete all matching items (if multiple found)")

    if st.button("🗑️ Delete", type="primary", use_container_width=True):
        if not description.strip():
            st.error("❌ Please enter a description.")
        else:
            with st.spinner("Finding and deleting..."):
                try:
                    # Classify item type to route to the right delete function
                    request_type = determine_calendar_request_type(description)
                    item_type = request_type.get("item_type", "unknown")

                    if item_type == "task":
                        result = delete_task(creds, description, all=delete_all)
                    else:
                        result = delete_event(creds, "primary", description, all=delete_all)

                    if result and result.success:
                        st.success("✅ Deleted successfully!")
                        st.markdown(f"**Message:** {result.message}")
                    else:
                        msg = result.message if result else "Could not process request."
                        st.error(f"❌ {msg}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")


def show_settings_page():
    """Page for application settings."""
    st.markdown("## ⚙️ Settings")

    st.markdown("### 🔑 API Configuration")
    st.info("Your Google API key is configured.")

    st.markdown("### 📁 File Locations")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Required files:**")
        if os.path.exists("credentials.json"):
            st.success("✅ credentials.json")
        else:
            st.error("❌ credentials.json (missing)")

        if os.path.exists("token.json"):
            st.success("✅ token.json")
        else:
            st.info("ℹ️ token.json (will be created on first use)")

    with col2:
        st.markdown("**Environment variables:**")
        if os.environ.get("GOOGLE_API_KEY"):
            st.success("✅ GOOGLE_API_KEY")
        else:
            st.error("❌ GOOGLE_API_KEY")

    st.markdown("### 🧹 Clear Data")
    if st.button("🗑️ Clear Authentication Token"):
        if os.path.exists("token.json"):
            os.remove("token.json")
            st.success("✅ Authentication token cleared. You'll need to re-authenticate.")
        else:
            st.info("ℹ️ No authentication token to clear.")


if __name__ == "__main__":
    main()
