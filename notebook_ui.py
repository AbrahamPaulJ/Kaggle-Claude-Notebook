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
from flask import Flask, jsonify, request, render_template_string, Response

SERVER_URL   = os.environ.get("KAGGLE_SERVER_URL", "")
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
    global ACTIVE_SLUG, _chat_history, _chat_started
    if slug == ACTIVE_SLUG:
        return
    if ACTIVE_SLUG:
        _save_history(_chat_history, ACTIVE_SLUG)
    ACTIVE_SLUG = slug
    _chat_history = _load_history(slug)
    _chat_started = len(_chat_history) > 0
    print(f"[slug] switched to {slug!r}, {len(_chat_history)} messages in history")

_chat_history = _load_history(ACTIVE_SLUG)
_chat_started = len(_chat_history) > 0

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

# ---------------------------------------------------------------------------
# Flask routes — notebook
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/server-url", methods=["GET"])
def api_get_url():
    return jsonify({"url": SERVER_URL})

@app.route("/api/server-url", methods=["POST"])
def api_set_url():
    global SERVER_URL
    url = request.json.get("url", "").strip().rstrip("/")
    if not url:
        return jsonify({"error": "empty url"}), 400
    SERVER_URL = url
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
python3 {REPO_DIR}/kaggle_client.py --url "{url}" list
python3 {REPO_DIR}/kaggle_client.py --url "{url}" show <index>
python3 {REPO_DIR}/kaggle_client.py --url "{url}" add "code here"
python3 {REPO_DIR}/kaggle_client.py --url "{url}" edit <index> "new code"
python3 {REPO_DIR}/kaggle_client.py --url "{url}" delete <index>
python3 {REPO_DIR}/kaggle_client.py --url "{url}" run <index>
python3 {REPO_DIR}/kaggle_client.py --url "{url}" run-all
python3 {REPO_DIR}/kaggle_client.py --url "{url}" exec "print('hello')"

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


def _add_to_last_block(msg, btype, text):
    if msg["blocks"] and msg["blocks"][-1]["type"] == btype:
        msg["blocks"][-1]["text"] += text
    else:
        msg["blocks"].append({"type": btype, "text": text})

@app.route("/api/claude", methods=["POST"])
def api_claude():
    """Run claude -p <prompt> and stream the output back via SSE."""
    global _chat_started, _chat_history
    prompt = request.json.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "empty prompt"}), 400

    is_first = not _chat_started
    full_prompt = _build_context(prompt) if is_first else prompt
    _chat_started = True

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
    global _chat_started, _chat_history
    _chat_started = False
    _chat_history = []
    f = _history_file(ACTIVE_SLUG)
    if os.path.exists(f):
        os.remove(f)
    return jsonify({"ok": True})

@app.route("/api/md", methods=["POST"])
def api_md():
    text = request.json.get("text", "")
    html = md_lib.markdown(text, extensions=["fenced_code"])
    return jsonify({"html": html})

# ---------------------------------------------------------------------------
# HTML / JS frontend
# ---------------------------------------------------------------------------

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Kaggle Notebook</title>
<style>
:root {
  --navy: #1a1a2e;
  --purple: #6c3fd4;
  --green: #27ae60;
  --red: #e74c3c;
  --bg: #f0f2f5;
  --card: #ffffff;
  --border: #e0e0e0;
  --text: #1a1a2e;
  --muted: #888;
  --tab-h: 60px;
  --header-h: 52px;
}
* { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
html, body { height: 100%; overflow: hidden; background: var(--bg); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: var(--text); }

/* ── Header ── */
#header {
  position: fixed; top: 0; left: 0; right: 0; height: var(--header-h);
  background: var(--navy); color: #fff; display: flex; align-items: center;
  padding: 0 14px; gap: 10px; z-index: 50;
  box-shadow: 0 2px 8px #0004;
}
#header h1 { font-size: 0.9rem; font-weight: 700; flex: 1; letter-spacing: 0.01em; }
#kernel-dot { width: 8px; height: 8px; border-radius: 50%; background: #888; flex-shrink: 0; transition: background 0.4s; }
#kernel-dot.idle { background: var(--green); }
#kernel-dot.busy { background: #f39c12; animation: pulse 1s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
#status-text { font-size: 0.7rem; color: #aaa; flex: 1; text-align: right; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 160px; }
.icon-btn { background: none; border: none; color: #fff; font-size: 1.2rem; padding: 6px; cursor: pointer; opacity: 0.8; }
.icon-btn:active { opacity: 1; }

/* ── Tab bar ── */
#tabbar {
  position: fixed; bottom: 0; left: 0; right: 0; height: var(--tab-h);
  background: var(--card); border-top: 1px solid var(--border);
  display: flex; z-index: 50;
  box-shadow: 0 -2px 10px #0002;
}
.tab { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;
       gap: 3px; font-size: 0.65rem; color: var(--muted); cursor: pointer; transition: color 0.2s; padding: 6px 0; }
.tab .tab-icon { font-size: 1.3rem; }
.tab.active { color: var(--purple); }
.tab.active .tab-icon { filter: drop-shadow(0 0 4px #6c3fd488); }

/* ── Content area ── */
#content { position: fixed; top: var(--header-h); bottom: var(--tab-h); left: 0; right: 0; overflow: hidden; }
.tab-page { position: absolute; inset: 0; overflow-y: auto; -webkit-overflow-scrolling: touch; display: none; flex-direction: column; }
.tab-page.active { display: flex; }

/* ── Notebook tab ── */
#page-notebook { padding: 10px 10px 80px; gap: 10px; }
.cell { background: var(--card); border-radius: 12px; overflow: hidden; box-shadow: 0 1px 4px #0001; border: 1.5px solid var(--border); transition: border-color 0.2s; }
.cell.running { border-color: #f39c12; }
.cell.done-flash { border-color: var(--green); }
.cell-header { display: flex; align-items: center; gap: 6px; padding: 8px 10px; background: #fafafa; border-bottom: 1px solid var(--border); }
.cell-badge { font-size: 0.65rem; background: #eee; padding: 2px 7px; border-radius: 10px; color: #555; font-weight: 600; }
.cell-badge.md { background: #e8f4fd; color: #2980b9; }
.exec-count { font-size: 0.7rem; color: var(--muted); min-width: 24px; }
.cell-actions { margin-left: auto; display: flex; gap: 4px; }
.cell-actions button { border: none; border-radius: 8px; padding: 5px 10px; font-size: 0.78rem; cursor: pointer; font-weight: 600; }
.btn-run { background: var(--green); color: #fff; }
.btn-edit { background: #eee; color: #555; }
.btn-del { background: #fdecea; color: var(--red); }
.cell-source { font-family: "Courier New", monospace; font-size: 0.78rem; padding: 10px 12px;
               white-space: pre-wrap; word-break: break-word; line-height: 1.5; min-height: 32px; outline: none; }
.cell-source[contenteditable=true] { background: #fffde7; }
.cell-output { border-top: 1px solid var(--border); padding: 8px 12px; font-family: "Courier New", monospace;
               font-size: 0.75rem; white-space: pre-wrap; word-break: break-word; max-height: 300px; overflow-y: auto; }
.out-stream { color: #222; }
.out-result { color: var(--navy); font-weight: 500; }
.out-error { color: var(--red); background: #fff5f5; padding: 6px; border-radius: 6px; display: block; }
.cell-markdown .cell-source { font-family: sans-serif; display: none; }
.cell-markdown .rendered { padding: 10px 12px; font-size: 0.88rem; line-height: 1.6; }
.cell-markdown .rendered h1,.cell-markdown .rendered h2,.cell-markdown .rendered h3 { margin: 4px 0 6px; }
.cell-markdown .rendered p { margin-bottom: 5px; }
.cell-markdown .rendered code { background: #f0f0f0; padding: 1px 4px; border-radius: 3px; font-size:0.8rem; }
#empty-cells { text-align: center; color: var(--muted); padding: 48px 20px; font-size: 0.9rem; }

/* ── FAB ── */
#fab { position: fixed; right: 18px; bottom: calc(var(--tab-h) + 14px); width: 52px; height: 52px;
       background: var(--navy); color: #fff; border: none; border-radius: 50%; font-size: 1.5rem;
       display: flex; align-items: center; justify-content: center; cursor: pointer; z-index: 40;
       box-shadow: 0 4px 14px #0003; transition: transform 0.2s; }
#fab:active { transform: scale(0.93); }
#fab.hidden { display: none; }

/* ── Add cell sheet ── */
#add-sheet { position: fixed; left: 0; right: 0; bottom: var(--tab-h); background: var(--card);
             border-top: 2px solid var(--border); padding: 14px; z-index: 45; display: none;
             flex-direction: column; gap: 10px; box-shadow: 0 -4px 20px #0002; border-radius: 16px 16px 0 0; }
#add-sheet.open { display: flex; }
#add-sheet textarea { font-family: monospace; font-size: 0.82rem; padding: 8px; border: 1px solid var(--border);
                      border-radius: 8px; resize: none; height: 90px; outline: none; }
#add-sheet textarea:focus { border-color: var(--purple); }
.sheet-row { display: flex; gap: 8px; }
.sheet-row select { flex: 1; padding: 8px; border: 1px solid var(--border); border-radius: 8px; font-size: 0.82rem; background: #fff; }
.sheet-row button { padding: 8px 18px; border: none; border-radius: 8px; font-size: 0.82rem; font-weight: 600; cursor: pointer; }
.btn-cancel { background: #eee; color: #555; }
.btn-add { background: var(--navy); color: #fff; }
.btn-run-all { background: var(--green); color: #fff; }

/* ── Notebook toolbar ── */
#notebook-toolbar { display: flex; gap: 8px; padding: 10px 10px 0; flex-wrap: wrap; }
#notebook-toolbar button { padding: 7px 14px; border: none; border-radius: 8px; font-size: 0.8rem;
                           font-weight: 600; cursor: pointer; }

/* ── Chat tab ── */
#page-chat { flex-direction: column; }
#chat-messages { flex: 1; overflow-y: auto; -webkit-overflow-scrolling: touch; padding: 12px 12px 8px; display: flex; flex-direction: column; gap: 10px; }
.msg { max-width: 88%; word-break: break-word; line-height: 1.5; }
.msg-user { align-self: flex-end; }
.msg-user .bubble { background: var(--purple); color: #fff; border-radius: 18px 18px 4px 18px; padding: 10px 14px; font-size: 0.85rem; }
.msg-claude { align-self: flex-start; }
.msg-claude .bubble { background: var(--card); border: 1px solid var(--border); border-radius: 18px 18px 18px 4px; padding: 10px 14px; font-size: 0.85rem; white-space: pre-wrap; box-shadow: 0 1px 4px #0001; }
.thinking-block { font-style: italic; color: #666; font-size: 0.8rem; margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px dashed #eee; display: block; white-space: pre-wrap; }
.thinking-block::before { content: "💭 Thinking... "; font-weight: bold; font-style: normal; }
.msg-meta { font-size: 0.65rem; color: var(--muted); margin-top: 3px; padding: 0 4px; }
.msg-user .msg-meta { text-align: right; }

/* Tool call blocks */
.tool-block { background: #0d1117; color: #e6edf3; border-radius: 8px; padding: 8px 10px; margin: 6px 0; font-family: "Courier New", monospace; font-size: 0.73rem; border-left: 3px solid var(--purple); }
.tool-name { color: #a371f7; font-weight: bold; margin-bottom: 4px; font-size: 0.72rem; }
.tool-cmd { color: #7ee787; white-space: pre-wrap; word-break: break-all; }
.tool-result-text { color: #b0b8c1; border-top: 1px solid #30363d; margin-top: 6px; padding-top: 6px; white-space: pre-wrap; word-break: break-word; }
.tool-result-text.pending { color: #555; font-style: italic; }

/* Typing indicator */
.typing-bubble { display: flex; gap: 5px; align-items: center; padding: 12px 16px; }
.typing-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--muted); animation: bounce 1.2s infinite ease-in-out; }
.typing-dot:nth-child(1) { animation-delay: 0s; }
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%,80%,100%{transform:translateY(0)} 40%{transform:translateY(-7px)} }

#chat-input-area { padding: 8px 10px; background: var(--card); border-top: 1px solid var(--border); display: flex; gap: 8px; align-items: flex-end; flex-shrink: 0; }
#chat-input { flex: 1; padding: 10px 14px; border: 1.5px solid var(--border); border-radius: 20px; font-size: 0.85rem; resize: none; max-height: 120px; outline: none; line-height: 1.4; font-family: inherit; }
#chat-input:focus { border-color: var(--purple); }
#chat-send { width: 42px; height: 42px; border-radius: 50%; background: var(--purple); border: none; color: #fff; font-size: 1.1rem; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: transform 0.15s; }
#chat-send:active { transform: scale(0.92); }
#chat-send:disabled { background: #ccc; }

/* ── Data tab ── */
#page-data { padding: 12px 12px 80px; gap: 12px; }
.data-card { background: var(--card); border-radius: 12px; padding: 14px; box-shadow: 0 1px 4px #0001; border: 1px solid var(--border); display: flex; flex-direction: column; gap: 10px; }
.data-card h3 { font-size: 0.85rem; font-weight: 700; color: var(--navy); }
.data-card input { padding: 9px 12px; border: 1.5px solid var(--border); border-radius: 8px; font-size: 0.83rem; width: 100%; outline: none; }
.data-card input:focus { border-color: var(--purple); }
.data-card input[type=password] { font-family: monospace; }
.data-btn { padding: 10px; border: none; border-radius: 8px; font-size: 0.83rem; font-weight: 600; cursor: pointer; width: 100%; }
.data-btn.primary { background: var(--navy); color: #fff; }
.data-btn.purple { background: var(--purple); color: #fff; }
#ds-output { font-family: monospace; font-size: 0.72rem; white-space: pre-wrap; background: #f5f5f5;
             padding: 8px; border-radius: 6px; max-height: 140px; overflow-y: auto; display: none; }
.ds-item { padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 0.8rem; }
.ds-item:last-child { border-bottom: none; }
.ds-item strong { display: block; margin-bottom: 3px; }
.ds-file { color: var(--muted); font-size: 0.75rem; }

/* ── Modals ── */
.modal-overlay { position: fixed; inset: 0; background: #0007; z-index: 100; display: none; align-items: flex-end; justify-content: center; }
.modal-overlay.open { display: flex; }
.modal-sheet { background: var(--card); border-radius: 20px 20px 0 0; width: 100%; max-height: 80vh; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 12px; }
.modal-handle { width: 36px; height: 4px; background: var(--border); border-radius: 2px; margin: 0 auto 4px; }
.modal-title { font-weight: 700; font-size: 0.95rem; }
.modal-sheet input, .modal-sheet textarea { padding: 9px 12px; border: 1.5px solid var(--border); border-radius: 8px; font-size: 0.83rem; width: 100%; outline: none; }
.modal-sheet input:focus, .modal-sheet textarea:focus { border-color: var(--purple); }
.modal-sheet label { font-size: 0.78rem; color: var(--muted); margin-bottom: -6px; }
.modal-row { display: flex; gap: 8px; }
.modal-row button { flex: 1; padding: 10px; border: none; border-radius: 8px; font-size: 0.83rem; font-weight: 600; cursor: pointer; }
.btn-primary { background: var(--navy); color: #fff; }
.btn-ghost { background: #eee; color: #555; }
</style>
</head>
<body>

<!-- Header -->
<div id="header">
  <div id="kernel-dot"></div>
  <h1>📓 Kaggle Notebook</h1>
  <span id="status-text">loading…</span>
  <button class="icon-btn" onclick="openUrlModal()" title="Change URL">⚙</button>
</div>

<!-- Content -->
<div id="content">

  <!-- Notebook tab -->
  <div id="page-notebook" class="tab-page active">
    <div id="notebook-toolbar">
      <button style="background:var(--green);color:#fff;" onclick="runAll()">▶ Run All</button>
      <button style="background:#eee;color:#333;" onclick="downloadNotebook()">⬇ Download</button>
      <button style="background:#eee;color:#333;" onclick="loadNotebook()">↻ Refresh</button>
    </div>
    <div id="cells-container"></div>
  </div>

  <!-- Chat tab -->
  <div id="page-chat" class="tab-page">
    <div id="chat-header" style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px 0;flex-shrink:0;">
      <span style="font-size:0.72rem;color:var(--muted);" id="chat-session-label">new session</span>
      <button onclick="resetChat()" style="font-size:0.72rem;background:none;border:1px solid var(--border);border-radius:8px;padding:3px 10px;color:var(--muted);cursor:pointer;">+ New Chat</button>
    </div>
    <div id="chat-messages"></div>
    <div id="chat-input-area">
      <textarea id="chat-input" rows="1" placeholder="Ask Claude…"
        oninput="autoResize(this)"
        onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendToClaude();}">
      </textarea>
      <button id="chat-send" onclick="sendToClaude()">➤</button>
    </div>
  </div>

  <!-- Data tab -->
  <div id="page-data" class="tab-page">
    <div class="data-card">
      <h3>🔑 Kaggle Credentials</h3>
      <input id="ds-username" placeholder="Kaggle username" autocomplete="username"/>
      <input id="ds-key" type="password" placeholder="API key" autocomplete="current-password"/>
      <button class="data-btn primary" onclick="saveCredentials()">Save Credentials</button>
      <div id="creds-status" style="font-size:0.75rem;color:var(--muted);"></div>
    </div>

    <div class="data-card">
      <h3>⬇ Download Dataset</h3>
      <input id="ds-slug" placeholder="owner/dataset-name  e.g. heptapod/titanic" style="font-family:monospace;"/>
      <button class="data-btn purple" onclick="downloadDataset()" id="ds-dl-btn">Download to Kaggle</button>
      <div id="ds-output"></div>
    </div>

    <div class="data-card">
      <h3>📁 Available on Kernel</h3>
      <div id="ds-list" style="font-size:0.82rem;color:var(--muted);">Loading…</div>
      <button class="data-btn" style="background:#eee;color:#555;" onclick="refreshDatasets()">↻ Refresh</button>
    </div>
  </div>

  <!-- KB tab -->
  <div id="page-kb" class="tab-page" style="padding:12px 12px 80px;gap:12px;">
    <div class="data-card">
      <h3>📚 Knowledge Base</h3>
      <p style="font-size:0.78rem;color:var(--muted);line-height:1.5;">Upload files (txt, md, csv, py, json…) — their content is injected into every Claude prompt automatically.</p>
      <input type="file" id="kb-file-input" multiple style="font-size:0.78rem;">
      <button class="data-btn primary" onclick="uploadKbFiles()">Upload</button>
      <div id="kb-upload-status" style="font-size:0.75rem;color:var(--muted);"></div>
    </div>
    <div class="data-card">
      <h3>📄 Uploaded Files</h3>
      <div id="kb-list" style="font-size:0.82rem;color:var(--muted);">Loading…</div>
      <button class="data-btn" style="background:#eee;color:#555;" onclick="refreshKb()">↻ Refresh</button>
    </div>
  </div>

</div>

<!-- FAB -->
<button id="fab" onclick="openAddSheet()">＋</button>

<!-- Add cell sheet -->
<div id="add-sheet">
  <textarea id="new-source" placeholder="Type code or markdown…"></textarea>
  <div class="sheet-row">
    <select id="new-type">
      <option value="code">Code</option>
      <option value="markdown">Markdown</option>
    </select>
    <button class="btn-cancel" onclick="closeAddSheet()">Cancel</button>
    <button class="btn-add" onclick="addCellAtEnd()">Add ↓</button>
  </div>
</div>

<!-- URL modal -->
<div class="modal-overlay" id="url-modal">
  <div class="modal-sheet">
    <div class="modal-handle"></div>
    <div class="modal-title">⚙ Kaggle Server URL</div>
    <button class="btn-primary" style="width:100%;margin-bottom:10px" onclick="startSession()">▶ Start Session Automatically</button>
    <div id="session-status" style="font-size:0.8rem;color:#aaa;margin-bottom:8px;display:none"></div>
    <label>Or paste URL manually</label>
    <textarea id="url-input" rows="4" style="font-family:monospace;font-size:0.72rem;"
      placeholder="https://kkb-production.jupyter-proxy.kaggle.net/k/..."></textarea>
    <div class="modal-row">
      <button class="btn-ghost" onclick="closeUrlModal()">Cancel</button>
      <button class="btn-primary" onclick="saveUrl()">Save &amp; Reconnect</button>
    </div>
  </div>
</div>

<!-- Tab bar -->
<div id="tabbar">
  <div class="tab active" id="tab-notebook" onclick="switchTab('notebook')">
    <span class="tab-icon">📓</span>Notebook
  </div>
  <div class="tab" id="tab-chat" onclick="switchTab('chat')">
    <span class="tab-icon">✦</span>Claude
  </div>
  <div class="tab" id="tab-data" onclick="switchTab('data')">
    <span class="tab-icon">📦</span>Data
  </div>
  <div class="tab" id="tab-kb" onclick="switchTab('kb')">
    <span class="tab-icon">📚</span>KB
  </div>
</div>

<script>
// ── State ────────────────────────────────────────────────────────────────────
let notebook = null;
let _polling = null;
let currentTab = 'notebook';

// ── Tab switching ─────────────────────────────────────────────────────────────
function switchTab(name) {
  currentTab = name;
  document.querySelectorAll('.tab-page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  document.getElementById('tab-' + name).classList.add('active');
  document.getElementById('fab').classList.toggle('hidden', name !== 'notebook');
  if (name === 'data') refreshDatasets();
  if (name === 'kb') refreshKb();
}

// ── Notebook ──────────────────────────────────────────────────────────────────
async function loadNotebook() {
  setStatus('loading…');
  try {
    const r = await fetch('/api/notebook');
    notebook = await r.json();
    if (notebook.error) throw new Error(notebook.error);
    renderCells();
    setStatus(`${notebook.cells.length} cells · ${new Date().toLocaleTimeString()}`);
  } catch(e) { setStatus('⚠ ' + e.message); }
}

function setStatus(msg) {
  document.getElementById('status-text').textContent = msg;
}

function renderCells() {
  const c = document.getElementById('cells-container');
  if (!notebook.cells.length) {
    c.innerHTML = '<div id="empty-cells">No cells yet.<br>Tap ＋ to add one.</div>';
    return;
  }
  c.innerHTML = '';
  notebook.cells.forEach((cell, idx) => c.appendChild(buildCell(cell, idx)));
}

function buildCell(cell, idx) {
  const div = document.createElement('div');
  div.className = 'cell' + (cell.cell_type === 'markdown' ? ' cell-markdown' : '');
  div.dataset.idx = idx;
  const ec = cell.execution_count ? `[${cell.execution_count}]` : '[ ]';
  const badge = cell.cell_type === 'markdown' ? 'MD' : 'PY';
  const badgeClass = cell.cell_type === 'markdown' ? 'cell-badge md' : 'cell-badge';
  div.innerHTML = `
    <div class="cell-header">
      <span class="${badgeClass}">${badge}</span>
      <span class="exec-count">${cell.cell_type === 'code' ? ec : ''}</span>
      <div class="cell-actions">
        ${cell.cell_type === 'code'
          ? `<button class="btn-run" onclick="runCell(${idx})">▶ Run</button>`
          : `<button class="btn-edit" onclick="toggleMdEdit(${idx})">✏ Edit</button>`}
        <button class="btn-del" onclick="deleteCell(${idx})">✕</button>
      </div>
    </div>
    <div class="cell-source" id="src-${idx}"
      ${cell.cell_type === 'code' ? 'contenteditable="true"' : ''}
      onblur="${cell.cell_type === 'code' ? `saveEdit(${idx})` : ''}"
    >${escHtml(''.concat(...[cell.source].flat()))}</div>
    ${cell.cell_type === 'markdown' ? `<div class="rendered" id="rendered-${idx}"></div>` : ''}
    ${cell.cell_type === 'code' ? buildOutputHtml(cell.outputs || []) : ''}
  `;
  if (cell.cell_type === 'markdown')
    renderMarkdown(idx, ''.concat(...[cell.source].flat()));
  return div;
}

function buildOutputHtml(outputs) {
  if (!outputs.length) return '';
  let html = '<div class="cell-output">';
  for (const o of outputs) {
    if (o.output_type === 'stream')
      html += `<span class="out-stream">${escHtml(o.text)}</span>`;
    else if (o.output_type === 'execute_result' || o.output_type === 'display_data') {
      if (o.data?.['image/png'])
        html += `<img src="data:image/png;base64,${o.data['image/png']}" style="max-width:100%;border-radius:6px;margin:4px 0;display:block;">`;
      else if (o.data?.['text/html'])
        html += `<div style="font-size:0.78rem;overflow-x:auto;">${o.data['text/html']}</div>`;
      else
        html += `<span class="out-result">${escHtml(o.data?.['text/plain'] || '')}</span>`;
    }
    else if (o.output_type === 'error') {
      const tb = (o.traceback||[]).map(stripAnsi).join('\n');
      html += `<span class="out-error">${escHtml(o.ename)}: ${escHtml(o.evalue)}\n${escHtml(tb)}</span>`;
    }
  }
  return html + '</div>';
}

function renderMarkdown(idx, src) {
  fetch('/api/md', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text:src})})
    .then(r=>r.json()).then(d=>{ const el=document.getElementById('rendered-'+idx); if(el) el.innerHTML=d.html; });
}

function updateLiveOutput(idx, text) {
  const cellEl = document.querySelector(`.cell[data-idx="${idx}"]`);
  if (!cellEl) return;
  let out = cellEl.querySelector('.live-output');
  if (!out) { out=document.createElement('div'); out.className='cell-output live-output'; cellEl.appendChild(out); }
  out.innerHTML = `<span class="out-stream">${escHtml(text)}</span>`;
}

// ── Cell actions ──────────────────────────────────────────────────────────────
async function runCell(idx) {
  const r = await fetch(`/api/cell/${idx}/run`, {method:'POST'});
  const data = await r.json();
  if (data.error) { setStatus('⚠ ' + data.error); return; }
  setKernelBusy(true);
  setStatus(`⏳ Cell ${idx} running…`);
  startPolling();
}

async function runAll() {
  const code = (notebook?.cells||[]).map((c,i)=>[c,i]).filter(([c])=>c.cell_type==='code');
  for (const [,idx] of code) { await runCell(idx); await waitForIdle(); }
}

function waitForIdle() {
  return new Promise(resolve => {
    const t = setInterval(async () => {
      const r = await fetch('/api/execution/status');
      const d = await r.json();
      if (!d.running) { clearInterval(t); resolve(); }
    }, 2000);
  });
}

function startPolling() {
  if (_polling) return;
  _polling = setInterval(pollExecution, 5000);
}

async function pollExecution() {
  try {
    const r = await fetch('/api/execution/status');
    const d = await r.json();
    if (d.running) {
      setStatus(`⏳ Cell ${d.cell_idx} running… (${d.output.length} chars)`);
      updateLiveOutput(d.cell_idx, d.output);
    }
    if (d.done) {
      clearInterval(_polling); _polling = null;
      setKernelBusy(false);
      const cellEl = document.querySelector(`.cell[data-idx="${d.cell_idx}"]`);
      if (cellEl) { cellEl.classList.add('done-flash'); setTimeout(()=>cellEl.classList.remove('done-flash'),1200); }
      setStatus(d.error ? `⚠ Cell ${d.cell_idx} errored` : `✓ Cell ${d.cell_idx} done`);
      await loadNotebook();
    }
    if (!d.running && !d.done) { clearInterval(_polling); _polling = null; setKernelBusy(false); }
  } catch(e) { setStatus('⚠ poll error'); }
}

function setKernelBusy(busy) {
  const dot = document.getElementById('kernel-dot');
  dot.className = busy ? 'busy' : 'idle';
}

async function saveEdit(idx) {
  const el = document.getElementById('src-' + idx);
  await fetch(`/api/cell/${idx}`, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({source:el.innerText})});
}

async function deleteCell(idx) {
  if (!confirm(`Delete cell ${idx}?`)) return;
  await fetch(`/api/cell/${idx}`, {method:'DELETE'});
  await loadNotebook();
}

function toggleMdEdit(idx) {
  const src = document.getElementById('src-' + idx);
  const rendered = document.getElementById('rendered-' + idx);
  if (src.style.display === 'block') {
    src.style.display = 'none';
    rendered.style.display = 'block';
    saveEdit(idx).then(()=>loadNotebook());
  } else {
    src.style.display = 'block';
    rendered.style.display = 'none';
    src.contentEditable = 'true';
    src.focus();
  }
}

// ── FAB / add sheet ───────────────────────────────────────────────────────────
function openAddSheet() {
  document.getElementById('add-sheet').classList.add('open');
  document.getElementById('new-source').focus();
}
function closeAddSheet() {
  document.getElementById('add-sheet').classList.remove('open');
  document.getElementById('new-source').value = '';
}
async function addCellAtEnd() {
  const src = document.getElementById('new-source').value;
  const type = document.getElementById('new-type').value;
  await fetch('/api/cell', {method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({source:src, type, index:-1})});
  closeAddSheet();
  await loadNotebook();
}

function downloadNotebook() { window.location.href = '/api/notebook/download'; }

// ── Claude chat ───────────────────────────────────────────────────────────────
function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function appendMsg(role, text) {
  const box = document.getElementById('chat-messages');
  const wrap = document.createElement('div');
  wrap.className = 'msg msg-' + role;
  wrap.innerHTML = `<div class="bubble"></div><div class="msg-meta"></div>`;
  wrap.querySelector('.bubble').textContent = text;
  box.appendChild(wrap);
  box.scrollTop = box.scrollHeight;
  return wrap;
}

function showTyping() {
  const box = document.getElementById('chat-messages');
  const wrap = document.createElement('div');
  wrap.className = 'msg msg-claude';
  wrap.id = 'typing-indicator';
  wrap.innerHTML = `<div class="bubble typing-bubble">
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
  </div>`;
  box.appendChild(wrap);
  box.scrollTop = box.scrollHeight;
}

function removeTyping() {
  const el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

async function resetChat() {
  await fetch('/api/claude/reset', {method:'POST'});
  document.getElementById('chat-messages').innerHTML = '';
  document.getElementById('chat-session-label').textContent = 'new session';
}

async function loadChatHistory() {
  const r = await fetch('/api/claude/history');
  const history = await r.json();
  const box = document.getElementById('chat-messages');
  box.innerHTML = '';
  if (!history.length) return;

  history.forEach(msg => {
    if (msg.role === 'user') {
      appendMsg('user', msg.text);
    } else {
      const wrap = appendMsg('claude', '');
      const bubble = wrap.querySelector('.bubble');
      (msg.blocks || []).forEach(block => {
        if (block.type === 'thinking') {
          const el = document.createElement('div');
          el.className = 'thinking-block';
          el.textContent = block.text;
          bubble.appendChild(el);
        } else if (block.type === 'text') {
          const el = document.createElement('span');
          el.style.whiteSpace = 'pre-wrap';
          el.textContent = block.text;
          bubble.appendChild(el);
        } else if (block.type === 'tool_call') {
          addToolBlock(bubble, block.name, block.command);
        } else if (block.type === 'tool_result') {
          fillToolResult(bubble, block.text);
        }
      });
    }
  });
  box.scrollTop = box.scrollHeight;
  document.getElementById('chat-session-label').textContent = 'session active';
}

function addToolBlock(bubble, name, command) {
  const div = document.createElement('div');
  div.className = 'tool-block';
  div.innerHTML = `<div class="tool-name">▶ ${escHtml(name)}</div><div class="tool-cmd">${escHtml(command)}</div><div class="tool-result-text pending">running…</div>`;
  bubble.appendChild(div);
  return div;
}

function fillToolResult(bubble, resultText) {
  const blocks = bubble.querySelectorAll('.tool-block');
  for (let i = blocks.length - 1; i >= 0; i--) {
    const r = blocks[i].querySelector('.tool-result-text');
    if (r && r.classList.contains('pending')) {
      r.classList.remove('pending');
      r.textContent = resultText || '(done)';
      return;
    }
  }
}

async function sendToClaude() {
  const input = document.getElementById('chat-input');
  const prompt = input.value.trim();
  if (!prompt) return;
  input.value = ''; input.style.height = 'auto';
  document.getElementById('chat-send').disabled = true;

  appendMsg('user', prompt);
  showTyping();
  switchTab('chat');

  let started = false;
  let replyWrap = null;
  let currentTextNode = null;
  let currentThinkingNode = null;
  let currentText = '';
  let currentThinking = '';

  function ensureReply() {
    if (!started) { removeTyping(); replyWrap = appendMsg('claude', ''); started = true; }
  }

  try {
    const resp = await fetch('/api/claude', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({prompt}),
    });
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      buf += decoder.decode(value, {stream:true});
      const lines = buf.split('\n'); buf = lines.pop();
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const data = JSON.parse(line.slice(6));
        if (data.done) break;
        const box = document.getElementById('chat-messages');
        if (data.thinking) {
          ensureReply();
          if (!currentThinkingNode) {
            currentThinkingNode = document.createElement('div');
            currentThinkingNode.className = 'thinking-block';
            replyWrap.querySelector('.bubble').prepend(currentThinkingNode);
          }
          currentThinking += data.thinking;
          currentThinkingNode.textContent = currentThinking;
          box.scrollTop = box.scrollHeight;
        }
        if (data.text) {
          ensureReply();
          if (!currentTextNode) {
            currentTextNode = document.createElement('span');
            currentTextNode.style.whiteSpace = 'pre-wrap';
            replyWrap.querySelector('.bubble').appendChild(currentTextNode);
          }
          currentText += data.text;
          currentTextNode.textContent = currentText;
          box.scrollTop = box.scrollHeight;
        }
        if (data.tool_call) {
          ensureReply();
          currentTextNode = null; currentText = '';
          currentThinkingNode = null; currentThinking = '';
          addToolBlock(replyWrap.querySelector('.bubble'), data.tool_call.name, data.tool_call.command);
          box.scrollTop = box.scrollHeight;
        }
        if (data.tool_result) {
          ensureReply();
          fillToolResult(replyWrap.querySelector('.bubble'), data.tool_result);
          box.scrollTop = box.scrollHeight;
        }
      }
    }
    if (!started) { removeTyping(); replyWrap = appendMsg('claude', '(no response)'); }
    const now = new Date().toLocaleTimeString();
    if (replyWrap) replyWrap.querySelector('.msg-meta').textContent = `✓ ${now}`;
    document.getElementById('chat-session-label').textContent = 'session active';
  } catch(e) {
    removeTyping();
    appendMsg('claude', 'Error: ' + e.message);
  }

  document.getElementById('chat-send').disabled = false;
  await loadNotebook();
}

// ── URL modal ─────────────────────────────────────────────────────────────────
async function openUrlModal() {
  const [ru, rs] = await Promise.all([fetch('/api/server-url'), fetch('/api/active-slug')]);
  const d = await ru.json(), s = await rs.json();
  document.getElementById('url-input').value = d.url;
  const status = document.getElementById('session-status');
  const btn = document.querySelector('#url-modal .btn-primary');
  btn.disabled = false;
  btn.textContent = '▶ Start Session Automatically';
  if (s.slug) {
    status.style.display = 'block';
    status.style.color = '#aaa';
    status.textContent = 'Notebook: ' + s.slug;
  } else {
    status.style.display = 'none';
  }
  document.getElementById('url-modal').classList.add('open');
}
function closeUrlModal() { document.getElementById('url-modal').classList.remove('open'); }
async function saveUrl() {
  const url = document.getElementById('url-input').value.trim();
  if (!url) return;
  await fetch('/api/server-url', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({url})});
  closeUrlModal();
  await loadNotebook();
}
async function startSession() {
  const btn = document.querySelector('#url-modal .btn-primary');
  const status = document.getElementById('session-status');
  btn.disabled = true;
  btn.textContent = '⏳ Starting session…';
  status.style.display = 'block';
  status.textContent = 'Launching headless browser, this takes ~30s…';
  try {
    const r = await fetch('/api/fetch-kaggle-url', {method:'POST'});
    const d = await r.json();
    if (d.url) {
      document.getElementById('url-input').value = d.url;
      status.style.color = '#4caf50';
      status.textContent = '✓ ' + (d.slug || 'Session') + ' started — tap Save & Reconnect';
      btn.textContent = '✓ Done';
    } else {
      status.style.color = '#f44336';
      status.textContent = '✗ ' + (d.error || 'Failed');
      btn.disabled = false;
      btn.textContent = '▶ Start Session Automatically';
    }
  } catch(e) {
    status.style.color = '#f44336';
    status.textContent = '✗ Server unreachable';
    btn.disabled = false;
    btn.textContent = '▶ Start Session Automatically';
  }
}

// ── Data tab ──────────────────────────────────────────────────────────────────
async function saveCredentials() {
  const u = document.getElementById('ds-username').value.trim();
  const k = document.getElementById('ds-key').value.trim();
  if (!u || !k) { alert('Both fields required.'); return; }
  const r = await fetch('/api/credentials', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username:u,key:k})});
  const d = await r.json();
  document.getElementById('creds-status').textContent = d.ok ? `✓ Saved for ${u}` : 'Error: '+d.error;
  document.getElementById('ds-key').value = '';
}

async function downloadDataset() {
  const slug = document.getElementById('ds-slug').value.trim();
  if (!slug) { alert('Enter a dataset slug'); return; }
  const btn = document.getElementById('ds-dl-btn');
  const out = document.getElementById('ds-output');
  btn.disabled = true; btn.textContent = '⏳ Downloading…';
  out.style.display = 'block'; out.textContent = 'Requesting download on Kaggle kernel…';
  try {
    const r = await fetch('/api/datasets/download', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({slug})});
    const d = await r.json();
    out.textContent = d.error || d.output || 'Done.';
    if (!d.error) refreshDatasets();
  } catch(e) { out.textContent = 'Error: '+e.message; }
  btn.disabled = false; btn.textContent = 'Download to Kaggle';
}

async function refreshDatasets() {
  const el = document.getElementById('ds-list');
  el.textContent = 'Loading…';
  try {
    const r = await fetch('/api/datasets');
    const d = await r.json();
    if (d.error) { el.textContent = 'Error: '+d.error; return; }
    const keys = Object.keys(d);
    if (!keys.length) { el.textContent = 'No datasets yet.'; return; }
    el.innerHTML = keys.map(name =>
      `<div class="ds-item"><strong>📁 ${name}</strong>` +
      d[name].map(f=>`<div class="ds-file">  📄 ${f}</div>`).join('') + '</div>'
    ).join('');
  } catch(e) { el.textContent = 'Could not reach kernel.'; }
}

// Load credentials status on data tab open
async function loadCredsStatus() {
  const r = await fetch('/api/credentials');
  const d = await r.json();
  if (d.username) {
    document.getElementById('ds-username').value = d.username;
    document.getElementById('creds-status').textContent = d.has_key ? `✓ Credentials saved for ${d.username}` : '';
  }
}

// ── Knowledge Base ────────────────────────────────────────────────────────────
async function uploadKbFiles() {
  const input = document.getElementById('kb-file-input');
  const status = document.getElementById('kb-upload-status');
  if (!input.files.length) { status.textContent = 'No files selected.'; return; }
  status.textContent = 'Uploading…';
  let ok = 0;
  for (const file of input.files) {
    const fd = new FormData();
    fd.append('file', file);
    const r = await fetch('/api/kb/upload', {method:'POST', body:fd});
    const d = await r.json();
    if (d.ok) ok++;
  }
  status.textContent = `✓ ${ok} file(s) uploaded`;
  input.value = '';
  refreshKb();
}

async function refreshKb() {
  const el = document.getElementById('kb-list');
  el.textContent = 'Loading…';
  const r = await fetch('/api/kb');
  const files = await r.json();
  if (!files.length) { el.textContent = 'No files yet.'; return; }
  el.innerHTML = files.map(f =>
    `<div class="ds-item" style="display:flex;align-items:center;justify-content:space-between;">
      <span>📄 ${escHtml(f.name)} <span style="color:var(--muted);font-size:0.7rem;">(${(f.size/1024).toFixed(1)} KB)</span></span>
      <button onclick="deleteKbFile('${escHtml(f.name)}')" style="border:none;background:#fdecea;color:var(--red);border-radius:6px;padding:3px 8px;font-size:0.75rem;cursor:pointer;">✕</button>
    </div>`
  ).join('');
}

async function deleteKbFile(name) {
  await fetch('/api/kb/' + encodeURIComponent(name), {method:'DELETE'});
  refreshKb();
}

// ── Utils ─────────────────────────────────────────────────────────────────────
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function stripAnsi(s) { return String(s).replace(/\x1b\[[0-9;]*m/g,''); }

// ── Init ──────────────────────────────────────────────────────────────────────
loadNotebook();
loadCredsStatus();
loadChatHistory();
setInterval(loadNotebook, 15000);
</script>
</body>
</html>
"""
# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _auto_start_session():
    """On startup: if no SERVER_URL, auto-activate the cc- notebook in background."""
    global SERVER_URL
    import time
    time.sleep(2)  # let Flask finish starting
    if SERVER_URL:
        _refresh_active_slug()
        return
    print("[startup] No SERVER_URL set — auto-starting Kaggle session...")
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

if __name__ == "__main__":
    print("Open http://localhost:5000 in your browser")
    threading.Thread(target=_auto_start_session, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
