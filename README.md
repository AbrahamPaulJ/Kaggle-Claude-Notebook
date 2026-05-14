# Kaggle Claude Notebook

Control a live Kaggle Jupyter notebook from your Android phone — add, edit, and execute cells on a Kaggle GPU — via a local browser UI with integrated Claude Code and Gemini CLI chat. No manual upload/download required.

---

## Features

- **Browser UI** — view cells, run code on Kaggle GPU, add/edit/delete cells from your phone
- **Dual-model chat** — Claude Code and Gemini CLI with real-time streaming, thinking blocks, and tool visibility; toggle between models in the chat tab
- **Collapsible cells** — click the cell header to collapse/expand (source + output together); output has its own independent sub-accordion; state survives auto-refresh
- **Auto session startup** — Selenium automatically starts your Kaggle Jupyter Server and fetches the JWT URL
- **Selective KB injection** — drop reference files into `kb/`; when starting a New Chat, choose which files to include per session to save tokens
- **Per-notebook chat history** — each notebook gets its own persistent chat history, survives page reloads and server restarts
- **Dataset downloads** — download Kaggle datasets directly to the GPU via the UI
- **Kill kernel** — stop the Jupyter kernel from the settings panel without touching the browser
- **Plot rendering** — `matplotlib`/`seaborn` plots captured as PNG and displayed inline

---

## Requirements

- Android phone with [Termux](https://github.com/termux/termux-app) (F-Droid version)
- Termux:X11 (for one-time browser login)
- Python 3.x, Node.js
- geckodriver + Firefox for Android (for Selenium)
- A Kaggle account

---

## Setup

### 1. Install dependencies
```bash
pip install flask requests selenium websocket-client markdown
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
Rename your Kaggle notebook to start with `cc-` (e.g. `cc-main`). This prevents automation from touching unintended notebooks.

---

## Usage

```bash
bash start.sh
```

Then open `http://localhost:5000` in your phone browser.

On startup, Flask automatically finds your most recently run `cc-` notebook and starts its Kaggle Jupyter Server session via Selenium. If that fails, open **⚙ Settings** and click **▶ Start Session Automatically**, or paste the URL manually.

> GPU is allocated when the session starts. If your notebook has GPU disabled, the session still works for CPU workloads — GPU-dependent code will fail at runtime.

### Termux shortcuts (optional)
Copy the scripts from `~/.shortcuts/` to your Termux widget:
- **CC-Kaggle-UI.sh** — one-tap launch
- **Kill-UI.sh** — one-tap stop
- **Copy-Screenshot.sh** — copies your latest DCIM screenshot to `~/debug_screenshot.png` (resized to 900px)

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
├── kb/                    # Knowledge Base — selectively injected into chat prompts
└── .claude/
    └── settings.json      # Claude Code permissions
```

---

## How It Works

Kaggle embeds a JWT token in the Jupyter server URL:
```
https://kkb-production.jupyter-proxy.kaggle.net/k/<kernel-id>/<jwt>/proxy
```

`kaggle_selenium.py` automates navigating to **Run → Kaggle Jupyter Server → Start Session** and extracts this URL. From there, `kaggle_client.py` talks directly to the Jupyter kernel over REST and WebSocket — no browser needed for cell execution.

On the first cell run per session, `%matplotlib inline` is automatically prepended so plots render inline without any setup code.

Both Claude Code and Gemini CLI run locally in Termux. The first message of each chat session receives full context (notebook state + selected KB files). Follow-up messages reuse the same session (`--continue` / `--resume`) without re-injecting context.

---

## Claude Code Version

Must be exactly `@anthropic-ai/claude-code@2.1.112` — the only version that works on Android arm64. `start.sh` installs and verifies this automatically.

---

## Notes

- The managed notebook is `claude_notebook.ipynb` in `/kaggle/working/` — separate from Kaggle's `__notebook_source__.ipynb` (which is blocked from the contents API)
- JWT URLs expire with the session — use **⚙ Settings** in the browser to update without restarting
- KB files are never committed — add your own reference docs locally
