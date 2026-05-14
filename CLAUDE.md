# Kaggle-Claude-Notebook

## Project Goal
A tool that lets Claude Code remotely control a live Kaggle Jupyter notebook session from Termux on Android — adding, editing, and executing cells on the Kaggle GPU — via a local browser UI. No manual upload/download required.

## Current Status
- **Working end-to-end** — browser UI, cell execution on GPU, Claude chat with full notebook context
- **Dynamic Real-time Chat** — streams thinking steps and tokens instantly via `--include-partial-messages`
- **Persistent Chat History** — sessions survive page reloads and server restarts via server-side JSON storage
- **Per-notebook chat history** — history files are keyed by notebook slug (`chat_history_{slug}.json`); switching notebooks preserves each notebook's history
- **Claude Code version locked** to `@2.1.112` (only version that works on Android arm64)
- **Auto-init** — notebook is created automatically on new Kaggle sessions
- **URL hot-swap** — change Kaggle URL from the browser without restarting
- **Persistent chat session** — `--continue` reuses the same Claude Code session across messages; full context injected only on first message
- **Terminal-style tool visibility** — chat UI shows each bash tool call and its output as Claude works
- **Auto session start** — Flask auto-starts the Kaggle Jupyter Server session on startup if no URL is set (via Selenium)
- **Selenium session automation** — `kaggle_selenium.py` navigates Run → Kaggle Jupyter Server → Start Session and extracts the JWT proxy URL automatically
- **`cc-` notebook convention** — only notebooks with the `cc-` name prefix are managed by the automation tools (safeguard against touching unintended notebooks)
- **KB write permissions fixed** — `settings.json` uses full wildcards (`Write(*)`, `Edit(*)`, etc.) so Claude in Flask chat can write files to `kb/`

---

## File Structure

```
Kaggle-Claude-Notebook/
├── CLAUDE.md              # this file
├── kaggle_client.py       # CLI client for all notebook operations
├── notebook_ui.py         # Flask browser UI (port 5000)
├── new_html.py            # standalone HTML/CSS/JS template (mobile UI)
├── kaggle_selenium.py     # Selenium automation — starts Kaggle session, extracts JWT URL
├── kaggle_login.py        # one-time login: saves Firefox session for Selenium reuse
├── add_tts_cells.py       # helper: adds TTS cells to the notebook
├── start.sh               # one-command launcher
├── kb/                    # Knowledge Base — files injected into Claude context
└── .claude/
    ├── settings.json      # full wildcard permissions (Bash/Read/Write/Edit/List/MultiEdit)
    └── settings.local.json  # URL-specific permissions for current session

~/.shortcuts/
├── CC-Kaggle-UI.sh        # Termux widget — starts UI with hardcoded URL
└── Kill-UI.sh             # Termux widget — stops server + releases wake lock
```

---

## What We Built

### 1. `kaggle_client.py` — CLI client
Talks directly to the Kaggle Jupyter server via REST + WebSocket.

```bash
python3 kaggle_client.py --url "<KAGGLE_SERVER_URL>" <command>
```

| Command | What it does |
|---|---|
| `init` | Create `claude_notebook.ipynb` on the Kaggle server |
| `list` | List all cells with execution count and output count |
| `show <i>` | Print a cell's source and saved output |
| `add "code"` | Append a code cell (`--type markdown`, `--index N` optional) — `\n` in the string is expanded to real newlines |
| `edit <i> "code"` | Replace a cell's source (clears outputs) — `\n` expanded |
| `delete <i>` | Remove a cell |
| `run <i>` | Execute cell on Kaggle GPU, save output back to notebook |
| `run-all` | Run every code cell in order |
| `exec "code"` | Run ad-hoc code on kernel (not saved to notebook) |

### Datasets
Kaggle datasets are downloaded to `/kaggle/working/datasets/<name>/` via the Kaggle CLI.
Credentials are saved locally in `.kaggle_creds.json` and written to `/root/.kaggle/kaggle.json` on the kernel before each download.

To download in a code cell:
```python
import subprocess
subprocess.run(['kaggle', 'datasets', 'download', '-d', 'owner/slug', '--unzip', '-p', '/kaggle/working/datasets/name/'])
```
Then access files at `/kaggle/working/datasets/<name>/<file>`.

The UI **📦 Datasets** button handles credentials + download without writing code.

### 2. `notebook_ui.py` — Flask browser UI
Local web server on port 5000. Open `http://localhost:5000` in your phone browser.

Features:
- View all cells + outputs (markdown rendered, code with execution count)
- **▶ Run** per cell — executes on Kaggle GPU, saves output inline
- **▶ Run All** — runs all code cells in order
- **+ Code / + MD** — add cells from toolbar or the input bar at the bottom
- **⬇ Download** — download `claude_notebook.ipynb` to phone
- **✦ Claude** — persistent chat session (`--continue`); full context injected on first message only; subsequent messages are raw user text. 
    - **Real-time streaming**: Shows thinking steps and token deltas as they arrive.
    - **Session persistence**: History is saved to `chat_history_{slug}.json` (per notebook) and restored automatically on page reload.
    - **Tool visibility**: Shows tool calls + outputs terminal-style.
    - **New Chat**: Resets the history and starts a fresh session.
    - **Delete Chat**: Clears all history and resets the session.
- **📁 Knowledge Base** — upload/delete reference files (PDFs, markdown, etc.) stored in `kb/`; their contents are automatically injected into every Claude prompt
- **⚙ URL** — paste a new Kaggle server URL and reconnect without restarting
- Auto-refreshes every 15 seconds
- Auto-creates `claude_notebook.ipynb` on new Kaggle sessions (handles 404)

### Knowledge Base (`kb/`)
Files placed in the `kb/` directory are read by `_build_kb_context()` and prepended to every Claude chat prompt. Use this for assignment instructions, reference docs, or any persistent context Claude should always have.

Manage via the UI (**📁 KB** tab) or directly drop files into `kb/`. Supported: any text-readable format (`.md`, `.txt`, `.py`, `.pdf` text, etc.).

Claude in the Flask chat can also write files directly to `kb/` — `settings.json` grants `Write(*)` permission so no prompts appear.

### 3. `kaggle_selenium.py` — session automation
Uses Selenium + geckodriver with a saved Firefox profile to automate Kaggle session startup.

- `fetch_jwt_url(kernel_slug, headless)` — opens the notebook edit page, checks if session is already running (URL in page HTML), or clicks Run → Kaggle Jupyter Server → Start Session and polls for the JWT proxy URL (up to 3 min)
- `_get_active_slug()` — queries Kaggle API for the most recently run `cc-` notebook
- Uses JS click (`execute_script`) + 5 XPath strategies to handle React SPA elements
- Firefox profile: `/data/data/com.termux/files/home/.firefox-profiles/kaggle` (saved by `kaggle_login.py`)
- `dom.webdriver.enabled: false` prevents Google OAuth bot detection

### 4. `kaggle_login.py` — one-time login
Run once with Termux:X11 open to save your Google/Kaggle session to the Firefox profile.
```bash
python3 kaggle_login.py
# Opens Firefox in X11 — log in with Google, then press Enter in terminal
```
Only needs to be run again if the session cookie expires.

### 5. `new_html.py` — HTML/CSS/JS template
Contains the full mobile-optimized frontend as a Python string (`NEW_HTML`). Mobile-first layout with fixed header, bottom tab bar, and touch-friendly controls.

### 8. `add_tts_cells.py` — TTS helper
Standalone script that appends text-to-speech cells to the notebook. Has a hardcoded `URL` constant at the top — update it to the current Kaggle session URL before running.

```bash
python3 add_tts_cells.py
```

### 9. `start.sh` — one-command launcher
Installs the required Claude Code version, acquires wake lock, starts UI, opens browser.

```bash
export KAGGLE_SERVER_URL="https://..."   # optional — script prompts if not set
bash ~/Kaggle-Claude-Notebook/start.sh
```

### 10. Termux shortcuts
- **CC-Kaggle-UI.sh** — tap to launch (edit file to hardcode URL)
- **Kill-UI.sh** — tap to stop server and release wake lock

---

## How the Kaggle Connection Works

### Authentication
Kaggle embeds a JWT token in the server URL path — no separate auth header needed. The URL is the auth:
```
https://kkb-production.jupyter-proxy.kaggle.net/k/<kernel-id>/<jwt>/proxy
```
Get it from: Kaggle notebook → **Add-ons → External Editor** → copy VSCode-compatible URL.

URLs expire with the session. Use **⚙ URL** in the browser UI to update without restarting, or click **▶ Start Session Automatically** to let Selenium fetch it for you.

### Notebook file
We create and manage **`claude_notebook.ipynb`** in `/kaggle/working/` via the Jupyter contents API.

**Do not touch `__notebook_source__.ipynb`** — Kaggle blocks it from the contents API (returns 404). That's the user's original notebook; we maintain a separate one.

### Cell execution
Code → WebSocket (`/api/kernels/<id>/channels`) → kernel runs it on GPU → outputs captured → written back into notebook JSON → visible in UI.

### Claude chat context
The **first message** of a session gets the full context injected (notebook state + KB + instructions). **Subsequent messages** use `--continue` to resume the same Claude Code session — only the raw user text is sent, saving tokens. Use "New Chat" in the UI (or restart the server) to start a fresh session with re-injected context.

---

## Key Technical Decisions

| Decision | Reason |
|---|---|
| Separate `claude_notebook.ipynb` | Kaggle blocks `__notebook_source__.ipynb` from contents API |
| JWT in URL path, no auth header | Kaggle's external editor auth is URL-embedded |
| WebSocket for execution, REST for file I/O | Jupyter kernel protocol requires WebSocket |
| Flask SSE for Claude streaming | Streams Claude output token-by-token to browser |
| Literal URL in Claude context (not `$VAR`) | Shell variable expansion blocked by Termux hooks |
| `.claude/settings.json` allows `python3`/`node` | Prevents Claude from asking permission on every command |
| `nohup` + `termux-wake-lock` in start.sh | Keeps server alive when screen locks or terminal closes |
| Auto-install `cli.js` check at startup | `cli.js` disappears if server started without `start.sh` |
| `kb/` directory for reference files | Persistent context (assignment docs, instructions) always available to Claude without manual pasting |
| `settings.local.json` alongside `settings.json` | URL-specific permissions for the current session without polluting the checked-in config |
| `--continue` on chat follow-up messages | Reuses Claude Code session — avoids re-injecting full context on every turn |
| `--include-partial-messages` | Enables real-time streaming of tokens and thinking steps |
| `chat_history_{slug}.json` per-notebook | Each notebook has isolated chat history; switching notebooks preserves each one's context |
| `--max-turns 50` | Removes default turn limit so Claude completes multi-step tasks without stopping early |
| `_unescape()` in `kaggle_client.py` | Shell args pass `\n` as two chars; must expand to real newlines or multi-line code becomes one giant comment |
| "Do NOT write helper scripts" in system prompt | Claude was writing script text instead of executing `kaggle_client.py` tool calls directly |
| `cc-` prefix convention for managed notebooks | Prevents automation tools from accidentally touching the user's original Kaggle notebook |
| `dom.webdriver.enabled: false` in Selenium | Prevents Google OAuth from detecting Selenium as a bot |
| Saved Firefox profile for Selenium | Reuses Google login cookie — no credentials stored, no CAPTCHA |
| `Write(*)` wildcard in `settings.json` | Path-specific globs (`Write(kb/**)`) are not honored by Claude Code 2.1.112; wildcard is required |

---

## Claude Code — EXACT VERSION REQUIRED

> **Must be exactly `@anthropic-ai/claude-code@2.1.112`**

Other versions fail on Android arm64:
```
[@anthropic-ai/claude-code] Unsupported platform: android arm64
```

`start.sh` and `notebook_ui.py` both install/verify this automatically. Invoked as:
```bash
node /data/data/com.termux/files/usr/lib/node_modules/@anthropic-ai/claude-code/cli.js \
  -p "<prompt>" --output-format stream-json --verbose --max-turns 50 --include-partial-messages
# add --continue on all messages after the first (managed by notebook_ui.py)
```

---

## Token Efficiency Rules
- Only read files explicitly mentioned in the user's request
- Do NOT speculatively read files for context unless asked
- Do NOT re-read a file already read in this session unless it was modified
- Prefer targeted edits over full rewrites
- If a task requires reading more than 2 files you weren't directed to, stop and confirm
- Notebook state is pre-injected into every Claude chat prompt — do NOT re-read it via tools
- KB files are pre-injected too — do NOT re-read `kb/` files unless asked to modify them

## Behaviour Rules
- Act immediately — `.claude/settings.json` already grants permission for `python3`/`node`
- Use the literal URL value from the injected context, never `$KAGGLE_SERVER_URL`
- Do not ask for clarification unless the request is genuinely ambiguous

---

## Environment
- For global device, Termux, and environment details, refer to `~/CLAUDE.md`.

| | |
|---|---|
| Kaggle GPU | Tesla T4 |
| Kaggle Python | 3.12.12 |

---

## Starting a New Session

### Prerequisites (one-time setup)
1. Run `python3 kaggle_login.py` with Termux:X11 open — log in with Google, press Enter
2. Ensure your managed notebook name starts with `cc-` (e.g. `cc-main`)

### Normal startup
1. Open a Kaggle notebook (`cc-*`) with GPU enabled — does **not** need Jupyter Server started
2. Tap **CC-Kaggle-UI** shortcut (or `bash ~/Kaggle-Claude-Notebook/start.sh`)
3. Open `http://localhost:5000` in browser — Flask auto-starts the session via Selenium in the background
4. If auto-start fails → tap **⚙ URL** → click **▶ Start Session Automatically**, or paste URL manually
5. To stop → tap **Kill-UI** shortcut (or `pkill -f notebook_ui.py`)
