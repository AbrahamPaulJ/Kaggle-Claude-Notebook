# Kaggle Claude Notebook

Control a live Kaggle Jupyter notebook from your Android phone — add, edit, and execute cells on a Kaggle GPU — via a local browser UI with an integrated Claude Code chat. No manual upload/download required.

---

## Features

- **Browser UI** — view cells, run code on Kaggle GPU, add/edit/delete cells from your phone
- **Claude Code chat** — ask Claude to write and execute notebook code, with real-time streaming and tool visibility
- **Auto session startup** — Selenium automatically starts your Kaggle Jupyter Server and fetches the JWT URL
- **Knowledge Base** — drop reference files into `kb/` and they're injected into every Claude prompt
- **Per-notebook chat history** — each notebook gets its own persistent chat history, survives page reloads
- **Dataset downloads** — download Kaggle datasets directly to the GPU via the UI

---

## Requirements

- Android phone with [Termux](https://github.com/termux/termux-app) (F-Droid version)
- Termux:X11 (for one-time browser login)
- Python 3.x, Node.js
- geckodriver + Firefox for Android (for Selenium)
- A Kaggle account with GPU-enabled notebooks

---

## Setup

### 1. Install dependencies
```bash
pip install flask requests selenium websocket-client
```

### 2. Save Kaggle credentials
Create `.kaggle_creds.json` in the project root:
```json
{
  "username": "your-kaggle-username",
  "key": "your-kaggle-api-key"
}
```

### 3. One-time browser login (for Selenium)
With Termux:X11 open:
```bash
python3 kaggle_login.py
```
Log in with Google in the Firefox window, then press Enter. Your session is saved and reused automatically.

### 4. Name your notebook with the `cc-` prefix
Rename your Kaggle notebook to start with `cc-` (e.g. `cc-main`). This is the safeguard that prevents automation from touching unintended notebooks.

---

## Usage

```bash
bash start.sh
```

Then open `http://localhost:5000` in your phone browser.

On startup, Flask automatically finds your most recently run `cc-` notebook and starts its Kaggle Jupyter Server session via Selenium. If that fails, open the **⚙ URL** panel and click **▶ Start Session Automatically**.

### Termux shortcuts (optional)
Copy `CC-Kaggle-UI.sh` and `Kill-UI.sh` to `~/.shortcuts/` for one-tap launch/stop from the Termux widget.

---

## File Structure

```
Kaggle-Claude-Notebook/
├── kaggle_client.py       # CLI — add/edit/run cells via Jupyter REST + WebSocket
├── notebook_ui.py         # Flask browser UI (port 5000)
├── new_html.py            # Mobile-optimized frontend (HTML/CSS/JS)
├── kaggle_selenium.py     # Selenium automation — starts session, extracts JWT URL
├── kaggle_login.py        # One-time login to save Firefox session
├── add_tts_cells.py       # Helper: appends TTS cells to notebook
├── start.sh               # One-command launcher
├── kb/                    # Knowledge Base — injected into every Claude prompt
└── .claude/
    └── settings.json      # Claude Code permissions
```

---

## How It Works

Kaggle embeds a JWT token in the Jupyter server URL:
```
https://kkb-production.jupyter-proxy.kaggle.net/k/<kernel-id>/<jwt>/proxy
```

`kaggle_selenium.py` automates navigating to **Run → Kaggle Jupyter Server → Start Session** and extracts this URL from the page. From there, `kaggle_client.py` talks directly to the Jupyter kernel over REST and WebSocket — no browser needed for cell execution.

Claude Code runs locally in Termux and receives notebook state + KB contents as context on each chat session.

---

## Claude Code Version

Must be exactly `@anthropic-ai/claude-code@2.1.112` — the only version that works on Android arm64. `start.sh` installs and verifies this automatically.

---

## Notes

- The managed notebook is `claude_notebook.ipynb` in `/kaggle/working/` — separate from Kaggle's `__notebook_source__.ipynb` (which is blocked from the contents API)
- JWT URLs expire with the session — use **⚙ URL** in the browser to update without restarting
- KB files are never committed (see `.gitignore`) — add your own reference docs locally
