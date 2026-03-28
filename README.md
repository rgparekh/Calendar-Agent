# Calendar Agent

Google Calendar agent that **creates, searches, modifies, and deletes meetings, events, and tasks** from **natural language**, using the Gemini API and the Google Calendar and Tasks APIs. This repo includes a **Streamlit** UI and a Python module you can import from your own scripts.

**Repository:** [github.com/rgparekh/Calendar-Agent](https://github.com/rgparekh/Calendar-Agent)

## Features

- **Meetings** — calendar entries with one or more invited attendees (invites are sent via Google Calendar)
- **Events** — personal calendar entries owned only by you, with no external attendees (e.g. focus blocks, appointments, reminders)
- **Tasks** — to-do items managed via Google Tasks; no calendar time slot required
- **Notifications** — email and/or pop-up reminders for meetings and events, configurable to any number of minutes, hours, or days before the item
- **Streamlit app** (`calendar_agent_ui.py`): home screen with upcoming events, create, search, modify, delete, and settings pages
- **Agent logic** (`google_calendar_agent.py`): classifies each request by action (create / modify / delete) and item type (meeting / event / task), then drives the appropriate Google API call via structured LLM output
- OAuth **token refresh** with recovery if the refresh token is revoked (`invalid_grant`): stale `token.json` is removed and you sign in again

## Natural Language Examples

Just describe what you want in plain English. The agent figures out whether it's a meeting, event, or task and takes the appropriate action.

### Meetings

| Intent | Example prompt |
|--------|---------------|
| Create | `Schedule a sync with Alice (alice@co.com) and Bob (bob@co.com) on Friday at 2 PM PT for 1 hour` |
| Create recurring | `Set up a weekly team standup every Monday at 9 AM with the team (team@co.com) for 30 minutes` |
| Create with location | `Book a client dinner with Sarah (sarah@client.com) at Nobu on Thursday at 7 PM for 2 hours` |
| Modify time | `Move the Friday sync with Alice to 3 PM` |
| Add attendee | `Add Carol (carol@co.com) to the Monday standup` |
| Delete | `Cancel the client dinner with Sarah on Thursday` |

### Events

| Intent | Example prompt |
|--------|---------------|
| Create | `Block my calendar for deep work on Monday from 9 AM to 12 PM PT` |
| Create | `Add a dentist appointment on March 30 at 10 AM` |
| Create all-day | `Add a personal day on April 4` |
| Modify | `Change my dentist appointment to 11 AM` |
| Modify location | `Update my dentist appointment location to 123 Main St` |
| Delete | `Remove the focus block on Monday morning` |

### Tasks

| Intent | Example prompt |
|--------|---------------|
| Create | `Add a task to submit the Q1 report by end of this week` |
| Create | `Remind me to buy groceries` |
| Create with due date | `Add a task to review the project proposal — due Friday` |
| Modify | `Update the Q1 report task notes to include the finance team review` |
| Complete | `Mark the grocery task as completed` |
| Delete | `Delete the task to review the project proposal` |

### Notifications

Notifications can be set when **creating or modifying a meeting or event**. Google Tasks does not support notifications via the API.

#### Via the Streamlit UI

On the **Create** or **Modify** page, expand the Notifications section beneath the description field:

1. Check **Email notification** to receive an email reminder, and/or **Pop-up notification** for an on-screen alert.
2. For each selected type, enter an amount and choose a unit — **minutes**, **hours**, or **days**.
3. Multiple notification types can be combined (e.g. an email 1 day before and a pop-up 30 minutes before).

#### Via natural language (CLI or UI description field)

You can also describe reminders directly in your prompt. The agent extracts the notification details automatically:

| Intent | Example prompt |
|--------|---------------|
| Email only | `Schedule a dentist appointment on Friday at 10 AM — email me 1 day before` |
| Pop-up only | `Add a focus block Monday 9–12 PM with a pop-up reminder 15 minutes before` |
| Both types | `Book a team sync with Alice (alice@co.com) tomorrow at 2 PM — email 1 day before and pop-up 30 minutes before` |
| Modify reminders | `Add a pop-up reminder 1 hour before the Monday standup` |

#### How notifications work

| Setting | Delivered as |
|---------|-------------|
| Email | An email sent to the calendar owner's Google account address |
| Pop-up | An alert shown in Google Calendar (web and mobile) |
| Time before | Any value expressed in minutes; the UI converts hours and days automatically (1 hour = 60 min, 1 day = 1440 min) |

## Requirements

- Python 3.10+ (recommended)
- A [Google Cloud](https://console.cloud.google.com/) project with:
  - **Google Calendar API** enabled
  - **Google Tasks API** enabled
  - **OAuth consent screen** configured
  - **OAuth 2.0 Client ID** of type **Desktop app** → download as `credentials.json`
- A **Gemini API key** exposed as `GOOGLE_API_KEY` (used by `google_calendar_agent.py`)

## Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/rgparekh/Calendar-Agent.git
   cd Calendar-Agent
   ```

2. **Create a virtual environment (recommended)**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Add secrets locally (do not commit these)**

   | File / variable | Purpose |
   |-----------------|--------|
   | `credentials.json` | OAuth client secret from Google Cloud Console (Desktop client) |
   | `GOOGLE_API_KEY` | Gemini API key for the agent |

   Example (current shell only):

   ```bash
   export GOOGLE_API_KEY="your-gemini-api-key"
   ```

   Or use a `.env` file with your preferred loader; the Streamlit UI also lets you paste the API key once if the variable is unset.

5. **Place `credentials.json`** in the project root (same directory as `calendar_agent_ui.py`).

## Run the Streamlit UI

From the project root:

```bash
streamlit run calendar_agent_ui.py
```

The first time you use Calendar access, a browser window opens for Google sign-in. Tokens are saved to `token.json` locally.

## Project layout

| File | Role |
|------|------|
| `calendar_agent_ui.py` | Streamlit frontend and OAuth helper |
| `google_calendar_agent.py` | Gemini client, models, and Calendar operations |
| `google_calendar_events.py` | Lower-level Calendar helpers (optional / reference) |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Excludes `credentials.json`, `token.json`, `.env`, etc. |

## Troubleshooting

- **`invalid_grant` / auth errors:** Delete `token.json` (or use **Settings → Clear Authentication Token** in the UI) and sign in again. Ensure `credentials.json` matches the OAuth client that originally issued the token.
- **Missing API key:** Set `GOOGLE_API_KEY` before starting Streamlit, or enter it when the app prompts you.
- **Scope changes:** If you change OAuth scopes in code (e.g. adding the Tasks scope), remove `token.json` and re-authorize.

## License

This project is licensed under the MIT License. See [LICENSE.md](LICENSE.md) for details.
