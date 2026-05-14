#!/usr/bin/env python3
"""
Local Flask UI for viewing and controlling the Kaggle notebook.
Run this on Termux, then open http://localhost:5000 in your phone browser.
"""

import os
import json
import threading
import subprocess
import uuid
import markdown as md_lib
import requests
import websocket
from flask import Flask, jsonify, request, render_template_string, Response, send_from_directory
from new_html import NEW_HTML

SERVER_URL   = os.environ.get("KAGGLE_SERVER_URL", "")
if SERVER_URL == "change-me":
    SERVER_URL = ""
TOKEN        = os.environ.get("KAGGLE_TOKEN", "")
NOTEBOOK     = "claude_notebook.ipynb"
CLAUDE_CLI   = "/data/data/com.termux/files/usr/lib/node_modules/@anthropic-ai/claude-code/cli.js"
REPO_DIR     = os.path.dirname(os.path.abspath(__file__))
CREDS_FILE   = os.path.join(REPO_DIR, ".kaggle_creds.json")
DATASETS_DIR = "datasets"  # relative to /kaggle/working/ on the kernel
KB_DIR       = os.path.join(REPO_DIR, "kb")
os.makedirs(KB_DIR, exist_ok=True)

ACTIVE_SLUG  = ""  # current cc- notebook slug, e.g. "cc-main"
CC_PREFIX    = "cc-"  # only notebooks with this prefix are managed by this tool
GEMINI_MODEL_PREFERRED = ""   # empty = use CLI default (gemini-3-flash-preview)
GEMINI_MODEL_FALLBACK  = ""   # no working alternative model on free tier

def _history_file(slug=""):
    name = f"chat_history_{slug}.json" if slug else "chat_history.json"
    return os.path.join(REPO_DIR, name)

def _load_history(slug=""):
    f = _history_file(slug)
    if os.path.exists(f):
        try:
            with open(f, "r") as fh:
                return json.load(fh)
        except: return []
    return []

def _save_history(hist, slug=""):
    with open(_history_file(slug), "w") as fh:
        json.dump(hist, fh)

def _set_active_slug(slug):
    """Switch active notebook slug, swapping chat history accordingly."""
    global ACTIVE_SLUG, _chat_history, _chat_started, _session_active, _gemini_session_id, _gemini_session_active
    if slug == ACTIVE_SLUG:
        return
    if ACTIVE_SLUG:
        _save_history(_chat_history, ACTIVE_SLUG)
    ACTIVE_SLUG = slug
    _chat_history = _load_history(slug)
    _chat_started = len(_chat_history) > 0
    _session_active = False
    _gemini_session_id = None
    _gemini_session_active = False
    print(f"[slug] switched to {slug!r}, {len(_chat_history)} messages in history")

_chat_history = _load_history(ACTIVE_SLUG)
_chat_started = len(_chat_history) > 0
_session_active = False
_gemini_session_id = None
_gemini_session_active = False
_gemini_model = GEMINI_MODEL_PREFERRED
_active_kb_files = None  # None = include all; list = include only these filenames

def _ensure_claude():
    if not os.path.exists(CLAUDE_CLI):
        print("cli.js not found — installing @anthropic-ai/claude-code@2.1.112 ...")
        subprocess.run(
            ["npm", "install", "-g", "@anthropic-ai/claude-code@2.1.112", "--silent"],
            check=True
        )
        print("Claude Code installed.")

_ensure_claude()

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Kaggle API helpers
# ---------------------------------------------------------------------------

def _headers():
    return {"Authorization": f"Token {TOKEN}"} if TOKEN else {}

def _read_nb():
    r = requests.get(f"{SERVER_URL}/api/contents/{NOTEBOOK}", headers=_headers())
    r.raise_for_status()
    return r.json()["content"]

def _write_nb(nb):
    r = requests.put(f"{SERVER_URL}/api/contents/{NOTEBOOK}",
                     headers=_headers(), json={"type": "notebook", "content": nb})
    r.raise_for_status()

def _get_kernel_id():
    r = requests.get(f"{SERVER_URL}/api/sessions", headers=_headers())
    r.raise_for_status()
    sessions = r.json()
    if not sessions:
        raise RuntimeError("No active kernel.")
    return sessions[0]["kernel"]["id"]

def _run_on_kernel(code, timeout=120):
    kernel_id = _get_kernel_id()
    ws_url = (SERVER_URL.replace("https://", "wss://").replace("http://", "ws://")
              + f"/api/kernels/{kernel_id}/channels")
    msg_id = str(uuid.uuid4())
    execute_msg = {
        "header": {"msg_id": msg_id, "msg_type": "execute_request",
                   "username": "claude", "session": str(uuid.uuid4()),
                   "date": "", "version": "5.3"},
        "parent_header": {}, "metadata": {},
        "content": {"code": code, "silent": False, "store_history": True,
                    "user_expressions": {}, "allow_stdin": False},
        "channel": "shell",
    }
    messages = []
    done = threading.Event()

    def on_open(ws): ws.send(json.dumps(execute_msg))
    def on_message(ws, raw):
        d = json.loads(raw)
        if d.get("parent_header", {}).get("msg_id") != msg_id:
            return
        messages.append(d)
        if d.get("msg_type") == "status" and d["content"].get("execution_state") == "idle":
            done.set()
    def on_error(ws, err):
        messages.append({"msg_type": "error",
                         "content": {"ename": "WSError", "evalue": str(err), "traceback": []}})
        done.set()

    ws = websocket.WebSocketApp(ws_url, on_open=on_open, on_message=on_message, on_error=on_error)
    t = threading.Thread(target=ws.run_forever); t.daemon = True; t.start()
    done.wait(timeout=timeout); ws.close()
    return messages

# ---------------------------------------------------------------------------
# Async execution state
# ---------------------------------------------------------------------------

_exec_lock = threading.Lock()
_execution = {
    "running": False,
    "cell_idx": None,
    "output": "",       # live text buffer shown while running
    "done": False,
    "error": None,
}

def _run_cell_background(cell_idx: int, code: str):
    """Long-running execution in a background thread — no timeout."""
    global _exec_count, _execution

    kernel_id = _get_kernel_id()
    ws_url = (SERVER_URL.replace("https://", "wss://").replace("http://", "ws://")
              + f"/api/kernels/{kernel_id}/channels")

    msg_id = str(uuid.uuid4())
    execute_msg = {
        "header": {"msg_id": msg_id, "msg_type": "execute_request",
                   "username": "claude", "session": str(uuid.uuid4()),
                   "date": "", "version": "5.3"},
        "parent_header": {}, "metadata": {},
        "content": {"code": code, "silent": False, "store_history": True,
                    "user_expressions": {}, "allow_stdin": False},
        "channel": "shell",
    }

    all_messages = []
    finished = threading.Event()

    def on_open(ws):
        ws.send(json.dumps(execute_msg))

    def on_message(ws, raw):
        d = json.loads(raw)
        if d.get("parent_header", {}).get("msg_id") != msg_id:
            return
        mtype = d.get("msg_type", "")
        c = d.get("content", {})
        all_messages.append(d)

        # Append to live text buffer
        if mtype == "stream":
            with _exec_lock:
                _execution["output"] += c.get("text", "")
        elif mtype in ("execute_result", "display_data"):
            txt = c.get("data", {}).get("text/plain", "")
            if txt:
                with _exec_lock:
                    _execution["output"] += txt + "\n"
        elif mtype == "error":
            tb = "\n".join(c.get("traceback", []))
            import re
            tb_clean = re.sub(r"\x1b\[[0-9;]*m", "", tb)
            with _exec_lock:
                _execution["output"] += f"ERROR {c.get('ename')}: {c.get('evalue')}\n{tb_clean}\n"
        elif mtype == "status" and c.get("execution_state") == "idle":
            finished.set()

    def on_error(ws, err):
        with _exec_lock:
            _execution["error"] = str(err)
        finished.set()

    def on_close(ws, code, msg):
        finished.set()

    ws = websocket.WebSocketApp(ws_url, on_open=on_open, on_message=on_message,
                                on_error=on_error, on_close=on_close)
    t = threading.Thread(target=ws.run_forever); t.daemon = True; t.start()
    finished.wait()  # no timeout — waits as long as needed
    ws.close()

    # Save final outputs to notebook
    outputs = _messages_to_outputs(all_messages)
    _exec_count += 1
    try:
        nb = _read_nb()
        nb["cells"][cell_idx]["outputs"] = outputs
        nb["cells"][cell_idx]["execution_count"] = _exec_count
        _write_nb(nb)
    except Exception as e:
        with _exec_lock:
            _execution["error"] = f"Failed to save outputs: {e}"

    with _exec_lock:
        _execution["running"] = False
        _execution["done"] = True

def _messages_to_outputs(messages):
    outputs = []
    stream_buf = {}
    def flush():
        for name, text in stream_buf.items():
            outputs.append({"output_type": "stream", "name": name, "text": text})
        stream_buf.clear()
    for d in messages:
        mtype = d.get("msg_type"); c = d.get("content", {})
        if mtype == "stream":
            n = c.get("name", "stdout")
            stream_buf[n] = stream_buf.get(n, "") + c.get("text", "")
        elif mtype == "execute_result":
            flush()
            outputs.append({"output_type": "execute_result",
                            "execution_count": c.get("execution_count"),
                            "data": c.get("data", {}), "metadata": {}})
        elif mtype == "display_data":
            flush()
            outputs.append({"output_type": "display_data",
                            "data": c.get("data", {}), "metadata": {}})
        elif mtype == "error":
            flush()
            outputs.append({"output_type": "error", "ename": c.get("ename", ""),
                            "evalue": c.get("evalue", ""),
                            "traceback": c.get("traceback", [])})
    flush()
    return outputs

_exec_count = 0
_auto_starting = False
_kernel_plot_setup_done = False

_PLOT_SETUP_CODE = """\
try:
    from IPython import get_ipython as _gip
    _ip = _gip()
    if _ip:
        _ip.run_line_magic('matplotlib', 'inline')
except Exception:
    pass
"""

# ---------------------------------------------------------------------------
# Flask routes — notebook
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/server-url", methods=["GET"])
def api_get_url():
    return jsonify({"url": SERVER_URL})

@app.route("/api/kernel/stop", methods=["POST"])
def api_kernel_stop():
    try:
        kid = _get_kernel_id()
        r = requests.delete(f"{SERVER_URL}/api/kernels/{kid}", headers=_headers())
        r.raise_for_status()
        return jsonify({"stopped": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/server-url", methods=["POST"])
def api_set_url():
    global SERVER_URL, _kernel_plot_setup_done
    url = request.json.get("url", "").strip().rstrip("/")
    if not url:
        return jsonify({"error": "empty url"}), 400
    SERVER_URL = url
    _kernel_plot_setup_done = False  # re-run plot setup on new session
    # Derive and switch to the active cc- slug in background
    threading.Thread(target=_refresh_active_slug, daemon=True).start()
    return jsonify({"ok": True})

@app.route("/api/active-slug", methods=["GET"])
def api_active_slug():
    return jsonify({"slug": ACTIVE_SLUG})

def _refresh_active_slug():
    try:
        from kaggle_selenium import _get_active_slug
        slug = _get_active_slug()
        if slug:
            _set_active_slug(slug)
    except Exception as e:
        print(f"[slug] refresh failed: {e}")


@app.route("/api/fetch-kaggle-url", methods=["POST"])
def api_fetch_kaggle_url():
    """Start Kaggle Jupyter Server via headless Firefox and return JWT proxy URL."""
    global SERVER_URL
    try:
        from kaggle_selenium import fetch_jwt_url, _get_active_slug
        slug = _get_active_slug()
        if not slug:
            return jsonify({"error": f"No notebook with '{CC_PREFIX}' prefix found in your Kaggle account"}), 404
        url = fetch_jwt_url(kernel_slug=slug)
    except Exception as e:
        print(f"[selenium] import/run error: {e}")
        url, slug = None, ""
    if url:
        SERVER_URL = url
        _set_active_slug(slug)
        return jsonify({"url": url, "slug": slug})
    return jsonify({"error": "Could not start session — run kaggle_login.py first"}), 503

EMPTY_NOTEBOOK = {
    "nbformat": 4, "nbformat_minor": 5,
    "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                 "language_info": {"name": "python"}},
    "cells": [],
}

@app.route("/api/notebook")
def api_notebook():
    if not SERVER_URL:
        if _auto_starting:
            return jsonify({"auto_starting": True, "cells": []}), 200
        return jsonify({"error": "No Kaggle URL set. Tap ⚙ to configure.", "cells": []}), 200
    try:
        return jsonify(_read_nb())
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            _write_nb(EMPTY_NOTEBOOK)
            return jsonify(EMPTY_NOTEBOOK)
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/notebook/download")
def api_download():
    nb = _read_nb()
    return Response(
        json.dumps(nb, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename={NOTEBOOK}"}
    )

@app.route("/api/cell", methods=["POST"])
def api_add_cell():
    data = request.json
    nb = _read_nb()
    cell_type = data.get("type", "code")
    cell = {
        "cell_type": cell_type,
        "id": str(uuid.uuid4())[:8],
        "metadata": {},
        "source": data.get("source", ""),
    }
    if cell_type == "code":
        cell["execution_count"] = None
        cell["outputs"] = []
    idx = data.get("index", -1)
    if idx == -1:
        nb["cells"].append(cell)
        pos = len(nb["cells"]) - 1
    else:
        nb["cells"].insert(idx, cell)
        pos = idx
    _write_nb(nb)
    return jsonify({"index": pos})

@app.route("/api/cell/<int:idx>", methods=["PUT"])
def api_edit_cell(idx):
    data = request.json
    nb = _read_nb()
    nb["cells"][idx]["source"] = data.get("source", "")
    nb["cells"][idx]["outputs"] = []
    nb["cells"][idx]["execution_count"] = None
    _write_nb(nb)
    return jsonify({"ok": True})

@app.route("/api/cell/<int:idx>", methods=["DELETE"])
def api_delete_cell(idx):
    nb = _read_nb()
    nb["cells"].pop(idx)
    _write_nb(nb)
    return jsonify({"ok": True})

@app.route("/api/cell/<int:idx>/run", methods=["POST"])
def api_run_cell(idx):
    with _exec_lock:
        if _execution["running"]:
            return jsonify({"error": "A cell is already running. Wait for it to finish."}), 409
    nb = _read_nb()
    cell = nb["cells"][idx]
    if cell["cell_type"] != "code":
        return jsonify({"error": "not a code cell"}), 400
    code = "".join(cell["source"])
    global _kernel_plot_setup_done
    if not _kernel_plot_setup_done:
        _kernel_plot_setup_done = True
        code = _PLOT_SETUP_CODE + "\n" + code
    with _exec_lock:
        _execution.update({"running": True, "cell_idx": idx,
                           "output": "", "done": False, "error": None})
    t = threading.Thread(target=_run_cell_background, args=(idx, code))
    t.daemon = True
    t.start()
    return jsonify({"started": True, "cell_idx": idx})

@app.route("/api/execution/status")
def api_execution_status():
    with _exec_lock:
        return jsonify(dict(_execution))

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Flask routes — Kaggle credentials + datasets
# ---------------------------------------------------------------------------

def _load_creds():
    if os.path.exists(CREDS_FILE):
        with open(CREDS_FILE) as f:
            return json.load(f)
    return {}

def _save_creds(username, key):
    with open(CREDS_FILE, "w") as f:
        json.dump({"username": username, "key": key}, f)

def _kernel_exec(code, timeout=600):
    """Run code on the Kaggle kernel, return stdout text."""
    kernel_id = _get_kernel_id()
    ws_url = (SERVER_URL.replace("https://", "wss://").replace("http://", "ws://")
              + f"/api/kernels/{kernel_id}/channels")
    msg_id = str(uuid.uuid4())
    msg = {
        "header": {"msg_id": msg_id, "msg_type": "execute_request",
                   "username": "claude", "session": str(uuid.uuid4()),
                   "date": "", "version": "5.3"},
        "parent_header": {}, "metadata": {},
        "content": {"code": code, "silent": False, "store_history": False,
                    "user_expressions": {}, "allow_stdin": False},
        "channel": "shell",
    }
    out = []; done = threading.Event()
    def on_open(ws): ws.send(json.dumps(msg))
    def on_message(ws, raw):
        d = json.loads(raw)
        if d.get("parent_header", {}).get("msg_id") != msg_id: return
        if d.get("msg_type") == "stream": out.append(d["content"].get("text", ""))
        if d.get("msg_type") == "error":
            c = d["content"]
            out.append(f"ERROR: {c.get('ename')}: {c.get('evalue')}\n")
        if d.get("msg_type") == "status" and d["content"].get("execution_state") == "idle":
            done.set()
    ws = websocket.WebSocketApp(ws_url, on_open=on_open, on_message=on_message)
    t = threading.Thread(target=ws.run_forever); t.daemon = True; t.start()
    done.wait(timeout=timeout); ws.close()
    return "".join(out)

@app.route("/api/credentials", methods=["GET"])
def api_get_creds():
    creds = _load_creds()
    return jsonify({"username": creds.get("username", ""), "has_key": bool(creds.get("key"))})

@app.route("/api/credentials", methods=["POST"])
def api_save_creds():
    data = request.json
    username = data.get("username", "").strip()
    key = data.get("key", "").strip()
    if not username or not key:
        return jsonify({"error": "username and key required"}), 400
    _save_creds(username, key)
    return jsonify({"ok": True})

@app.route("/api/datasets", methods=["GET"])
def api_list_datasets():
    code = f"""
import os, json
d = '/kaggle/working/{DATASETS_DIR}'
if os.path.exists(d):
    result = {{}}
    for name in os.listdir(d):
        path = os.path.join(d, name)
        if os.path.isdir(path):
            files = os.listdir(path)
            result[name] = files
    print(json.dumps(result))
else:
    print(json.dumps({{}}))
"""
    try:
        out = _kernel_exec(code, timeout=15)
        # find the JSON in output
        for line in out.strip().splitlines():
            try:
                return jsonify(json.loads(line))
            except Exception:
                continue
        return jsonify({})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/datasets/download", methods=["POST"])
def api_download_dataset():
    slug = request.json.get("slug", "").strip()  # e.g. "heptapod/titanic"
    if not slug:
        return jsonify({"error": "dataset slug required"}), 400
    creds = _load_creds()
    if not creds:
        return jsonify({"error": "No Kaggle credentials saved. Add them via ⚙ Datasets first."}), 400

    code = f"""
import os, json, subprocess

# Write credentials
os.makedirs('/root/.kaggle', exist_ok=True)
with open('/root/.kaggle/kaggle.json', 'w') as f:
    json.dump({{"username": "{creds['username']}", "key": "{creds['key']}"}}, f)
os.chmod('/root/.kaggle/kaggle.json', 0o600)

# Download dataset
dest = '/kaggle/working/{DATASETS_DIR}/{slug.split('/')[-1]}'
os.makedirs(dest, exist_ok=True)
result = subprocess.run(
    ['kaggle', 'datasets', 'download', '-d', '{slug}', '--unzip', '-p', dest],
    capture_output=True, text=True
)
print(result.stdout)
print(result.stderr)
print('FILES:', os.listdir(dest))
"""
    try:
        out = _kernel_exec(code, timeout=300)
        return jsonify({"output": out, "slug": slug})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Flask routes — Knowledge Base
# ---------------------------------------------------------------------------

@app.route("/api/kb", methods=["GET"])
def api_kb_list():
    files = []
    for name in sorted(os.listdir(KB_DIR)):
        path = os.path.join(KB_DIR, name)
        if os.path.isfile(path):
            files.append({"name": name, "size": os.path.getsize(path)})
    return jsonify(files)

@app.route("/api/kb/upload", methods=["POST"])
def api_kb_upload():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "No file provided"}), 400
    name = os.path.basename(f.filename)
    f.save(os.path.join(KB_DIR, name))
    return jsonify({"ok": True, "name": name})

@app.route("/api/kb/<path:filename>/download", methods=["GET"])
def api_kb_download(filename):
    return send_from_directory(KB_DIR, os.path.basename(filename), as_attachment=True)

@app.route("/api/kb/<path:filename>/view", methods=["GET"])
def api_kb_view(filename):
    path = os.path.join(KB_DIR, os.path.basename(filename))
    if not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404
    try:
        with open(path, "r", errors="ignore") as f:
            content = f.read()
        return jsonify({"content": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/kb/<path:filename>", methods=["DELETE"])
def api_kb_delete(filename):
    path = os.path.join(KB_DIR, os.path.basename(filename))
    if os.path.exists(path):
        os.remove(path)
    return jsonify({"ok": True})

# Flask routes — Claude
# ---------------------------------------------------------------------------

def _build_kb_context() -> str:
    parts = []
    for name in sorted(os.listdir(KB_DIR)):
        path = os.path.join(KB_DIR, name)
        if not os.path.isfile(path):
            continue
        if _active_kb_files is not None and name not in _active_kb_files:
            continue
        try:
            with open(path, "r", errors="ignore") as fh:
                content = fh.read(20000)  # cap at 20k chars per file
            parts.append(f"=== {name} ===\n{content}")
        except Exception:
            pass
    return "\n\n".join(parts) if parts else "(none)"

def _build_context(prompt: str) -> str:
    """Prepend notebook state and tool instructions to the user prompt."""
    url = SERVER_URL
    creds = _load_creds()
    try:
        nb = _read_nb()
        cells = nb.get("cells", [])
        cell_lines = []
        for i, cell in enumerate(cells):
            src = "".join(cell["source"])
            ec = cell.get("execution_count")
            tag = f"[{ec}]" if ec else "[ ]"
            ctype = cell["cell_type"]
            outputs = cell.get("outputs", [])
            out_text = ""
            if outputs:
                parts = []
                for o in outputs:
                    if o.get("output_type") == "stream":
                        parts.append(o.get("text", ""))
                    elif o.get("output_type") in ("execute_result", "display_data"):
                        parts.append(o.get("data", {}).get("text/plain", ""))
                    elif o.get("output_type") == "error":
                        parts.append(f"ERROR: {o.get('ename')}: {o.get('evalue')}")
                out_text = "\n  OUTPUT:\n" + "".join(parts).strip()[:400]
            cell_lines.append(
                f"--- Cell {i} ({ctype}) {tag} ---\n{src.strip()}{out_text}"
            )
        cells_summary = "\n\n".join(cell_lines) if cell_lines else "(no cells yet)"
    except Exception as e:
        cells_summary = f"(could not read notebook: {e})"

    return f"""You are an autonomous agent controlling a Kaggle Jupyter notebook from Termux on Android.

## Your job
Act immediately on the user's request using the bash commands below.
Do NOT ask for clarification unless the request is genuinely ambiguous.
Do NOT ask for permission — you already have it.
Do NOT re-read files you were not explicitly asked to read.
Do NOT write helper scripts — execute kaggle_client.py commands directly via bash tool calls.

## Token efficiency rules
- The notebook state is fully provided below — do NOT read it again via tools.
- Only read files explicitly mentioned in the user's request.
- Do NOT speculatively read files for context.
- Do NOT re-read a file already read in this session unless it was modified.
- Prefer targeted edits over full rewrites.

## Kaggle server URL (use this literal value in all commands)
{url}

## Available commands

# List / inspect
python3 {REPO_DIR}/kaggle_client.py --url "{url}" list
python3 {REPO_DIR}/kaggle_client.py --url "{url}" show <index>
python3 {REPO_DIR}/kaggle_client.py --url "{url}" delete <index>
python3 {REPO_DIR}/kaggle_client.py --url "{url}" run <index>
python3 {REPO_DIR}/kaggle_client.py --url "{url}" run-all

# Adding / editing cells — ALWAYS use heredoc to avoid escaping issues.
# Pass "-" as the source argument and pipe code via stdin.
# The <<'PYEOF' delimiter (quoted) prevents ALL shell substitution inside.
python3 {REPO_DIR}/kaggle_client.py --url "{url}" add - <<'PYEOF'
# your Python code here — any quotes, backslashes, f-strings are safe
PYEOF

python3 {REPO_DIR}/kaggle_client.py --url "{url}" add --type markdown - <<'PYEOF'
## Markdown heading
PYEOF

python3 {REPO_DIR}/kaggle_client.py --url "{url}" edit <index> - <<'PYEOF'
# replacement code here
PYEOF

# exec (ad-hoc, not saved) — use heredoc for anything non-trivial
python3 {REPO_DIR}/kaggle_client.py --url "{url}" exec - <<'PYEOF'
print("hello")
PYEOF

# NEVER create temporary .py files. NEVER use echo/printf to pipe code.
# NEVER pass multi-line code as a quoted string argument.

## Kaggle datasets (available at /kaggle/working/datasets/<name>/)
Kaggle credentials are already saved. To write them to the kernel run this first:
  python3 {REPO_DIR}/kaggle_client.py --url "{url}" exec "import os,json; os.makedirs('/root/.kaggle',exist_ok=True); open('/root/.kaggle/kaggle.json','w').write(json.dumps({{'username':'{creds.get('username','')}','key':'{creds.get('key','')}'}})); os.chmod('/root/.kaggle/kaggle.json',0o600); print('creds written')"

To download a dataset when the user asks in natural language:
  1. Write credentials (above)
  2. Run: python3 {REPO_DIR}/kaggle_client.py --url "{url}" exec "import subprocess; print(subprocess.getoutput('kaggle datasets download -d owner/slug --unzip -p /kaggle/working/datasets/name/'))"
  3. Add a code cell that loads the data with pandas

Available datasets already on kernel: check /kaggle/working/datasets/

## Knowledge base (local files uploaded by user)
{_build_kb_context()}

## Current notebook state (complete — do not re-read)
{cells_summary}

## User request
{prompt}"""


def _build_gemini_context(prompt: str) -> str:
    """Like _build_context but with stricter shell-command formatting rules for Gemini."""
    url = SERVER_URL
    creds = _load_creds()
    try:
        nb = _read_nb()
        cells = nb.get("cells", [])
        cell_lines = []
        for i, cell in enumerate(cells):
            src = "".join(cell["source"])
            ec = cell.get("execution_count")
            tag = f"[{ec}]" if ec else "[ ]"
            ctype = cell["cell_type"]
            outputs = cell.get("outputs", [])
            out_text = ""
            if outputs:
                parts = []
                for o in outputs:
                    if o.get("output_type") == "stream":
                        parts.append(o.get("text", ""))
                    elif o.get("output_type") in ("execute_result", "display_data"):
                        parts.append(o.get("data", {}).get("text/plain", ""))
                    elif o.get("output_type") == "error":
                        parts.append(f"ERROR: {o.get('ename')}: {o.get('evalue')}")
                out_text = "\n  OUTPUT:\n" + "".join(parts).strip()[:400]
            cell_lines.append(
                f"--- Cell {i} ({ctype}) {tag} ---\n{src.strip()}{out_text}"
            )
        cells_summary = "\n\n".join(cell_lines) if cell_lines else "(no cells yet)"
    except Exception as e:
        cells_summary = f"(could not read notebook: {e})"

    return f"""You are an autonomous agent controlling a Kaggle Jupyter notebook via shell commands.

CRITICAL RULES — read carefully before every tool call:
1. Run commands EXACTLY as shown below. No extra arguments, no comments, no description fields.
2. These are SHELL COMMANDS, not Python function calls. Never append ", description=..." or any extra text.
3. Act immediately. Do not ask for clarification.
4. Do not re-read the notebook state — it is provided below.
5. Do NOT read any project files (kaggle_selenium.py, notebook_ui.py, kaggle_client.py, etc.).
6. If you get a network/connection error (NameResolutionError, ConnectionError, HTTP 5xx), STOP immediately and respond: "The Kaggle URL appears to have expired. Please tap ⚙ → Start Session Automatically to refresh it." Do not attempt to fix the connection or read any files.

Kaggle server URL (copy this exactly into every command):
{url}

SHELL COMMANDS — exact forms. Use heredoc for ALL add/edit/exec with multi-line or non-trivial code.

List / inspect / run:
  python3 {REPO_DIR}/kaggle_client.py --url "{url}" list
  python3 {REPO_DIR}/kaggle_client.py --url "{url}" show <index>
  python3 {REPO_DIR}/kaggle_client.py --url "{url}" delete <index>
  python3 {REPO_DIR}/kaggle_client.py --url "{url}" run <index>
  python3 {REPO_DIR}/kaggle_client.py --url "{url}" run-all

Add/edit/exec — ALWAYS use heredoc. Pass "-" and pipe via stdin.
The <<'PYEOF' delimiter prevents ALL shell substitution so any Python code is safe:

  python3 {REPO_DIR}/kaggle_client.py --url "{url}" add - <<'PYEOF'
  import numpy as np
  text = "hello\nworld"   # quotes, backslashes, f-strings all safe
  print(text)
  PYEOF

  python3 {REPO_DIR}/kaggle_client.py --url "{url}" edit <index> - <<'PYEOF'
  # replacement code
  PYEOF

  python3 {REPO_DIR}/kaggle_client.py --url "{url}" exec - <<'PYEOF'
  print("hello")
  PYEOF

NEVER pass multi-line code as a quoted shell argument — it breaks on string literals.
NEVER create temporary .py files.
NEVER append ", description=..." or any extra argument after the command.

Knowledge base:
{_build_kb_context()}

Current notebook state (do not re-read):
{cells_summary}

User request:
{prompt}"""


def _add_to_last_block(msg, btype, text):
    if msg["blocks"] and msg["blocks"][-1]["type"] == btype:
        msg["blocks"][-1]["text"] += text
    else:
        msg["blocks"].append({"type": btype, "text": text})

@app.route("/api/claude", methods=["POST"])
def api_claude():
    """Run claude -p <prompt> and stream the output back via SSE."""
    global _chat_started, _chat_history, _session_active
    prompt = request.json.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "empty prompt"}), 400

    is_first = not _session_active
    full_prompt = _build_context(prompt) if is_first else prompt
    _chat_started = True
    _session_active = True

    def generate():
        nonlocal prompt
        _chat_history.append({"role": "user", "text": prompt})
        _save_history(_chat_history, ACTIVE_SLUG)

        env = os.environ.copy()
        env["CLAUDE_CODE_DISABLE_UPDATES"] = "1"
        env["KAGGLE_SERVER_URL"] = SERVER_URL
        cmd = ["node", CLAUDE_CLI, "-p", full_prompt,
               "--output-format", "stream-json", "--verbose",
               "--max-turns", "50", "--include-partial-messages"]
        if not is_first:
            cmd.append("--continue")
        
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            cwd=REPO_DIR, env=env, text=True, bufsize=1,
        )
        
        current_claude_msg = {"role": "claude", "blocks": []}
        yielded_tools = set()

        for line in proc.stdout:
            line = line.rstrip("\n")
            if not line: continue
            try:
                obj = json.loads(line)
                t = obj.get("type")
                if t == "assistant":
                    for block in obj.get("message", {}).get("content", []):
                        if block.get("type") == "tool_use":
                            tool_id = block.get("id")
                            if tool_id and tool_id not in yielded_tools:
                                inp = block.get("input", {})
                                if inp:
                                    yielded_tools.add(tool_id)
                                    cmd_text = inp.get("command") or inp.get("path") or inp.get("file_path") or inp.get("prompt") or json.dumps(inp)
                                    current_claude_msg["blocks"].append({"type": "tool_call", "name": block.get("name","Tool"), "command": cmd_text})
                                    yield f"data: {json.dumps({'tool_call': {'name': block.get('name','Tool'), 'command': cmd_text}})}\n\n"
                elif t == "stream_event":
                    ev = obj.get("event", {})
                    etype = ev.get("type")
                    if etype == "content_block_delta":
                        delta = ev.get("delta", {})
                        if delta.get("type") == "text_delta":
                            txt = delta['text']
                            _add_to_last_block(current_claude_msg, "text", txt)
                            yield f"data: {json.dumps({'text': txt})}\n\n"
                        elif delta.get("type") == "thinking_delta":
                            th = delta['thinking']
                            _add_to_last_block(current_claude_msg, "thinking", th)
                            yield f"data: {json.dumps({'thinking': th})}\n\n"
                    elif etype == "message_delta":
                        usage = ev.get("usage", {})
                        if usage:
                            current_claude_msg["usage"] = usage
                            yield f"data: {json.dumps({'usage': usage})}\n\n"
                elif t == "message_stop":
                    usage = obj.get("message", {}).get("usage", {})
                    if usage:
                        current_claude_msg["usage"] = usage
                        yield f"data: {json.dumps({'usage': usage})}\n\n"
                elif t == "user":
                    for block in obj.get("message", {}).get("content", []):
                        if block.get("type") == "tool_result":
                            raw = block.get("content", "")
                            if isinstance(raw, list):
                                text = "".join(b.get("text","") for b in raw if isinstance(b,dict) and b.get("type")=="text")
                            else: text = str(raw)
                            res_text = text.strip()[:1000]
                            current_claude_msg["blocks"].append({"type": "tool_result", "text": res_text})
                            yield f"data: {json.dumps({'tool_result': res_text})}\n\n"
            except json.JSONDecodeError: pass
        
        proc.wait()
        _chat_history.append(current_claude_msg)
        _save_history(_chat_history, ACTIVE_SLUG)
        yield f"data: {json.dumps({'done': True})}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

@app.route("/api/claude/history")
def api_claude_history():
    return jsonify(_chat_history)

@app.route("/api/claude/reset", methods=["POST"])
def api_claude_reset():
    global _chat_started, _chat_history, _session_active, _gemini_session_id, _gemini_session_active
    _chat_started = False
    _session_active = False
    _gemini_session_id = None
    _gemini_session_active = False
    _chat_history = []
    f = _history_file(ACTIVE_SLUG)
    if os.path.exists(f):
        os.remove(f)
    return jsonify({"ok": True})

@app.route("/api/new-chat", methods=["POST"])
def api_new_chat():
    global _chat_started, _chat_history, _session_active, _gemini_session_id, \
           _gemini_session_active, _gemini_model, _active_kb_files
    data = request.json or {}
    _active_kb_files = data.get("kb_files")  # None = all, list = selected filenames
    _chat_started = False
    _session_active = False
    _gemini_session_id = None
    _gemini_session_active = False
    _gemini_model = GEMINI_MODEL_PREFERRED
    _chat_history = []
    f = _history_file(ACTIVE_SLUG)
    if os.path.exists(f):
        os.remove(f)
    return jsonify({"ok": True})

@app.route("/api/gemini/model")
def api_gemini_model():
    return jsonify({"model": _gemini_model})

@app.route("/api/gemini", methods=["POST"])
def api_gemini():
    """Run gemini -p <prompt> and stream the output back via SSE. Auto-falls back on quota."""
    global _chat_history, _gemini_session_id, _gemini_session_active, _gemini_model
    prompt = request.json.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "empty prompt"}), 400

    is_first = not _gemini_session_active
    full_prompt = _build_gemini_context(prompt) if is_first else prompt

    def generate():
        global _gemini_session_id, _gemini_session_active

        _chat_history.append({"role": "user", "text": prompt})
        _save_history(_chat_history, ACTIVE_SLUG)

        import re as _re
        _SKIP_LINES = ("YOLO mode", "Ripgrep is not available", "Falling back to")

        env = os.environ.copy()
        env["KAGGLE_SERVER_URL"] = SERVER_URL
        # No -m flag: all explicit model names fail on free tier; CLI default works
        cmd = ["gemini", "-p", full_prompt, "--output-format", "stream-json", "--yolo"]
        if not is_first and _gemini_session_id:
            cmd += ["--resume", _gemini_session_id]

        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            cwd=REPO_DIR, env=env, text=True, bufsize=1,
        )

        current_msg = {"role": "gemini", "blocks": []}
        pending_tools = {}
        active_model = "gemini"

        for line in proc.stdout:
            line = line.rstrip("\n")
            if not line: continue
            try:
                obj = json.loads(line)
                t = obj.get("type")
                if t == "init":
                    sid = obj.get("session_id")
                    active_model = obj.get("model", active_model)
                    _gemini_model = active_model
                    if sid and not _gemini_session_id:
                        _gemini_session_id = sid
                        _gemini_session_active = True
                elif t == "tool_use":
                    name = obj.get("tool_name", "Tool")
                    tool_id = obj.get("tool_id", "")
                    if name == "update_topic":
                        continue
                    params = obj.get("parameters", {})
                    cmd_text = (params.get("command") or params.get("cmd") or
                                params.get("file_path") or params.get("dir_path") or
                                params.get("path") or params.get("query") or
                                json.dumps(params))
                    idx = len(current_msg["blocks"])
                    pending_tools[tool_id] = idx
                    current_msg["blocks"].append({"type": "tool_call", "name": name, "command": cmd_text})
                    yield f"data: {json.dumps({'tool_call': {'name': name, 'command': cmd_text}})}\n\n"
                elif t == "tool_result":
                    tool_id = obj.get("tool_id", "")
                    output = (obj.get("output") or obj.get("result") or "")
                    if isinstance(output, dict):
                        output = json.dumps(output)
                    res_text = str(output).strip()[:1000]
                    if tool_id in pending_tools:
                        current_msg["blocks"].append({"type": "tool_result", "text": res_text})
                    yield f"data: {json.dumps({'tool_result': res_text})}\n\n"
                elif t == "message" and obj.get("role") == "assistant":
                    text = obj.get("content", "")
                    if text:
                        if obj.get("thought"):
                            if current_msg["blocks"] and current_msg["blocks"][-1]["type"] == "thinking":
                                current_msg["blocks"][-1]["text"] += text
                            else:
                                current_msg["blocks"].append({"type": "thinking", "text": text})
                            yield f"data: {json.dumps({'thinking': text})}\n\n"
                        else:
                            if current_msg["blocks"] and current_msg["blocks"][-1]["type"] == "text":
                                current_msg["blocks"][-1]["text"] += text
                            else:
                                current_msg["blocks"].append({"type": "text", "text": text})
                            yield f"data: {json.dumps({'text': text})}\n\n"
                elif t == "result":
                    stats = obj.get("stats", {})
                    usage = {
                        "input_tokens": stats.get("input_tokens", 0),
                        "output_tokens": stats.get("output_tokens", 0),
                    }
                    if stats.get("cached"):
                        usage["cache_read_tokens"] = stats["cached"]
                    current_msg["usage"] = usage
                    yield f"data: {json.dumps({'usage': usage})}\n\n"
            except json.JSONDecodeError:
                if any(s in line for s in _SKIP_LINES):
                    continue
                stripped = line.strip()
                if (stripped.startswith("at ") or stripped in ("{", "}", "")
                        or _re.match(r"^\s*(cause|code|message|details|retryDelayMs|reason)\s*:", stripped)):
                    continue
                print(f"[gemini] {stripped[:300]}")
                # Extract readable error; highlight quota exhaustion with reset time
                m_quota = _re.search(r"reset after\s+([\dhms]+)", stripped)
                m_err = _re.search(r"(\w+Error):\s*(.+?)(?:\.\s|$)", stripped)
                if m_quota:
                    err_text = f"⚠ Quota exhausted — resets in {m_quota.group(1)}"
                elif m_err:
                    err_text = f"⚠ {m_err.group(1)}: {m_err.group(2).rstrip('.')}"
                else:
                    err_text = f"⚠ {stripped[:300]}"
                current_msg["blocks"].append({"type": "text", "text": err_text})
                yield f"data: {json.dumps({'text': err_text})}\n\n"

        proc.wait()
        _chat_history.append(current_msg)
        _save_history(_chat_history, ACTIVE_SLUG)
        yield f"data: {json.dumps({'done': True, 'active_model': active_model})}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})

@app.route("/api/gemini/reset", methods=["POST"])
def api_gemini_reset():
    global _gemini_session_id, _gemini_session_active, _gemini_model
    _gemini_session_id = None
    _gemini_session_active = False
    _gemini_model = GEMINI_MODEL_PREFERRED
    return jsonify({"ok": True})

@app.route("/api/md", methods=["POST"])
def api_md():
    text = request.json.get("text", "")
    html = md_lib.markdown(text, extensions=["fenced_code"])
    return jsonify({"html": html})

# ---------------------------------------------------------------------------
# HTML / JS frontend
# ---------------------------------------------------------------------------
HTML = NEW_HTML
# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _auto_start_session():
    """On startup: if no SERVER_URL, auto-activate the cc- notebook in background."""
    global SERVER_URL, _auto_starting
    import time
    time.sleep(2)  # let Flask finish starting
    if SERVER_URL:
        _refresh_active_slug()
        return
    print("[startup] No SERVER_URL set — auto-starting Kaggle session...")
    _auto_starting = True
    try:
        from kaggle_selenium import fetch_jwt_url, _get_active_slug
        slug = _get_active_slug()
        if not slug:
            print(f"[startup] No '{CC_PREFIX}' notebook found — rename a Kaggle notebook to start with '{CC_PREFIX}'")
            return
        url = fetch_jwt_url(kernel_slug=slug)
        if url:
            SERVER_URL = url
            _set_active_slug(slug)
            print(f"[startup] Session started: {slug}")
        else:
            print("[startup] Failed to start session — run kaggle_login.py first")
    except Exception as e:
        print(f"[startup] Auto-start error: {e}")
    finally:
        _auto_starting = False

if __name__ == "__main__":
    print("Open http://localhost:5000 in your browser")
    threading.Thread(target=_auto_start_session, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
