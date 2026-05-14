# Kaggle-Claude-Notebook

## Project Goal
A tool that lets Claude Code (or Gemini CLI) remotely control a live Kaggle Jupyter notebook session from Termux on Android — adding, editing, and executing cells on the Kaggle GPU — via a local browser UI. No manual upload/download required.

## Current Status
- **Working end-to-end** — browser UI, cell execution on GPU, dual-model chat with full notebook context
- **Dual-model chat** — Claude Code and Gemini CLI both available; toggle in the chat tab; shared history displayed together
- **Default model: Gemini** — UI starts with Gemini selected on each page load
- **Dynamic Real-time Chat** — Claude streams thinking + tokens via `--include-partial-messages`; Gemini streams delta messages; both show thinking blocks
- **Gemini thinking blocks** — Gemini 2.5 emits `thought: true` events; routed to the thinking-block display (same spinner as Claude)
- **Persistent Chat History** — sessions survive page reloads and server restarts via server-side JSON storage
- **Per-notebook chat history** — history files keyed by notebook slug (`chat_history_{slug}.json`); shared by both models; switching notebooks preserves each notebook's history
- **Claude Code version locked** to `@2.1.112` (only version that works on Android arm64)
- **Gemini CLI** at `/data/data/com.termux/files/usr/bin/gemini`; sessions continued via `--resume <session_id>`
- **Auto-init** — notebook is created automatically on new Kaggle sessions
- **URL hot-swap** — change Kaggle URL from the browser without restarting
- **Heredoc stdin for code** — `add`/`edit`/`exec` accept `-` as source to read from stdin, eliminating all shell-escaping issues with string literals
- **Compact tool chips** — chat shows `⚡ ToolName` → `✓ ToolName` chips only; no command text or output clutter
- **Plot rendering** — `image/png` base64 outputs rendered as `<img>` tags in the notebook UI; `%matplotlib inline` prepended to first cell run (no background thread, no retina format)
- **Auto session start** — Flask auto-starts the Kaggle Jupyter Server session on startup if no URL is set (via Selenium)
- **Selenium session automation** — `kaggle_selenium.py` navigates Run → Kaggle Jupyter Server → Start Session and extracts the JWT proxy URL automatically
- **`cc-` notebook convention** — only notebooks with the `cc-` name prefix are managed by the automation tools (safeguard against touching unintended notebooks)
- **KB write permissions fixed** — `settings.json` uses full wildcards (`Write(*)`, `Edit(*)`, etc.) so Claude in Flask chat can write files to `kb/`
- **Selective KB injection** — New Chat modal lets you choose which KB files to include per session; deselect to save tokens; cells always injected
- **Kill kernel button** — ⚙ settings modal has a "■ Stop Jupyter Kernel" button (calls `DELETE /api/kernels/{id}`)
- **Copy-Screenshot shortcut** — `~/.shortcuts/Copy-Screenshot.sh` copies the latest screenshot from DCIM to `~/debug_screenshot.png` (resized to 900px wide via ffmpeg)

---

## File Structure

```
Kaggle-Claude-Notebook/
├── CLAUDE.md              # this file (symlinked as GEMINI.md)
├── kaggle_client.py       # CLI client for all notebook operations
├── notebook_ui.py         # Flask browser UI (port 5000)
├── new_html.py            # standalone HTML/CSS/JS template (mobile UI)
├── kaggle_selenium.py     # Selenium automation — starts Kaggle session, extracts JWT URL
├── kaggle_login.py        # one-time login: saves Firefox session for Selenium reuse
├── add_tts_cells.py       # helper: adds TTS cells to the notebook
├── start.sh               # one-command launcher
├── kb/                    # Knowledge Base — files injected into Claude/Gemini context
└── .claude/
    ├── settings.json      # full wildcard permissions (Bash/Read/Write/Edit/List/MultiEdit)
    └── settings.local.json  # URL-specific permissions for current session

~/.shortcuts/
├── CC-Kaggle-UI.sh        # Termux widget — starts UI with hardcoded URL
├── Kill-UI.sh             # Termux widget — stops server + releases wake lock
└── Copy-Screenshot.sh     # Termux widget — copies latest DCIM screenshot to ~/debug_screenshot.png
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
| `add - <<'PYEOF'` | Append a code cell from stdin (heredoc) — **preferred form** |
| `add "code"` | Append a code cell from shell arg — only safe for trivial one-liners |
| `edit <i> - <<'PYEOF'` | Replace a cell's source from stdin (heredoc) — **preferred form** |
| `delete <i>` | Remove a cell |
| `run <i>` | Execute cell on Kaggle GPU, save output back to notebook |
| `run-all` | Run every code cell in order |
| `exec - <<'PYEOF'` | Run ad-hoc code on kernel (not saved) from stdin — **preferred form** |

#### Heredoc usage — mandatory for any non-trivial code

Passing multi-line code as a quoted shell argument breaks on string literals because `_unescape()` blindly converts `\n` everywhere. Always use heredoc with a **quoted** delimiter (`<<'PYEOF'`) which prevents all shell substitution:

```bash
python3 /path/kaggle_client.py --url "URL" add - <<'PYEOF'
import numpy as np
text = "hello\nworld"   # \n stays as-is — safe
arr = np.array([1, 2, 3])
print(arr)
PYEOF

python3 /path/kaggle_client.py --url "URL" edit 3 - <<'PYEOF'
# replacement code
PYEOF

python3 /path/kaggle_client.py --url "URL" exec - <<'PYEOF'
print("hello")
PYEOF
```

When source is `"-"`, `kaggle_client.py` reads from stdin and bypasses `_unescape()` entirely — no escaping needed.

### Datasets
Kaggle datasets are downloaded to `/kaggle/working/datasets/<name>/` via the Kaggle CLI.
Credentials are saved locally in `.kaggle_creds.json` and written to `/root/.kaggle/kaggle.json` on the kernel before each download.

The UI **📦 Datasets** button handles credentials + download without writing code.

### 2. `notebook_ui.py` — Flask browser UI
Local web server on port 5000. Open `http://localhost:5000` in your phone browser.

Features:
- View all cells + outputs (markdown rendered, code with execution count and output count)
- **▶ Run** per cell — executes on Kaggle GPU, saves output inline; plots rendered as images
- **▶ Run All** — runs all code cells in order
- **＋** FAB — add cells (code or markdown)
- **⬇ Download** — download `claude_notebook.ipynb` to phone
- **💬 Chat** — dual-model chat tab (Claude + Gemini toggle):
    - **Default model: Gemini** on each page load
    - **Claude** (`◉`): persistent session via `--continue`; full context injected on first message only
    - **Gemini** (`✦`): persistent session via `--resume <session_id>`; full context on first message
    - **Real-time streaming**: both models stream token deltas and thinking blocks
    - **Thinking blocks**: shown with rotating synonym spinner (`◑ Thinking…`)
    - **Tool chips**: compact `⚡ ToolName` → `✓ ToolName` inline chips; no command/result text shown
    - **Session persistence**: shared `chat_history_{slug}.json` per notebook; both models write to it
    - **New Chat**: opens KB selection modal — choose which KB files to include, then resets both sessions + clears history; cells always included regardless
    - **GPU status**: header shows `2× T4 ●` (active), `2× T4 ⚡` (busy), `2× T4` (disconnected)
- **📁 Knowledge Base** — upload/delete reference files stored in `kb/`; injected into every prompt (filtered by per-session `_active_kb_files`)
- **⚙ Settings** — paste a new Kaggle server URL, start session automatically, or stop the Jupyter kernel
- Auto-refreshes every 15 seconds; collapse state (cells + outputs) persists across refreshes
- Auto-creates `claude_notebook.ipynb` on new Kaggle sessions (handles 404)

#### Notebook UI design
- Color scheme: white cells, `#f7f8fa` page background, `#1c2330` dark header, `#0d9e6a` green accent
- Header: slug title (`cc-main.ipynb`), `2× T4` GPU pill, auto-start spinner
- Cell header: click anywhere to collapse/expand the whole cell (source + output); chevron `▾/▸` shows state
- Output section: independently collapsible sub-accordion inside the cell body
- Collapse state stored in module-level JS `Set`s (`cellCollapseState`, `outCollapseState`) — survives DOM rebuilds from auto-refresh
- Code: 8px `SFMono-Regular/Consolas`, `white-space: pre-wrap`; Python comments highlighted green
- Output: 8px monospace, `background: #f0f3f7`
- Copy buttons on cell source, cell output, and every chat message
- Left green gutter line on focused code cells

### Knowledge Base (`kb/`)
Files placed in the `kb/` directory are read by `_build_kb_context()` and prepended to every Claude/Gemini chat prompt — filtered by `_active_kb_files` (set when starting a New Chat).

- `_active_kb_files = None` → all files included (default after server start)
- `_active_kb_files = ["file1.md", ...]` → only listed files included
- Selection resets to "all" each time the New Chat modal is opened

Manage files via the UI (**📚 KB** tab) or drop directly into `kb/`. Supported: any text-readable format (`.md`, `.txt`, `.py`, `.pdf` text, etc.).

Claude in the Flask chat can also write files directly to `kb/` — `settings.json` grants `Write(*)` permission so no prompts appear.

### 3. `kaggle_selenium.py` — session automation
Uses Selenium + geckodriver with a saved Firefox profile to automate Kaggle session startup.

- `fetch_jwt_url(kernel_slug, headless)` — opens the notebook edit page, checks if session is already running, or clicks Run → Kaggle Jupyter Server → Start Session and polls for the JWT proxy URL (up to 3 min)
- `_get_active_slug()` — queries Kaggle API for the most recently run `cc-` notebook
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
Contains the full mobile-optimized frontend as a Python string (`NEW_HTML`). Green-accented design with fixed header (GPU pill + slug title), bottom tab bar (Notebook / Chat / KB / Data), collapsible cells, and dual-model chat.

### 6. `add_tts_cells.py` — TTS helper
Standalone script that appends text-to-speech cells to the notebook. Has a hardcoded `URL` constant at the top — update it to the current Kaggle session URL before running.

### 7. `start.sh` — one-command launcher
Installs the required Claude Code version, acquires wake lock, starts UI, opens browser.

```bash
export KAGGLE_SERVER_URL="https://..."   # optional — script prompts if not set
bash ~/Kaggle-Claude-Notebook/start.sh
```

### 8. Termux shortcuts
- **CC-Kaggle-UI.sh** — tap to launch (edit file to hardcode URL)
- **Kill-UI.sh** — tap to stop server and release wake lock
- **Copy-Screenshot.sh** — tap to copy latest DCIM screenshot → `~/debug_screenshot.png` (900px wide PNG via ffmpeg)

---

## How the Kaggle Connection Works

### Authentication
Kaggle embeds a JWT token in the server URL path — no separate auth header needed. The URL is the auth:
```
https://kkb-production.jupyter-proxy.kaggle.net/k/<kernel-id>/<jwt>/proxy
```
Get it from: Kaggle notebook → **Add-ons → External Editor** → copy VSCode-compatible URL.

URLs expire with the session. Use **⚙ Settings** in the browser UI to update without restarting, or click **▶ Start Session Automatically** to let Selenium fetch it for you.

### Notebook file
We create and manage **`claude_notebook.ipynb`** in `/kaggle/working/` via the Jupyter contents API.

**Do not touch `__notebook_source__.ipynb`** — Kaggle blocks it from the contents API (returns 404). That's the user's original notebook; we maintain a separate one.

### Cell execution
Code → WebSocket (`/api/kernels/<id>/channels`) → kernel runs it on GPU → outputs captured (text + `image/png`) → written back into notebook JSON → visible in UI.

On the **first cell run** after connecting, `_PLOT_SETUP_CODE` (runs `%matplotlib inline`) is prepended to the cell code. This is synchronous — no race condition. `_kernel_plot_setup_done` resets to `False` when the URL changes.

### Chat context injection
The **first message** of each model's session gets the full context injected (notebook state + selected KB files + instructions). **Subsequent messages** resume the same session (`--continue` for Claude, `--resume <session_id>` for Gemini) — only the raw user text is sent. Use "New Chat" to start a fresh session with re-injected context.

Claude and Gemini have separate session state (`_session_active` / `_gemini_session_id`) but write to the **same** `_chat_history` list (shared display, separate underlying sessions).

---

## Key Technical Decisions

| Decision | Reason |
|---|---|
| Separate `claude_notebook.ipynb` | Kaggle blocks `__notebook_source__.ipynb` from contents API |
| JWT in URL path, no auth header | Kaggle's external editor auth is URL-embedded |
| WebSocket for execution, REST for file I/O | Jupyter kernel protocol requires WebSocket |
| Flask SSE for streaming | Streams token deltas to browser for both Claude and Gemini |
| Literal URL in context (not `$VAR`) | Shell variable expansion blocked by Termux hooks |
| `.claude/settings.json` allows `python3`/`node` | Prevents Claude from asking permission on every command |
| `nohup` + `termux-wake-lock` in start.sh | Keeps server alive when screen locks or terminal closes |
| Auto-install `cli.js` check at startup | `cli.js` disappears if server started without `start.sh` |
| `kb/` directory for reference files | Persistent context always available without manual pasting |
| `settings.local.json` alongside `settings.json` | URL-specific permissions without polluting checked-in config |
| `--continue` on Claude follow-up messages | Reuses session — avoids re-injecting full context on every turn |
| `--resume <session_id>` for Gemini follow-ups | Same rationale; session_id captured from `init` event |
| `--include-partial-messages` (Claude) | Enables real-time streaming of tokens and thinking steps |
| `thought: true` event routing (Gemini) | Gemini 2.5 thinking tokens surfaced as thinking blocks, not raw text |
| `chat_history_{slug}.json` per-notebook | Each notebook has isolated history; both models write to same file |
| `--max-turns 50` | Removes default turn limit so Claude completes multi-step tasks |
| Heredoc stdin (`-`) for `add`/`edit`/`exec` | `_unescape()` blindly converts `\n` everywhere, breaking string literals in code; heredoc with `<<'PYEOF'` passes code verbatim with zero shell interpretation |
| `_unescape()` still used for simple one-liner args | Backward compatibility for trivial cases like `add "print('hi')"` |
| `_build_gemini_context()` separate from `_build_context()` | Gemini needs stricter "no description field", "no project file reads", and "stop on network error" rules; Claude Code's context is less strict |
| Gemini `stderr=subprocess.STDOUT` | Merges stderr so quota/auth errors surface in chat instead of silently producing `(no response)` |
| Compact tool chips (no command/result text) | Long command strings and outputs cluttered the chat; name + status is enough |
| `image/png` base64 rendered as `<img>` | matplotlib/seaborn plots were showing `<Figure size ...>` text; PNG data was already saved by the backend |
| `%matplotlib inline` prepended to first cell run (not background thread) | Background thread caused race condition where setup ran concurrently with cell execution, breaking plot capture |
| No `retina` figure format | `InlineBackend.figure_format='retina'` makes PNGs 4× larger; standard resolution is sufficient |
| Cell header click = whole-cell collapse | No dedicated chevron needed; all interactive buttons use `stopPropagation` |
| `cellCollapseState` / `outCollapseState` JS Sets | DOM is rebuilt on every 15s refresh; Sets persist collapse state across rebuilds |
| Hierarchical cell accordion (cell > output) | Whole cell collapses via header click; output has its own independent sub-accordion inside |
| `_active_kb_files` global for KB filtering | Per-session token savings; set via `/api/new-chat`; `None` = all files included |
| `/api/new-chat` unified reset endpoint | Resets both Claude + Gemini + history + KB selection in one call |
| DOM construction for KB checkboxes (not innerHTML) | Setting `style.cssText` then `innerHTML` silently clears inline styles on mobile browsers |
| `DELETE /api/kernels/{id}` for kernel stop | Clean REST call; no Selenium needed to stop a running kernel |
| Green accent `#0d9e6a` | Replaced Kaggle blue; consistent with GPU pill, running cell spinner, and focus gutter |
| `cc-` prefix convention for managed notebooks | Prevents automation from touching the user's original Kaggle notebook |
| `dom.webdriver.enabled: false` in Selenium | Prevents Google OAuth from detecting Selenium as a bot |
| Saved Firefox profile for Selenium | Reuses Google login cookie — no credentials stored, no CAPTCHA |
| `Write(*)` wildcard in `settings.json` | Path-specific globs are not honored by Claude Code 2.1.112; wildcard is required |

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

## Gemini CLI
Available at `/data/data/com.termux/files/usr/bin/gemini`. Invoked as:
```bash
gemini -p "<prompt>" --output-format stream-json --yolo
# add --resume <session_id> on all messages after the first (managed by notebook_ui.py)
```
- Gemini does **not** support `--include-partial-messages`; delta text arrives via `type: message, delta: true` events
- Thinking tokens arrive as `type: message, thought: true` events (Gemini 2.5+)
- Sessions are per-project (per cwd); `session_id` captured from the `init` event and reused via `--resume`
- No equivalent of Claude Code's tool system — Gemini uses its own built-in tools (shell, file read/write, etc.)
- No `-m` model flag — all explicit model names fail on free tier; CLI default is used

---

## Token Efficiency Rules
- Only read files explicitly mentioned in the user's request
- Do NOT speculatively read files for context unless asked
- Do NOT re-read a file already read in this session unless it was modified
- Prefer targeted edits over full rewrites
- If a task requires reading more than 2 files you weren't directed to, stop and confirm
- Notebook state is pre-injected into every chat prompt — do NOT re-read it via tools
- KB files are pre-injected too — do NOT re-read `kb/` files unless asked to modify them

## Behaviour Rules
- Act immediately — `.claude/settings.json` already grants permission for `python3`/`node`
- Use the literal URL value from the injected context, never `$KAGGLE_SERVER_URL`
- Do not ask for clarification unless the request is genuinely ambiguous
- For `add`/`edit`/`exec` with any non-trivial code, always use heredoc form (`- <<'PYEOF'`)
- Do NOT create temporary `.py` files to work around escaping — use heredoc instead

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
1. Open a Kaggle notebook (`cc-*`) — GPU optional (CPU-only sessions work; GPU code will fail at runtime)
2. Tap **CC-Kaggle-UI** shortcut (or `bash ~/Kaggle-Claude-Notebook/start.sh`)
3. Open `http://localhost:5000` in browser — Flask auto-starts the session via Selenium in the background
4. If auto-start fails → tap **⚙ Settings** → click **▶ Start Session Automatically**, or paste URL manually
5. To stop → tap **Kill-UI** shortcut (or `pkill -f notebook_ui.py`)
