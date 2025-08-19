# Simple Streamlit UI for Google Calendar Agent

import streamlit as st
import os
import json
import logging
from datetime import datetime, timezone, timedelta

# Import your calendar agent functions
from google_calendar_agent import (
    process_calendar_request,
    check_if_calendar_event,
    determine_calendar_request_type,
    get_calendar_events,
    create_new_event,
    modify_event,
    delete_event
)

# Google Calendar authentication imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Calendar scopes
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_google_credentials():
    """Get or create Google Calendar credentials"""
    creds = None
    
    # Check if token.json exists
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                st.error("❌ credentials.json file not found. Please download it from Google Cloud Console.")
                st.stop()
            
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
            
            # Save credentials
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
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
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
    
    # Header
    st.markdown('<h1 class="main-header">📅 Google Calendar Agent</h1>', unsafe_allow_html=True)
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    
    # Initialize page in session state
    if 'page' not in st.session_state:
        st.session_state.page = "🏠 Home"
    
    page = st.sidebar.selectbox(
        "Choose an action:",
        ["🏠 Home", "➕ Create Event", "🔍 Search Events", "✏️ Modify Event", "🗑️ Delete Event", "⚙️ Settings"],
        index=["🏠 Home", "➕ Create Event", "🔍 Search Events", "✏️ Modify Event", "🗑️ Delete Event", "⚙️ Settings"].index(st.session_state.page)
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
    
    # Main content based on selected page
    if page == "🏠 Home":
        show_home_page()
    
    elif page == "➕ Create Event":
        show_create_event_page(creds)
    
    elif page == "🔍 Search Events":
        show_search_events_page(creds)
    
    elif page == "✏️ Modify Event":
        show_modify_event_page(creds)
    
    elif page == "🗑️ Delete Event":
        show_delete_event_page(creds)
    
    elif page == "⚙️ Settings":
        show_settings_page()

def show_home_page():
    """Display the home page with overview and quick actions"""
    st.markdown("## 🏠 Welcome to Your Calendar Agent!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🚀 Quick Actions")
        if st.button("➕ Create New Event", use_container_width=True):
            st.session_state.page = "➕ Create Event"
            st.rerun()
        
        if st.button("🔍 Search Events", use_container_width=True):
            st.session_state.page = "🔍 Search Events"
            st.rerun()
    
    with col2:
        st.markdown("### 📊 Today's Overview")
        today = datetime.now().strftime("%A, %B %d, %Y")
        st.info(f"Today is {today}")
        
        # You can add more dynamic content here
        st.markdown("""
        - **3 upcoming events** this week
        - **2 pending invitations**
        - **1 recurring meeting** scheduled
        """)
    
    st.markdown("---")
    st.markdown("### 💡 How to Use")
    st.markdown("""
    1. **Create Events**: Describe your event in natural language
    2. **Search Events**: Find existing events by description or date
    3. **Modify Events**: Update event details easily
    4. **Delete Events**: Remove unwanted events with confirmation
    """)

def show_create_event_page(creds):
    """Page for creating new calendar events"""
    st.markdown("## ➕ Create New Calendar Event")
    
    # Event description input
    event_description = st.text_area(
        "Describe the event you want to create:",
        placeholder="Example: Schedule a team meeting with John (john@email.com) tomorrow at 2 PM for 1 hour at Conference Room A",
        height=120
    )
    
    # Quick templates
    st.markdown("### 📝 Quick Templates")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Team Meeting", use_container_width=True):
            st.session_state.event_description = "Schedule a team meeting tomorrow at 10 AM for 1 hour"
    
    with col2:
        if st.button("Client Call", use_container_width=True):
            st.session_state.event_description = "Schedule a client call with Sarah (sarah@company.com) on Friday at 3 PM for 45 minutes"
    
    with col3:
        if st.button("Daily Standup", use_container_width=True):
            st.session_state.event_description = "Set up daily standup meeting every weekday at 9 AM for 15 minutes"
    
    # Set description from session state if available
    if hasattr(st.session_state, 'event_description'):
        event_description = st.session_state.event_description
        del st.session_state.event_description
    
    # Create event button
    if st.button("🚀 Create Event", type="primary", use_container_width=True):
        if not event_description.strip():
            st.error("❌ Please enter an event description.")
        else:
            with st.spinner("Creating your event..."):
                try:
                    result = create_new_event(creds, 'primary', event_description)
                    if result and result.success:
                        st.success("✅ Event created successfully!")
                        st.markdown(f"**Message:** {result.message}")
                        if result.calendar_link:
                            st.markdown(f"**Calendar Link:** [View Event]({result.calendar_link})")
                    else:
                        st.error(f"❌ Failed to create event: {result.message if result else 'Unknown error'}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

def show_search_events_page(creds):
    """Page for searching calendar events"""
    st.markdown("## 🔍 Search Calendar Events")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Search by description
        search_query = st.text_input(
            "Search by description:",
            placeholder="e.g., team meeting, client call"
        )
    
    with col2:
        # Date range
        date_option = st.selectbox(
            "Date range:",
            ["Today", "This Week", "This Month", "Custom Range"]
        )
    
    # Custom date range
    if date_option == "Custom Range":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start date:")
        with col2:
            end_date = st.date_input("End date:")
    else:
        start_date = None
        end_date = None
    
    # Search button
    if st.button("🔍 Search Events", type="primary", use_container_width=True):
        if not search_query and date_option == "Custom Range" and not start_date and not end_date:
            st.warning("⚠️ Please provide a search query or select a date range.")
        else:
            with st.spinner("Searching for events..."):
                try:
                    # Convert dates to ISO format if provided
                    start_iso = None
                    end_iso = None
                    
                    if start_date:
                        start_iso = datetime.combine(start_date, datetime.min.time()).isoformat() + 'Z'
                    if end_date:
                        end_iso = datetime.combine(end_date, datetime.max.time()).isoformat() + 'Z'
                    
                    # Get events list from the user's description
                    events = get_calendar_events(creds, 'primary', search_query or "all events")
                    
                    # events = events_result.get('items', [])
                    
                    if not events:
                        st.info("📭 No events found matching your criteria.")
                    else:
                        st.success(f"✅ Found {len(events)} event(s)")
                        
                        for i, event in enumerate(events, 1):
                            with st.expander(f"{i}. {event.get('summary', 'No title')}"):
                                start = event['start'].get('dateTime', event['start'].get('date'))
                                end = event['end'].get('dateTime', event['end'].get('date'))
                                location = event.get('location', 'No location')
                                description = event.get('description', 'No description')
                                
                                st.markdown(f"**📅 Time:** {start} to {end}")
                                st.markdown(f"**📍 Location:** {location}")
                                st.markdown(f"**📝 Description:** {description}")
                                
                                if event.get('htmlLink'):
                                    st.markdown(f"**🔗 [View in Calendar]({event['htmlLink']})**")
                
                except Exception as e:
                    st.error(f"❌ Error searching events: {e}")

def show_modify_event_page(creds):
    """Page for modifying existing calendar events"""
    st.markdown("## ✏️ Modify Calendar Event")
    
    # Search for event to modify
    event_description = st.text_area(
        "Describe the event you want to modify:",
        placeholder="Example: Change the team meeting time to 3 PM and add John as attendee",
        height=100
    )
    
    if st.button("🔍 Find Event to Modify", type="primary", use_container_width=True):
        if not event_description.strip():
            st.error("❌ Please enter an event description.")
        else:
            with st.spinner("Finding event to modify..."):
                try:
                    result = modify_event(creds, 'primary', event_description)
                    if result and result.success:
                        st.success("✅ Event modified successfully!")
                        st.markdown(f"**Message:** {result.message}")
                    else:
                        st.error(f"❌ Failed to modify event: {result.message if result else 'Unknown error'}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

def show_delete_event_page(creds):
    """Page for deleting calendar events"""
    st.markdown("## 🗑️ Delete Calendar Event")
    
    st.warning("⚠️ **Warning:** This action cannot be undone!")
    
    # Search for event to delete
    event_description = st.text_area(
        "Describe the event you want to delete:",
        placeholder="Example: Delete the team meeting scheduled for tomorrow",
        height=100
    )
    
    # Delete options
    delete_all = st.checkbox("Delete all matching events (if multiple found)")
    
    if st.button("🗑️ Delete Event", type="primary", use_container_width=True):
        if not event_description.strip():
            st.error("❌ Please enter an event description.")
        else:
            with st.spinner("Finding event to delete..."):
                try:
                    result = delete_event(creds, 'primary', event_description, all=delete_all)
                    if result and result.success:
                        st.success("✅ Event(s) deleted successfully!")
                        st.markdown(f"**Message:** {result.message}")
                    else:
                        st.error(f"❌ Failed to delete event: {result.message if result else 'Unknown error'}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

def show_settings_page():
    """Page for application settings"""
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
