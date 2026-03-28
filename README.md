# Calendar Agent

Google Calendar agent that **creates, searches, modifies, and deletes** events from **natural language**, using the Gemini API and the Google Calendar API. This repo includes a **Streamlit** UI and a Python module you can import from your own scripts.

**Repository:** [github.com/rgparekh/Calendar-Agent](https://github.com/rgparekh/Calendar-Agent)

## Features

- **Streamlit app** (`calendar_agent_ui.py`): home, create, search, modify, delete, and settings
- **Agent logic** (`google_calendar_agent.py`): classifies intent and drives Calendar operations via structured LLM output
- OAuth **token refresh** with recovery if the refresh token is revoked (`invalid_grant`): stale `token.json` is removed and you sign in again

## Requirements

- Python 3.10+ (recommended)
- A [Google Cloud](https://console.cloud.google.com/) project with:
  - **Google Calendar API** enabled
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
- **Scope changes:** If you change OAuth scopes in code, remove `token.json` and re-authorize.

## License

Add a `LICENSE` file if you want to specify terms for reuse.
