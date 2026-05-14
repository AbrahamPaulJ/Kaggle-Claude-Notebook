#!/usr/bin/env python3
"""
Kaggle Jupyter remote client for Claude Code.

Creates and manages claude_notebook.ipynb directly on the Kaggle server.
Cells and outputs are saved as proper notebook JSON — open the file in
the Kaggle file browser to see everything live.
"""

import sys
import json
import uuid
import threading
import argparse
import requests
import websocket

NOTEBOOK = "claude_notebook.ipynb"

EMPTY_NOTEBOOK = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "cells": [],
}

# ---------------------------------------------------------------------------
# Notebook JSON helpers
# ---------------------------------------------------------------------------

def _new_cell(source: str, cell_type: str = "code") -> dict:
    cell = {
        "cell_type": cell_type,
        "id": str(uuid.uuid4())[:8],
        "metadata": {},
        "source": source,
    }
    if cell_type == "code":
        cell["execution_count"] = None
        cell["outputs"] = []
    return cell


def _outputs_from_messages(messages: list) -> list:
    """Convert collected kernel messages into notebook output objects."""
    outputs = []
    stream_buf = {}  # name → accumulated text

    def flush_stream():
        for name, text in stream_buf.items():
            outputs.append({"output_type": "stream", "name": name, "text": text})
        stream_buf.clear()

    for msg in messages:
        mtype = msg.get("msg_type")
        c = msg.get("content", {})
        if mtype == "stream":
            name = c.get("name", "stdout")
            stream_buf[name] = stream_buf.get(name, "") + c.get("text", "")
        elif mtype == "execute_result":
            flush_stream()
            outputs.append({
                "output_type": "execute_result",
                "execution_count": c.get("execution_count"),
                "data": c.get("data", {}),
                "metadata": c.get("metadata", {}),
            })
        elif mtype == "display_data":
            flush_stream()
            outputs.append({
                "output_type": "display_data",
                "data": c.get("data", {}),
                "metadata": c.get("metadata", {}),
            })
        elif mtype == "error":
            flush_stream()
            outputs.append({
                "output_type": "error",
                "ename": c.get("ename", ""),
                "evalue": c.get("evalue", ""),
                "traceback": c.get("traceback", []),
            })

    flush_stream()
    return outputs


def _render_outputs(outputs: list) -> str:
    parts = []
    for o in outputs:
        otype = o.get("output_type")
        if otype == "stream":
            parts.append(o.get("text", ""))
        elif otype in ("execute_result", "display_data"):
            parts.append(o.get("data", {}).get("text/plain", ""))
        elif otype == "error":
            parts.append(f"ERROR {o.get('ename')}: {o.get('evalue')}")
            for line in o.get("traceback", []):
                # strip ANSI codes for terminal display
                import re
                parts.append(re.sub(r"\x1b\[[0-9;]*m", "", line))
    return "\n".join(parts)

# ---------------------------------------------------------------------------
# KaggleClient
# ---------------------------------------------------------------------------

class KaggleClient:
    def __init__(self, server_url: str, token: str = ""):
        self.base_url = server_url.rstrip("/")
        self.headers = {"Authorization": f"Token {token}"} if token else {}
        self.kernel_id = None
        self._exec_count = 0

    # ── REST helpers ────────────────────────────────────────────────────────

    def _get(self, path):
        r = requests.get(f"{self.base_url}{path}", headers=self.headers)
        r.raise_for_status()
        return r.json()

    def _put(self, path, body):
        r = requests.put(f"{self.base_url}{path}", headers=self.headers, json=body)
        r.raise_for_status()
        return r.json()

    # ── Notebook read/write ─────────────────────────────────────────────────

    def _read_nb(self) -> dict:
        data = self._get(f"/api/contents/{NOTEBOOK}")
        return data["content"]

    def _write_nb(self, nb: dict):
        self._put(f"/api/contents/{NOTEBOOK}", {"type": "notebook", "content": nb})

    def init(self):
        """Create claude_notebook.ipynb on the Kaggle server (idempotent)."""
        try:
            self._read_nb()
            print(f"{NOTEBOOK} already exists.")
        except requests.HTTPError:
            self._write_nb(EMPTY_NOTEBOOK)
            print(f"Created {NOTEBOOK} on Kaggle server.")
        print(f"Open it in the Kaggle file browser (left panel) to see your notebook.")

    # ── Cell operations ─────────────────────────────────────────────────────

    def list_cells(self):
        nb = self._read_nb()
        cells = nb["cells"]
        if not cells:
            print("(no cells)")
            return
        for i, cell in enumerate(cells):
            src = "".join(cell["source"])[:72].replace("\n", " ")
            n_out = len(cell.get("outputs", []))
            tag = f"[{cell.get('execution_count') or ' '}]" if cell["cell_type"] == "code" else "[md]"
            print(f"  {i:>3}  {tag}  {src}{'…' if len(''.join(cell['source'])) > 72 else ''}"
                  + (f"  ({n_out} output{'s' if n_out != 1 else ''})" if n_out else ""))

    def get_cell(self, index: int):
        nb = self._read_nb()
        cell = nb["cells"][index]
        print("".join(cell["source"]))
        if cell.get("outputs"):
            print("\n--- outputs ---")
            print(_render_outputs(cell["outputs"]))

    def add_cell(self, source: str, cell_type: str = "code", index: int = -1):
        nb = self._read_nb()
        cell = _new_cell(source, cell_type)
        if index == -1:
            nb["cells"].append(cell)
            pos = len(nb["cells"]) - 1
        else:
            nb["cells"].insert(index, cell)
            pos = index
        self._write_nb(nb)
        print(f"Added {cell_type} cell at index {pos}.")
        return pos

    def edit_cell(self, index: int, source: str):
        nb = self._read_nb()
        nb["cells"][index]["source"] = source
        nb["cells"][index]["outputs"] = []
        nb["cells"][index]["execution_count"] = None
        self._write_nb(nb)
        print(f"Edited cell {index} (outputs cleared).")

    def delete_cell(self, index: int):
        nb = self._read_nb()
        nb["cells"].pop(index)
        self._write_nb(nb)
        print(f"Deleted cell {index}.")

    # ── Kernel ──────────────────────────────────────────────────────────────

    def _ensure_kernel(self):
        if self.kernel_id:
            return
        sessions = self._get("/api/sessions")
        if not sessions:
            raise RuntimeError("No active kernel on this Kaggle server.")
        self.kernel_id = sessions[0]["kernel"]["id"]

    def _run_on_kernel(self, code: str, timeout: int = 120) -> list:
        """Send code to kernel; return list of raw kernel messages."""
        self._ensure_kernel()
        ws_url = (self.base_url.replace("https://", "wss://")
                               .replace("http://", "ws://")
                  + f"/api/kernels/{self.kernel_id}/channels")

        msg_id = str(__import__("uuid").uuid4())
        execute_msg = {
            "header": {
                "msg_id": msg_id, "msg_type": "execute_request",
                "username": "claude", "session": str(__import__("uuid").uuid4()),
                "date": "", "version": "5.3",
            },
            "parent_header": {}, "metadata": {},
            "content": {
                "code": code, "silent": False, "store_history": True,
                "user_expressions": {}, "allow_stdin": False,
            },
            "channel": "shell",
        }

        messages = []
        done = threading.Event()

        def on_open(ws):
            ws.send(json.dumps(execute_msg))

        def on_message(ws, raw):
            d = json.loads(raw)
            if d.get("parent_header", {}).get("msg_id") != msg_id:
                return
            mtype = d.get("msg_type", "")
            messages.append(d)
            if mtype == "status" and d["content"].get("execution_state") == "idle":
                done.set()

        def on_error(ws, err):
            messages.append({"msg_type": "error",
                              "content": {"ename": "WebSocketError", "evalue": str(err), "traceback": []}})
            done.set()

        ws = websocket.WebSocketApp(ws_url, on_open=on_open,
                                    on_message=on_message, on_error=on_error)
        t = threading.Thread(target=ws.run_forever)
        t.daemon = True
        t.start()
        done.wait(timeout=timeout)
        ws.close()
        return messages

    def execute_cell(self, index: int, timeout: int = 120):
        nb = self._read_nb()
        cell = nb["cells"][index]
        if cell["cell_type"] != "code":
            print(f"Cell {index} is markdown — nothing to execute.")
            return

        code = "".join(cell["source"])
        print(f"Running cell {index}...")

        messages = self._run_on_kernel(code, timeout)
        outputs = _outputs_from_messages(messages)
        self._exec_count += 1

        # Save outputs back into the notebook
        nb = self._read_nb()
        nb["cells"][index]["outputs"] = outputs
        nb["cells"][index]["execution_count"] = self._exec_count
        self._write_nb(nb)

        result = _render_outputs(outputs)
        print(result if result else "(no output)")
        return result

    def run_all(self, timeout: int = 300):
        nb = self._read_nb()
        for i, cell in enumerate(nb["cells"]):
            if cell["cell_type"] == "code":
                self.execute_cell(i, timeout)

    def run(self, code: str, timeout: int = 120):
        """Execute ad-hoc code on the kernel (not saved to notebook)."""
        messages = self._run_on_kernel(code, timeout)
        outputs = _outputs_from_messages(messages)
        result = _render_outputs(outputs)
        print(result if result else "(no output)")
        return result

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _unescape(s: str) -> str:
    """Expand \\n, \\t etc. that arrive as literal two-char sequences from shell args."""
    return s.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')


def get_client(args) -> KaggleClient:
    import os
    url = args.url or os.environ.get("KAGGLE_SERVER_URL")
    token = args.token or os.environ.get("KAGGLE_TOKEN", "")
    if not url:
        print("Provide --url or set KAGGLE_SERVER_URL.")
        sys.exit(1)
    return KaggleClient(url, token)


def main():
    parser = argparse.ArgumentParser(
        description="Kaggle Jupyter remote client — manages claude_notebook.ipynb")
    parser.add_argument("--url",   help="Jupyter server URL (or KAGGLE_SERVER_URL env var)")
    parser.add_argument("--token", help="Auth token (optional — Kaggle embeds it in the URL)")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("init",       help="Create claude_notebook.ipynb on the Kaggle server")
    sub.add_parser("list",       help="List all cells")

    p = sub.add_parser("show",   help="Print a cell's source and output")
    p.add_argument("index", type=int)

    p = sub.add_parser("add",    help="Add a cell (default: append code cell)")
    p.add_argument("source",     help="Cell source code or markdown text")
    p.add_argument("--type",     default="code", choices=["code", "markdown"])
    p.add_argument("--index",    type=int, default=-1, help="Insert at position (-1 = append)")

    p = sub.add_parser("edit",   help="Replace a cell's source (clears outputs)")
    p.add_argument("index", type=int)
    p.add_argument("source")

    p = sub.add_parser("delete", help="Delete a cell")
    p.add_argument("index", type=int)

    p = sub.add_parser("run",    help="Execute a cell and save its output to the notebook")
    p.add_argument("index", type=int)
    p.add_argument("--timeout",  type=int, default=120)

    p = sub.add_parser("run-all", help="Execute all code cells in order")
    p.add_argument("--timeout",   type=int, default=300)

    p = sub.add_parser("exec",   help="Run ad-hoc code on the kernel (not saved to notebook)")
    p.add_argument("code")
    p.add_argument("--timeout",  type=int, default=120)

    args = parser.parse_args()
    client = get_client(args)

    if   args.cmd == "init":     client.init()
    elif args.cmd == "list":     client.list_cells()
    elif args.cmd == "show":     client.get_cell(args.index)
    elif args.cmd == "add":      client.add_cell(_unescape(args.source), args.type, args.index)
    elif args.cmd == "edit":     client.edit_cell(args.index, _unescape(args.source))
    elif args.cmd == "delete":   client.delete_cell(args.index)
    elif args.cmd == "run":      client.execute_cell(args.index, args.timeout)
    elif args.cmd == "run-all":  client.run_all(args.timeout)
    elif args.cmd == "exec":     client.run(_unescape(args.code), args.timeout)
    else:                        parser.print_help()


if __name__ == "__main__":
    main()
