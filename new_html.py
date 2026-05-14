NEW_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Kaggle Notebook</title>
<style>
:root {
  --bg: #f7f8fa;
  --cell-bg: #fff;
  --cell-head: #f3f4f6;
  --border: #d1d5db;
  --border-light: #e5e7eb;
  --header-bg: #1c2330;
  --accent: #0d9e6a;
  --green: #0d9e6a;
  --red: #dc2626;
  --orange: #f59e0b;
  --text: #1f2937;
  --muted: #6b7280;
  --purple: #6c3fd4;
  --claude-color: #c2651a;
  --gemini-color: #4285f4;
  --tab-h: 62px;
  --header-h: 52px;
  --mono: "SFMono-Regular","Consolas","Menlo","Liberation Mono",monospace;
}
* { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
html, body { height: 100%; overflow: hidden; background: var(--bg); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: var(--text); font-size: 13px; }

/* ── Header ── */
#header {
  position: fixed; top: 0; left: 0; right: 0; height: var(--header-h);
  background: var(--header-bg); color: #fff; display: flex; align-items: center;
  padding: 0 12px; gap: 8px; z-index: 50; box-shadow: 0 1px 4px #0006;
}
#header h1 { font-size: 0.9rem; font-weight: 600; flex: 0 0 auto; max-width: 42%; letter-spacing: 0.01em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
#gpu-pill { font-size: 0.6rem; font-weight: 700; padding: 2px 7px; border-radius: 10px; letter-spacing: 0.06em; flex-shrink: 0; transition: all 0.3s; }
#gpu-pill.active  { background: rgba(13,158,106,0.18); color: #0d9e6a; border: 1px solid #0d9e6a; }
#gpu-pill.busy    { background: rgba(245,158,11,0.18); color: var(--orange); border: 1px solid var(--orange); }
#gpu-pill.inactive{ background: rgba(255,255,255,0.07); color: #666; border: 1px solid #444; }
#status-text { font-size: 0.65rem; color: #9ca3af; flex: 1; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.icon-btn { background: none; border: none; color: #ccc; font-size: 1.6rem; padding: 5px; cursor: pointer; opacity: 0.8; flex-shrink: 0; }
.icon-btn:active { opacity: 1; }
@keyframes spin { to { transform: rotate(360deg); } }
#hdr-spinner { display: none; width: 13px; height: 13px; border: 2px solid #ffffff22; border-top-color: #fff; border-radius: 50%; animation: spin 0.8s linear infinite; flex-shrink: 0; }
#hdr-spinner.active { display: inline-block; }

/* ── Tab bar ── */
#tabbar { position: fixed; bottom: 0; left: 0; right: 0; height: var(--tab-h); background: var(--cell-bg); border-top: 1px solid var(--border); display: flex; z-index: 50; box-shadow: 0 -1px 6px #0002; }
.tab { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px; font-size: 0.67rem; font-weight: 500; color: var(--muted); cursor: pointer; transition: color 0.15s; padding: 5px 0; }
.tab .tab-icon { display: flex; align-items: center; justify-content: center; line-height: 1; }
.tab.active { color: var(--accent); }

/* ── Content area ── */
#content { position: fixed; top: var(--header-h); bottom: var(--tab-h); left: 0; right: 0; overflow: hidden; }
.tab-page { position: absolute; inset: 0; overflow-y: auto; -webkit-overflow-scrolling: touch; display: none; flex-direction: column; }
.tab-page.active { display: flex; }

/* ── Notebook tab ── */
#page-notebook { padding: 12px 10px 80px; gap: 0; }
#notebook-toolbar { display: flex; gap: 6px; padding: 0 0 10px; flex-wrap: wrap; }
#notebook-toolbar button { padding: 5px 12px; border: 1px solid var(--border); border-radius: 4px; font-size: 0.75rem; font-weight: 600; cursor: pointer; background: var(--cell-bg); color: var(--text); }
#notebook-toolbar button:first-child { background: var(--accent); color: #fff; border-color: var(--accent); }
#empty-cells { text-align: center; color: var(--muted); padding: 60px 20px; font-size: 0.9rem; }

/* ── Cell ── */
.cell { background: var(--cell-bg); border: 1px solid var(--border); border-radius: 4px; margin-bottom: 14px; overflow: visible; }
.cell.running { border-color: var(--border); }
.cell.done-flash { border-color: var(--green); box-shadow: 0 0 0 2px rgba(13,158,106,0.15); transition: all 0.6s; }

/* Cell header */
.cell-head { display: flex; align-items: center; justify-content: space-between; padding: 4px 8px 4px 6px; background: var(--cell-head); border-bottom: 1px solid var(--border-light); min-height: 32px; gap: 6px; cursor: pointer; user-select: none; }
.ch-left { display: flex; align-items: center; gap: 6px; }
.ch-right { display: flex; align-items: center; gap: 3px; }
.run-btn { background: var(--accent); color: #fff; border: none; border-radius: 3px; padding: 3px 9px; font-size: 0.72rem; font-weight: 700; cursor: pointer; flex-shrink: 0; letter-spacing: 0.02em; }
.run-btn:active { opacity: 0.85; }
.cell-run-spinner { display: none; width: 10px; height: 10px; border: 1.5px solid rgba(13,158,106,0.2); border-top-color: var(--green); border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0; }
.cell.running .cell-run-spinner { display: inline-block; }
.cell.running .run-btn { background: var(--green); pointer-events: none; }
.cell-ec { font-family: var(--mono); font-size: 0.68rem; color: var(--muted); min-width: 34px; }
.md-tag { font-size: 0.62rem; font-weight: 700; padding: 1px 6px; border-radius: 3px; background: #d1fae5; color: #065f46; letter-spacing: 0.04em; }
.cell-btn { background: none; border: 1px solid var(--border-light); border-radius: 3px; color: var(--muted); font-size: 0.7rem; padding: 2px 6px; cursor: pointer; transition: all 0.12s; }
.cell-btn:hover { background: var(--border-light); color: var(--text); }
.cell-btn.del { color: var(--red); border-color: transparent; }
.cell-btn.del:hover { background: #fee2e2; }
.toggle-src { font-size: 0.75rem; transition: transform 0.15s; }

/* Cell source */
.cell-src-wrap { position: relative; border-left: 3px solid transparent; transition: border-color 0.15s; }
.cell-src-wrap:focus-within { border-left-color: var(--accent); }
.cell-src-wrap.collapsed { display: none; }
.cell-source { font-family: var(--mono); font-size: 8px; line-height: 1.55; padding: 8px 12px; outline: none; white-space: pre-wrap; word-break: break-all; min-height: 28px; color: var(--text); background: var(--cell-bg); display: block; }
.cell-source[contenteditable=true]:focus { background: #fafbff; }
.md-src { display: none !important; font-family: var(--mono); }
.md-src.editing { display: block !important; background: #fffde7; }
.md-rendered { padding: 10px 14px; font-size: 0.88rem; line-height: 1.65; }
.md-rendered h1,.md-rendered h2,.md-rendered h3 { margin: 6px 0 4px; font-size: 1rem; }
.md-rendered p { margin-bottom: 6px; }
.md-rendered code { background: #f1f5f9; padding: 1px 5px; border-radius: 3px; font-family: var(--mono); font-size: 0.82rem; }
.md-rendered pre { background: #f1f5f9; padding: 8px 10px; border-radius: 4px; overflow-x: auto; margin: 6px 0; }

/* Output section */
.cell-out-section { border-top: 1px solid var(--border-light); }
.out-head { display: flex; align-items: center; gap: 6px; padding: 4px 8px 4px 6px; min-height: 32px; cursor: pointer; user-select: none; background: #fafbfc; border-bottom: 1px solid var(--border-light); }
.out-head:active { background: var(--border-light); }
.out-chevron { font-size: 0.65rem; color: var(--muted); transition: transform 0.15s; display: inline-block; }
.out-chevron.collapsed { transform: rotate(-90deg); }
.out-label { font-family: var(--mono); font-size: 0.68rem; color: var(--muted); }
.cell-out-body { padding: 6px 12px; font-family: var(--mono); font-size: 8px; line-height: 1.55; background: #f0f3f7; }
.cell-out-body.collapsed { display: none; }
.out-stream { color: #1f2937; white-space: pre-wrap; word-break: break-word; display: block; }
.out-result { color: #065f46; white-space: pre-wrap; word-break: break-word; display: block; }
.out-error { color: var(--red); background: #fff5f5; padding: 6px 8px; border-radius: 3px; white-space: pre-wrap; word-break: break-word; display: block; border-left: 3px solid var(--red); }

/* Cell body collapse */
.cell-body.collapsed { display: none; }

/* Copy button */
.copy-btn { background: none; border: none; color: var(--muted); cursor: pointer; padding: 2px 4px; border-radius: 3px; opacity: 0.55; transition: opacity 0.12s; display: inline-flex; align-items: center; flex-shrink: 0; }
.copy-btn:hover { opacity: 1; }
.copy-btn.copied { color: var(--green); opacity: 1; }

/* Python comment syntax highlight */
.py-comment { color: #16a34a; font-style: italic; }

/* ── FAB ── */
#fab { position: fixed; right: 16px; bottom: calc(var(--tab-h) + 12px); width: 46px; height: 46px; background: var(--accent); color: #fff; border: none; border-radius: 50%; font-size: 1.4rem; display: flex; align-items: center; justify-content: center; cursor: pointer; z-index: 40; box-shadow: 0 3px 12px rgba(13,158,106,0.4); transition: transform 0.15s; }
#fab:active { transform: scale(0.92); }
#fab.hidden { display: none; }

/* ── Add cell sheet ── */
#add-sheet { position: fixed; left: 0; right: 0; bottom: var(--tab-h); background: var(--cell-bg); border-top: 1px solid var(--border); padding: 12px; z-index: 45; display: none; flex-direction: column; gap: 8px; box-shadow: 0 -4px 20px #0002; border-radius: 12px 12px 0 0; }
#add-sheet.open { display: flex; }
#add-sheet textarea { font-family: var(--mono); font-size: 12px; padding: 8px; border: 1px solid var(--border); border-radius: 4px; resize: none; height: 90px; outline: none; }
#add-sheet textarea:focus { border-color: var(--accent); }
.sheet-row { display: flex; gap: 6px; }
.sheet-row select { flex: 1; padding: 7px; border: 1px solid var(--border); border-radius: 4px; font-size: 0.8rem; background: #fff; }
.sheet-row button { padding: 7px 14px; border: none; border-radius: 4px; font-size: 0.8rem; font-weight: 600; cursor: pointer; }
.btn-cancel { background: #f3f4f6; color: #555; }
.btn-add { background: var(--accent); color: #fff; }

/* ── Chat tab ── */
#page-chat { flex-direction: column; }
#chat-messages { flex: 1; overflow-y: auto; -webkit-overflow-scrolling: touch; padding: 10px 10px 6px; display: flex; flex-direction: column; gap: 8px; }
.msg { max-width: 90%; word-break: break-word; line-height: 1.5; }
.msg-user { align-self: flex-end; }
.msg-user .bubble { background: var(--purple); color: #fff; border-radius: 16px 16px 4px 16px; padding: 8px 12px; font-size: 0.83rem; }
.msg-claude { align-self: flex-start; }
.msg-claude .bubble { background: var(--cell-bg); border: 1px solid var(--border); border-radius: 16px 16px 16px 4px; padding: 9px 12px; font-size: 0.83rem; white-space: pre-wrap; box-shadow: 0 1px 3px #0001; }
.msg-gemini { align-self: flex-start; }
.msg-gemini .bubble { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 16px 16px 16px 4px; padding: 9px 12px; font-size: 0.83rem; white-space: pre-wrap; box-shadow: 0 1px 3px #0001; }
.model-badge { font-size: 0.6rem; font-weight: 700; margin-bottom: 5px; display: block; letter-spacing: 0.03em; }
.model-badge.claude { color: var(--claude-color); }
.model-badge.gemini { color: var(--gemini-color); }
.model-btn { font-size: 0.68rem; padding: 3px 10px; border-radius: 12px; border: none; background: none; cursor: pointer; color: var(--muted); font-weight: 600; transition: all 0.15s; }
.model-btn.active { color: #fff; }
#btn-claude.active { background: var(--claude-color); }
#btn-gemini.active { background: var(--gemini-color); }
.thinking-block { font-style: italic; color: #888; font-size: 0.77rem; margin-bottom: 7px; padding-bottom: 7px; border-bottom: 1px dashed #e5e7eb; display: block; white-space: pre-wrap; --synonym: "Thinking..."; }
.thinking-block::before { content: "◑ " var(--synonym) " "; font-weight: 700; font-style: normal; color: var(--claude-color); }
.msg-meta { font-size: 0.6rem; color: var(--muted); margin-top: 2px; padding: 0 3px; }
.msg-user .msg-meta { text-align: right; }
.usage-footer { font-size: 0.6rem; color: var(--muted); margin-top: 6px; padding-top: 5px; border-top: 1px solid var(--border-light); font-family: var(--mono); display: flex; gap: 8px; flex-wrap: wrap; }
.usage-footer span { opacity: 0.75; }

/* Tool chips — compact, no command/result text */
.tool-chip { display: inline-flex; align-items: center; gap: 4px; font-size: 0.68rem; padding: 2px 8px; border-radius: 10px; margin: 2px 2px; font-family: var(--mono); font-weight: 600; vertical-align: middle; }
.tool-chip.pending { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
.tool-chip.done    { background: #d1fae5; color: #065f46; border: 1px solid #6ee7b7; }

/* Typing dots */
.typing-bubble { display: flex; gap: 5px; align-items: center; padding: 10px 14px; }
.typing-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--muted); animation: bounce 1.2s infinite ease-in-out; }
.typing-dot:nth-child(1) { animation-delay: 0s; }
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%,80%,100%{transform:translateY(0)} 40%{transform:translateY(-6px)} }

#chat-input-area { padding: 7px 10px; background: var(--cell-bg); border-top: 1px solid var(--border); display: flex; gap: 6px; align-items: flex-end; flex-shrink: 0; }
#chat-input { flex: 1; padding: 8px 12px; border: 1px solid var(--border); border-radius: 18px; font-size: 0.82rem; resize: none; max-height: 110px; outline: none; line-height: 1.4; font-family: inherit; background: var(--bg); }
#chat-input:focus { border-color: var(--accent); }
#chat-send { width: 38px; height: 38px; border-radius: 50%; background: var(--purple); border: none; color: #fff; font-size: 1rem; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: transform 0.12s; }
#chat-send:active { transform: scale(0.9); }
#chat-send:disabled { background: #d1d5db; }

/* ── Data / KB tabs ── */
#page-data, #page-kb { padding: 12px 10px 80px; gap: 10px; }
.data-card { background: var(--cell-bg); border-radius: 6px; padding: 12px; box-shadow: none; border: 1px solid var(--border); display: flex; flex-direction: column; gap: 9px; }
.data-card h3 { font-size: 0.82rem; font-weight: 700; color: var(--text); }
.data-card input { padding: 7px 10px; border: 1px solid var(--border); border-radius: 4px; font-size: 0.8rem; width: 100%; outline: none; background: var(--bg); }
.data-card input:focus { border-color: var(--accent); }
.data-card input[type=password] { font-family: var(--mono); }
.data-btn { padding: 8px; border: none; border-radius: 4px; font-size: 0.8rem; font-weight: 600; cursor: pointer; width: 100%; }
.data-btn.primary { background: var(--header-bg); color: #fff; }
.data-btn.purple { background: var(--purple); color: #fff; }
#ds-output { font-family: var(--mono); font-size: 0.7rem; white-space: pre-wrap; background: #f8f9fa; padding: 8px; border-radius: 4px; max-height: 140px; overflow-y: auto; display: none; border: 1px solid var(--border-light); }
.ds-item { padding: 7px 0; border-bottom: 1px solid var(--border-light); font-size: 0.78rem; }
.ds-item:last-child { border-bottom: none; }
.ds-item strong { display: block; margin-bottom: 2px; }
.ds-file { color: var(--muted); font-size: 0.72rem; }

/* ── Modals ── */
.modal-overlay { position: fixed; inset: 0; background: #0006; z-index: 100; display: none; align-items: flex-end; justify-content: center; }
.modal-overlay.open { display: flex; }
.modal-sheet { background: var(--cell-bg); border-radius: 16px 16px 0 0; width: 100%; max-height: 90vh; overflow-y: auto; padding: 18px; display: flex; flex-direction: column; gap: 10px; }
.modal-handle { width: 32px; height: 4px; background: var(--border); border-radius: 2px; margin: 0 auto 4px; }
.modal-title { font-weight: 700; font-size: 0.9rem; }
.modal-sheet input, .modal-sheet textarea { padding: 8px 10px; border: 1px solid var(--border); border-radius: 4px; font-size: 0.8rem; width: 100%; outline: none; background: var(--bg); }
.modal-sheet input:focus, .modal-sheet textarea:focus { border-color: var(--accent); }
.modal-sheet label { font-size: 0.75rem; color: var(--muted); margin-bottom: -4px; }
.modal-row { display: flex; gap: 8px; }
.modal-row button { flex: 1; padding: 9px; border: none; border-radius: 4px; font-size: 0.8rem; font-weight: 600; cursor: pointer; }
.btn-primary { background: var(--header-bg); color: #fff; }
.btn-ghost { background: #f3f4f6; color: #555; }
</style>
</head>
<body>

<!-- Header -->
<div id="header">
  <div id="gpu-pill" class="inactive">2× T4</div>
  <h1 id="notebook-title">Kaggle Notebook</h1>
  <div id="hdr-spinner"></div>
  <span id="status-text">loading…</span>
  <button class="icon-btn" onclick="openUrlModal()" title="Settings">⚙</button>
</div>

<!-- Content -->
<div id="content">

  <!-- Notebook tab -->
  <div id="page-notebook" class="tab-page active">
    <div id="notebook-toolbar">
      <button onclick="runAll()">▶ Run All</button>
      <button onclick="downloadNotebook()">⬇ Download</button>
      <button onclick="loadNotebook()">↻ Refresh</button>
    </div>
    <div id="cells-container"></div>
  </div>

  <!-- Chat tab -->
  <div id="page-chat" class="tab-page">
    <div id="chat-header" style="display:flex;align-items:center;gap:7px;padding:7px 10px 0;flex-shrink:0;">
      <div style="display:flex;gap:2px;background:#f1f2f4;border-radius:14px;padding:2px;flex-shrink:0;">
        <button id="btn-claude" class="model-btn" onclick="setModel('claude')">◉ Claude</button>
        <button id="btn-gemini" class="model-btn active" onclick="setModel('gemini')">✦ Gemini</button>
      </div>
      <span style="flex:1;font-size:0.65rem;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" id="chat-session-label">new session</span>
      <button onclick="openNewChatModal()" style="font-size:0.68rem;background:none;border:1px solid var(--border);border-radius:6px;padding:3px 9px;color:var(--muted);cursor:pointer;flex-shrink:0;">+ New Chat</button>
    </div>
    <div id="chat-messages"></div>
    <div id="chat-input-area">
      <textarea id="chat-input" rows="1" placeholder="Ask Gemini…"
        oninput="autoResize(this)"
        onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendChat();}">
      </textarea>
      <button id="chat-send" onclick="sendChat()">➤</button>
    </div>
  </div>

  <!-- Data tab -->
  <div id="page-data" class="tab-page">
    <div class="data-card">
      <h3>Credentials</h3>
      <input id="ds-username" placeholder="Kaggle username" autocomplete="username"/>
      <input id="ds-key" type="password" placeholder="API key" autocomplete="current-password"/>
      <button class="data-btn primary" onclick="saveCredentials()">Save Credentials</button>
      <div id="creds-status" style="font-size:0.72rem;color:var(--muted);"></div>
    </div>
    <div class="data-card">
      <h3>Download Dataset</h3>
      <input id="ds-slug" placeholder="owner/dataset-name  e.g. heptapod/titanic" style="font-family:var(--mono);"/>
      <button class="data-btn purple" onclick="downloadDataset()" id="ds-dl-btn">Download to Kaggle</button>
      <div id="ds-output"></div>
    </div>
    <div class="data-card">
      <h3>On Kernel</h3>
      <div id="ds-list" style="font-size:0.8rem;color:var(--muted);">Loading…</div>
      <button class="data-btn" style="background:#f3f4f6;color:#555;" onclick="refreshDatasets()">↻ Refresh</button>
    </div>
  </div>

  <!-- KB tab -->
  <div id="page-kb" class="tab-page">
    <div class="data-card">
      <h3>Knowledge Base</h3>
      <p style="font-size:0.75rem;color:var(--muted);line-height:1.5;">Upload files — contents are injected into every Claude/Gemini prompt.</p>
      <input type="file" id="kb-file-input" multiple style="font-size:0.75rem;">
      <button class="data-btn primary" onclick="uploadKbFiles()">Upload</button>
      <div id="kb-upload-status" style="font-size:0.72rem;color:var(--muted);"></div>
    </div>
    <div class="data-card">
      <h3>Uploaded Files</h3>
      <div id="kb-list" style="font-size:0.8rem;color:var(--muted);">Loading…</div>
      <button class="data-btn" style="background:#f3f4f6;color:#555;" onclick="refreshKb()">↻ Refresh</button>
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
    <button class="btn-primary" style="width:100%;padding:9px;border:none;border-radius:4px;font-size:0.8rem;font-weight:600;cursor:pointer;margin-bottom:4px;" onclick="startSession()">▶ Start Session Automatically</button>
    <div id="session-status" style="font-size:0.77rem;color:#aaa;display:none"></div>
    <label>Or paste URL manually</label>
    <textarea id="url-input" rows="7" style="font-family:var(--mono);font-size:0.7rem;"
      placeholder="https://kkb-production.jupyter-proxy.kaggle.net/k/..."></textarea>
    <div class="modal-row">
      <button class="btn-ghost" onclick="closeUrlModal()">Cancel</button>
      <button class="btn-primary" onclick="saveUrl()">Save &amp; Reconnect</button>
    </div>
    <button id="kill-kernel-btn" onclick="killKernel()" style="width:100%;padding:9px;border:1px solid var(--red);border-radius:4px;font-size:0.8rem;font-weight:600;cursor:pointer;background:none;color:var(--red);margin-top:2px;">■ Stop Jupyter Kernel</button>
    <div id="kill-status" style="font-size:0.77rem;color:var(--muted);display:none;text-align:center;"></div>
  </div>
</div>

<!-- New Chat modal -->
<div class="modal-overlay" id="new-chat-modal">
  <div class="modal-sheet">
    <div class="modal-handle"></div>
    <div class="modal-title">New Chat</div>
    <div style="font-size:0.75rem;color:var(--muted);">Cells always included. Deselect KB files to reduce tokens.</div>
    <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--border-light);cursor:pointer;" onclick="document.getElementById('kb-select-all').click()">
      <input type="checkbox" id="kb-select-all" onchange="toggleAllKb(this.checked)" onclick="event.stopPropagation()" style="flex-shrink:0;width:16px;height:16px;cursor:pointer;">
      <span style="font-size:0.8rem;font-weight:600;color:var(--text);">All KB files</span>
    </div>
    <div id="kb-checkbox-list" style="display:flex;flex-direction:column;gap:8px;max-height:38vh;overflow-y:auto;padding:4px 0;"></div>
    <div class="modal-row" style="margin-top:4px;">
      <button class="btn-ghost" onclick="closeNewChatModal()">Cancel</button>
      <button class="btn-primary" onclick="confirmNewChat()">Start New Chat</button>
    </div>
  </div>
</div>

<!-- KB Viewer Modal -->
<div class="modal-overlay" id="kb-view-modal">
  <div class="modal-sheet" style="max-height:90vh;">
    <div class="modal-handle"></div>
    <div class="modal-title" id="kb-view-title">File View</div>
    <pre id="kb-view-content" style="background:#f8f9fa;padding:10px;border-radius:4px;font-size:0.72rem;white-space:pre-wrap;overflow-y:auto;flex:1;border:1px solid var(--border);font-family:var(--mono);"></pre>
    <div class="modal-row">
      <button class="btn-ghost" onclick="closeKbView()">Close</button>
    </div>
  </div>
</div>

<!-- Tab bar -->
<div id="tabbar">
  <div class="tab active" id="tab-notebook" onclick="switchTab('notebook')">
    <span class="tab-icon"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="7" y1="3" x2="7" y2="21"/><line x1="11" y1="9" x2="17" y2="9"/><line x1="11" y1="13" x2="17" y2="13"/><line x1="11" y1="17" x2="17" y2="17"/></svg></span>
    Notebook
  </div>
  <div class="tab" id="tab-chat" onclick="switchTab('chat')">
    <span class="tab-icon"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></span>
    Chat
  </div>
  <div class="tab" id="tab-kb" onclick="switchTab('kb')">
    <span class="tab-icon"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg></span>
    KB
  </div>
  <div class="tab" id="tab-data" onclick="switchTab('data')">
    <span class="tab-icon"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg></span>
    Data
  </div>
</div>

<script>
// ── State ────────────────────────────────────────────────────────────────────
let notebook = null;
let _polling = null;
let currentTab = 'notebook';

const THINKING_SYNONYMS = ['musing','pondering','iterating','synthesizing','analyzing','designing','optimizing','reasoning'];

class SynonymSpinner {
  constructor(element) { this.element = element; this.index = 0; this.interval = null; }
  start() {
    if (this.interval) return;
    this.interval = setInterval(() => {
      this.index = (this.index + 1) % THINKING_SYNONYMS.length;
      const w = THINKING_SYNONYMS[this.index];
      this.element.style.setProperty('--synonym', `"${w.charAt(0).toUpperCase()+w.slice(1)}..."`);
    }, 1500);
  }
  stop() { clearInterval(this.interval); this.interval = null; this.element.style.setProperty('--synonym','"Thinking..."'); }
}

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
  try {
    const r = await fetch('/api/notebook');
    notebook = await r.json();
    if (notebook.auto_starting) {
      document.getElementById('hdr-spinner').classList.add('active');
      setStatus('Starting session…');
      updateGpu('inactive');
      return;
    }
    document.getElementById('hdr-spinner').classList.remove('active');
    if (notebook.error) throw new Error(notebook.error);
    renderCells();
    updateGpu('active');
    setStatus(`${notebook.cells.length} cells · ${new Date().toLocaleTimeString()}`);
    loadSlug();
  } catch(e) {
    document.getElementById('hdr-spinner').classList.remove('active');
    updateGpu('inactive');
    setStatus('⚠ ' + e.message);
  }
}

function setStatus(msg) {
  document.getElementById('status-text').textContent = msg;
}

function updateGpu(state) {
  const pill = document.getElementById('gpu-pill');
  if (!pill) return;
  pill.className = state;
  pill.textContent = state === 'busy' ? '2× T4 ⚡' : state === 'active' ? '2× T4 ●' : '2× T4';
}

function renderCells() {
  const c = document.getElementById('cells-container');
  if (!notebook.cells.length) {
    c.innerHTML = '<div id="empty-cells">No cells yet.<br>Tap ＋ to add one.</div>';
    return;
  }
  c.innerHTML = '';
  notebook.cells.forEach((cell, idx) => c.appendChild(buildCell(cell, idx)));
  notebook.cells.forEach((cell, idx) => {
    if (cell.cell_type === 'code') { const el = document.getElementById('src-'+idx); if (el) applyCommentHighlight(el); }
  });
  cellCollapseState.forEach(idx => {
    const body = document.getElementById(`cellbody-${idx}`);
    const chev = document.getElementById(`cellchev-${idx}`);
    if (body) { body.classList.add('collapsed'); if (chev) { chev.textContent = '▸'; chev.classList.add('collapsed'); } }
  });
  outCollapseState.forEach(idx => {
    const body = document.getElementById(`outbody-${idx}`);
    const chev = document.getElementById(`outchev-${idx}`);
    if (body) { body.classList.add('collapsed'); if (chev) { chev.textContent = '▸'; chev.classList.add('collapsed'); } }
  });
}

function buildCell(cell, idx) {
  const div = document.createElement('div');
  const isMd = cell.cell_type === 'markdown';
  div.className = 'cell' + (isMd ? ' cell-md' : ' cell-code');
  div.dataset.idx = idx;
  const ec = cell.execution_count ? `[${cell.execution_count}]` : '[ ]';
  const src = escHtml(''.concat(...[cell.source].flat()));

  const SP = `event.stopPropagation()`;
  const leftHead = isMd
    ? `<span class="md-tag">MD</span>`
    : `<button class="run-btn" onclick="${SP};runCell(${idx})">▶ Run</button>
       <span class="cell-ec" id="ec-${idx}">${ec}</span>
       <div class="cell-run-spinner" id="cellspinner-${idx}"></div>`;

  const rightHead = isMd
    ? `<button class="cell-btn" onclick="${SP};toggleMdEdit(${idx})" title="Edit">✏</button>
       <button class="copy-btn" id="copybtn-src-${idx}" onclick="${SP};copyCell(${idx})" title="Copy">${COPY_SVG}</button>
       <span class="out-chevron" id="cellchev-${idx}">▾</span>
       <button class="cell-btn del" onclick="${SP};deleteCell(${idx})">✕</button>`
    : `<button class="copy-btn" id="copybtn-src-${idx}" onclick="${SP};copyCell(${idx})" title="Copy">${COPY_SVG}</button>
       <span class="out-chevron" id="cellchev-${idx}">▾</span>
       <button class="cell-btn del" onclick="${SP};deleteCell(${idx})">✕</button>`;

  const srcLabel = isMd ? 'Markdown' : `In ${ec}`;

  const srcContent = isMd
    ? `<div class="cell-source md-src" id="src-${idx}" spellcheck="false">${src}</div>
       <div class="md-rendered" id="rendered-${idx}"></div>`
    : `<div class="cell-source" id="src-${idx}" contenteditable="true" spellcheck="false"
         onfocus="const t=this.innerText;this.textContent=t;"
         onblur="saveEdit(${idx})">${src}</div>`;

  div.innerHTML = `
    <div class="cell-head" onclick="toggleCell(${idx})">
      <div class="ch-left">${leftHead}</div>
      <div class="ch-right">${rightHead}</div>
    </div>
    <div class="cell-body" id="cellbody-${idx}">
      <div class="cell-src-wrap" id="srcwrap-${idx}">${srcContent}</div>
      ${!isMd ? buildOutputSection(cell.outputs || [], idx) : ''}
    </div>
  `;

  if (isMd) renderMarkdown(idx, ''.concat(...[cell.source].flat()));
  return div;
}

function buildOutputSection(outputs, idx) {
  if (!outputs.length) return '';
  let bodyHtml = '';
  for (const o of outputs) {
    if (o.output_type === 'stream')
      bodyHtml += `<div class="out-stream">${escHtml(o.text)}</div>`;
    else if (o.output_type === 'execute_result' || o.output_type === 'display_data') {
      const png = o.data?.['image/png'];
      if (png)
        bodyHtml += `<img src="data:image/png;base64,${png}" style="max-width:100%;height:auto;display:block;margin:4px 0;" alt="plot">`;
      else
        bodyHtml += `<div class="out-result">${escHtml(o.data?.['text/plain'] || '')}</div>`;
    }
    else if (o.output_type === 'error') {
      const tb = (o.traceback||[]).map(stripAnsi).join('\n');
      bodyHtml += `<div class="out-error">${escHtml(o.ename+': '+o.evalue)}\n${escHtml(tb)}</div>`;
    }
  }
  return `
    <div class="cell-out-section" id="outsec-${idx}">
      <div class="out-head" onclick="toggleCellOut(${idx})">
        <span class="out-chevron" id="outchev-${idx}">▾</span>
        <span class="out-label" style="flex:1;">Out ${outputs[0]?.execution_count ? '['+outputs[0].execution_count+']' : ''}</span>
        <button class="copy-btn" id="copybtn-out-${idx}" onclick="event.stopPropagation();copyCellOut(${idx})" title="Copy">${COPY_SVG}</button>
      </div>
      <div class="cell-out-body" id="outbody-${idx}">${bodyHtml}</div>
    </div>`;
}

function renderMarkdown(idx, src) {
  fetch('/api/md', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text:src})})
    .then(r=>r.json()).then(d=>{ const el=document.getElementById('rendered-'+idx); if(el) el.innerHTML=d.html; });
}

function updateLiveOutput(idx, text) {
  const cellBody = document.getElementById(`cellbody-${idx}`);
  if (!cellBody) return;
  let outsec = document.getElementById(`outsec-${idx}`);
  if (!outsec) {
    outsec = document.createElement('div');
    outsec.id = `outsec-${idx}`;
    outsec.className = 'cell-out-section';
    outsec.innerHTML = `
      <div class="out-head" onclick="toggleCellOut(${idx})">
        <span class="out-chevron" id="outchev-${idx}">▾</span>
        <span class="out-label">Output</span>
      </div>
      <div class="cell-out-body" id="outbody-${idx}"></div>`;
    cellBody.appendChild(outsec);
  }
  const body = document.getElementById(`outbody-${idx}`);
  if (body) { body.classList.remove('collapsed'); body.innerHTML = `<div class="out-stream">${escHtml(text)}</div>`; }
}

const cellCollapseState = new Set();
const outCollapseState = new Set();

function toggleCell(idx) {
  const body = document.getElementById(`cellbody-${idx}`);
  if (!body) return;
  const chev = document.getElementById(`cellchev-${idx}`);
  const collapsed = body.classList.toggle('collapsed');
  if (chev) { chev.textContent = collapsed ? '▸' : '▾'; chev.classList.toggle('collapsed', collapsed); }
  if (collapsed) cellCollapseState.add(idx); else cellCollapseState.delete(idx);
}

function toggleCellOut(idx) {
  const body = document.getElementById(`outbody-${idx}`);
  const chev = document.getElementById(`outchev-${idx}`);
  if (!body) return;
  const collapsed = body.classList.toggle('collapsed');
  if (chev) { chev.textContent = collapsed ? '▸' : '▾'; chev.classList.toggle('collapsed', collapsed); }
  if (collapsed) outCollapseState.add(idx); else outCollapseState.delete(idx);
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
  updateGpu(busy ? 'busy' : 'active');
}

async function saveEdit(idx) {
  const el = document.getElementById('src-' + idx);
  if (!el) return;
  const text = el.innerText;
  await fetch(`/api/cell/${idx}`, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({source:text})});
  if (document.getElementById('src-'+idx) === el) applyCommentHighlight(el);
}

async function deleteCell(idx) {
  if (!confirm(`Delete cell ${idx}?`)) return;
  await fetch(`/api/cell/${idx}`, {method:'DELETE'});
  await loadNotebook();
}

function toggleMdEdit(idx) {
  const src = document.getElementById('src-' + idx);
  const rendered = document.getElementById('rendered-' + idx);
  if (src.classList.contains('editing')) {
    src.classList.remove('editing');
    rendered.style.display = '';
    src.contentEditable = 'false';
    saveEdit(idx).then(()=>loadNotebook());
  } else {
    src.classList.add('editing');
    rendered.style.display = 'none';
    src.contentEditable = 'true';
    src.focus();
  }
}

// ── FAB / add sheet ───────────────────────────────────────────────────────────
function openAddSheet() { document.getElementById('add-sheet').classList.add('open'); document.getElementById('new-source').focus(); }
function closeAddSheet() { document.getElementById('add-sheet').classList.remove('open'); document.getElementById('new-source').value = ''; }
async function addCellAtEnd() {
  const src = document.getElementById('new-source').value;
  const type = document.getElementById('new-type').value;
  await fetch('/api/cell', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({source:src, type, index:-1})});
  closeAddSheet();
  await loadNotebook();
}
function downloadNotebook() { window.location.href = '/api/notebook/download'; }

// ── Chat ─────────────────────────────────────────────────────────────────────
let activeModel = 'gemini';

function setModel(m) {
  activeModel = m;
  document.getElementById('btn-claude').classList.toggle('active', m === 'claude');
  document.getElementById('btn-gemini').classList.toggle('active', m === 'gemini');
  document.getElementById('chat-input').placeholder = m === 'gemini' ? 'Ask Gemini…' : 'Ask Claude…';
}

function autoResize(el) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 110) + 'px'; }

function appendMsg(role, text) {
  const box = document.getElementById('chat-messages');
  const wrap = document.createElement('div');
  wrap.className = 'msg msg-' + role;
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  const metaRow = document.createElement('div');
  metaRow.style.cssText = `display:flex;align-items:center;gap:5px;${role==='user'?'justify-content:flex-end;':''}`;
  const metaSpan = document.createElement('span');
  metaSpan.className = 'msg-meta';
  metaSpan.style.flex = '1';
  const copyBtn = document.createElement('button');
  copyBtn.className = 'copy-btn';
  copyBtn.title = 'Copy';
  copyBtn.innerHTML = COPY_SVG;
  copyBtn.onclick = () => copyToClip(bubble.innerText, copyBtn);
  metaRow.appendChild(metaSpan);
  metaRow.appendChild(copyBtn);
  wrap.appendChild(bubble);
  wrap.appendChild(metaRow);
  box.appendChild(wrap);
  box.scrollTop = box.scrollHeight;
  return wrap;
}

function showTyping() {
  const box = document.getElementById('chat-messages');
  const wrap = document.createElement('div');
  wrap.className = `msg msg-${activeModel}`;
  wrap.id = 'typing-indicator';
  wrap.innerHTML = `<div class="bubble typing-bubble"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>`;
  box.appendChild(wrap);
  box.scrollTop = box.scrollHeight;
}

function removeTyping() { const el = document.getElementById('typing-indicator'); if (el) el.remove(); }

async function openNewChatModal() {
  const list = document.getElementById('kb-checkbox-list');
  list.innerHTML = '<span style="color:var(--muted);font-size:0.8rem;">Loading…</span>';
  document.getElementById('new-chat-modal').classList.add('open');
  try {
    const r = await fetch('/api/kb'); const files = await r.json();
    list.innerHTML = '';
    if (!files.length) {
      list.innerHTML = '<span style="color:var(--muted);font-size:0.8rem;">No KB files uploaded</span>';
      document.getElementById('kb-select-all').checked = true;
      return;
    }
    files.forEach(f => {
      const row = document.createElement('div');
      row.style.cssText = 'display:flex;align-items:center;gap:8px;font-size:0.8rem;cursor:pointer;min-width:0;';
      const cb = document.createElement('input');
      cb.type = 'checkbox'; cb.className = 'kb-file-cb'; cb.value = f.name;
      cb.checked = true;
      cb.style.cssText = 'flex-shrink:0;width:16px;height:16px;cursor:pointer;';
      cb.addEventListener('change', updateKbAllState);
      const nameSpan = document.createElement('span');
      nameSpan.style.cssText = 'flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text);font-size:0.8rem;';
      nameSpan.textContent = f.name;
      const sizeSpan = document.createElement('span');
      sizeSpan.style.cssText = 'color:var(--muted);font-size:0.7rem;flex-shrink:0;';
      sizeSpan.textContent = (f.size / 1024).toFixed(1) + 'k';
      row.addEventListener('click', () => { cb.checked = !cb.checked; updateKbAllState(); });
      cb.addEventListener('click', e => e.stopPropagation());
      row.append(cb, nameSpan, sizeSpan);
      list.appendChild(row);
    });
    document.getElementById('kb-select-all').checked = true;
    document.getElementById('kb-select-all').indeterminate = false;
  } catch(e) { list.innerHTML = '<span style="color:var(--red);font-size:0.8rem;">Error loading KB</span>'; }
}
function closeNewChatModal() { document.getElementById('new-chat-modal').classList.remove('open'); }
function toggleAllKb(checked) {
  document.querySelectorAll('.kb-file-cb').forEach(cb => cb.checked = checked);
  document.getElementById('kb-select-all').indeterminate = false;
}
function updateKbAllState() {
  const all = [...document.querySelectorAll('.kb-file-cb')];
  const n = all.filter(c => c.checked).length;
  const allCb = document.getElementById('kb-select-all');
  allCb.indeterminate = n > 0 && n < all.length;
  allCb.checked = n === all.length;
}
async function confirmNewChat() {
  const cbs = [...document.querySelectorAll('.kb-file-cb')];
  const allSel = !cbs.length || cbs.every(c => c.checked);
  const kb_files = allSel ? null : cbs.filter(c => c.checked).map(c => c.value);
  await fetch('/api/new-chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({kb_files})});
  document.getElementById('chat-messages').innerHTML = '';
  document.getElementById('chat-session-label').textContent = 'new session';
  closeNewChatModal();
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
    } else if (msg.role === 'claude' || msg.role === 'gemini') {
      const wrap = appendMsg(msg.role, '');
      const bubble = wrap.querySelector('.bubble');
      const badge = document.createElement('span');
      badge.className = `model-badge ${msg.role}`;
      badge.textContent = msg.role === 'gemini' ? '✦ Gemini' : '◉ Claude';
      bubble.appendChild(badge);
      (msg.blocks || []).forEach(block => {
        if (block.type === 'thinking') {
          const el = document.createElement('div'); el.className = 'thinking-block'; el.textContent = block.text; bubble.appendChild(el);
        } else if (block.type === 'text') {
          const el = document.createElement('span'); el.style.whiteSpace = 'pre-wrap'; el.textContent = block.text; bubble.appendChild(el);
        } else if (block.type === 'tool_call') {
          addToolBlock(bubble, block.name, 'done');
        } else if (block.type === 'tool_result') {
          /* skip — historical tool results not shown */
        }
      });
      if (msg.usage) appendUsageFooter(bubble, msg.usage);
    }
  });
  box.scrollTop = box.scrollHeight;
  document.getElementById('chat-session-label').textContent = 'session active';
}

function formatUsage(usage) {
  const parts = [];
  if (usage.input_tokens) parts.push(`<span>in:${usage.input_tokens}</span>`);
  if (usage.output_tokens) parts.push(`<span>out:${usage.output_tokens}</span>`);
  if (usage.cache_read_tokens) parts.push(`<span>cache:${usage.cache_read_tokens}</span>`);
  const th = usage.output_tokens_details?.thinking_tokens || usage.thinking_tokens;
  if (th) parts.push(`<span>think:${th}</span>`);
  return parts.join('');
}

function appendUsageFooter(bubble, usage) {
  const f = document.createElement('div'); f.className = 'usage-footer'; f.innerHTML = formatUsage(usage); bubble.appendChild(f);
}

function addToolBlock(bubble, name, state) {
  const row = document.createElement('div');
  row.style.cssText = 'margin:3px 0;';
  const chip = document.createElement('span');
  chip.className = state === 'done' ? 'tool-chip done' : 'tool-chip pending';
  chip.textContent = (state === 'done' ? '✓ ' : '⚡ ') + name;
  row.appendChild(chip);
  bubble.appendChild(row);
  return chip;
}

function fillToolResult(bubble) {
  const pending = bubble.querySelectorAll('.tool-chip.pending');
  if (pending.length) {
    const last = pending[pending.length - 1];
    const name = last.textContent.replace('⚡ ', '');
    last.className = 'tool-chip done';
    last.textContent = '✓ ' + name;
  }
}

async function sendChat() {
  const input = document.getElementById('chat-input');
  const prompt = input.value.trim();
  if (!prompt) return;
  input.value = ''; input.style.height = 'auto';
  document.getElementById('chat-send').disabled = true;

  appendMsg('user', prompt);
  showTyping();
  switchTab('chat');

  const model = activeModel;
  const endpoint = model === 'gemini' ? '/api/gemini' : '/api/claude';

  let started = false, replyWrap = null, currentTextNode = null, currentThinkingNode = null;
  let currentText = '', currentThinking = '', spinner = null, finalUsage = null;

  function ensureReply() {
    if (!started) {
      removeTyping();
      replyWrap = appendMsg(model, '');
      const badge = document.createElement('span');
      badge.className = `model-badge ${model}`;
      badge.textContent = model === 'gemini' ? '✦ Gemini' : '◉ Claude';
      replyWrap.querySelector('.bubble').appendChild(badge);
      started = true;
    }
  }

  try {
    const resp = await fetch(endpoint, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({prompt})});
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
        if (data.done) { break; }
        const box = document.getElementById('chat-messages');
        if (data.thinking) {
          ensureReply();
          if (!currentThinkingNode) {
            currentThinkingNode = document.createElement('div'); currentThinkingNode.className = 'thinking-block';
            replyWrap.querySelector('.bubble').prepend(currentThinkingNode);
            spinner = new SynonymSpinner(currentThinkingNode); spinner.start();
          }
          currentThinking += data.thinking; currentThinkingNode.textContent = currentThinking;
          box.scrollTop = box.scrollHeight;
        }
        if (data.text) {
          ensureReply();
          if (spinner) { spinner.stop(); spinner = null; }
          if (!currentTextNode) { currentTextNode = document.createElement('span'); currentTextNode.style.whiteSpace = 'pre-wrap'; replyWrap.querySelector('.bubble').appendChild(currentTextNode); }
          currentText += data.text; currentTextNode.textContent = currentText;
          box.scrollTop = box.scrollHeight;
        }
        if (data.tool_call) {
          ensureReply();
          if (spinner) { spinner.stop(); spinner = null; }
          currentTextNode = null; currentText = ''; currentThinkingNode = null; currentThinking = '';
          addToolBlock(replyWrap.querySelector('.bubble'), data.tool_call.name, 'pending');
          box.scrollTop = box.scrollHeight;
        }
        if (data.tool_result) {
          ensureReply();
          fillToolResult(replyWrap.querySelector('.bubble'));
        }
        if (data.usage) finalUsage = data.usage;
      }
    }
    if (!started) { removeTyping(); replyWrap = appendMsg(model, '(no response)'); }
    if (spinner) { spinner.stop(); spinner = null; }
    if (finalUsage && replyWrap) appendUsageFooter(replyWrap.querySelector('.bubble'), finalUsage);
    const now = new Date().toLocaleTimeString();
    if (replyWrap) replyWrap.querySelector('.msg-meta').textContent = `✓ ${now}`;
    document.getElementById('chat-session-label').textContent = `${model} active`;
  } catch(e) {
    removeTyping();
    appendMsg(model, 'Error: ' + e.message);
  }

  document.getElementById('chat-send').disabled = false;
  await loadNotebook();
}

// ── URL modal ─────────────────────────────────────────────────────────────────
async function openUrlModal() {
  const r = await fetch('/api/server-url'); const d = await r.json();
  document.getElementById('url-input').value = d.url;
  document.getElementById('url-modal').classList.add('open');
}
function closeUrlModal() { document.getElementById('url-modal').classList.remove('open'); }
async function killKernel() {
  const btn = document.getElementById('kill-kernel-btn');
  const status = document.getElementById('kill-status');
  btn.disabled = true; btn.textContent = '■ Stopping…';
  status.style.display = 'block'; status.textContent = '';
  try {
    const r = await fetch('/api/kernel/stop', {method:'POST'}); const d = await r.json();
    if (d.stopped) { status.style.color = '#0d9e6a'; status.textContent = '✓ Kernel stopped'; btn.textContent = '■ Stopped'; }
    else { status.style.color = '#dc2626'; status.textContent = '✗ ' + (d.error || 'Failed'); btn.disabled = false; btn.textContent = '■ Stop Jupyter Kernel'; }
  } catch(e) {
    status.style.color = '#dc2626'; status.textContent = '✗ Server unreachable';
    btn.disabled = false; btn.textContent = '■ Stop Jupyter Kernel';
  }
}
async function saveUrl() {
  const url = document.getElementById('url-input').value.trim();
  if (!url) return;
  await fetch('/api/server-url', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({url})});
  closeUrlModal(); await Promise.all([loadNotebook(), loadSlug()]);
}
async function startSession() {
  const btn = document.querySelector('#url-modal .btn-primary');
  const status = document.getElementById('session-status');
  btn.disabled = true; btn.textContent = '⏳ Starting…';
  status.style.display = 'block'; status.textContent = 'Launching browser, ~30s…';
  try {
    const r = await fetch('/api/fetch-kaggle-url', {method:'POST'}); const d = await r.json();
    if (d.url) {
      document.getElementById('url-input').value = d.url;
      status.style.color = '#0d9e6a'; status.textContent = '✓ Session started — click Save & Reconnect';
      btn.textContent = '✓ Done'; loadSlug();
    } else {
      status.style.color = '#dc2626'; status.textContent = '✗ ' + (d.error || 'Failed');
      btn.disabled = false; btn.textContent = '▶ Start Session Automatically';
    }
  } catch(e) {
    status.style.color = '#dc2626'; status.textContent = '✗ Server unreachable';
    btn.disabled = false; btn.textContent = '▶ Start Session Automatically';
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
  const btn = document.getElementById('ds-dl-btn'); const out = document.getElementById('ds-output');
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
  const el = document.getElementById('ds-list'); el.textContent = 'Loading…';
  try {
    const r = await fetch('/api/datasets'); const d = await r.json();
    if (d.error) { el.textContent = 'Error: '+d.error; return; }
    const keys = Object.keys(d);
    if (!keys.length) { el.textContent = 'No datasets yet.'; return; }
    el.innerHTML = keys.map(name =>
      `<div class="ds-item"><strong>${name}</strong>` + d[name].map(f=>`<div class="ds-file">${f}</div>`).join('') + '</div>'
    ).join('');
  } catch(e) { el.textContent = 'Could not reach kernel.'; }
}

async function loadCredsStatus() {
  const r = await fetch('/api/credentials'); const d = await r.json();
  if (d.username) {
    document.getElementById('ds-username').value = d.username;
    document.getElementById('creds-status').textContent = d.has_key ? `✓ Credentials saved for ${d.username}` : '';
  }
}

// ── Knowledge Base ────────────────────────────────────────────────────────────
async function uploadKbFiles() {
  const input = document.getElementById('kb-file-input'); const status = document.getElementById('kb-upload-status');
  if (!input.files.length) { status.textContent = 'No files selected.'; return; }
  status.textContent = 'Uploading…';
  let ok = 0;
  for (const file of input.files) {
    const fd = new FormData(); fd.append('file', file);
    const r = await fetch('/api/kb/upload', {method:'POST', body:fd});
    const d = await r.json(); if (d.ok) ok++;
  }
  status.textContent = `✓ ${ok} file(s) uploaded`; input.value = ''; refreshKb();
}

async function refreshKb() {
  const el = document.getElementById('kb-list'); el.textContent = 'Loading…';
  const r = await fetch('/api/kb'); const files = await r.json();
  if (!files.length) { el.textContent = 'No files yet.'; return; }
  el.innerHTML = files.map(f => {
    const ext = f.name.split('.').pop().toLowerCase();
    const canView = ['txt','md','py','json','csv','sh','log','js','css','html'].includes(ext);
    return `<div class="ds-item">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
        <span style="font-weight:600;font-size:0.82rem;">${escHtml(f.name)}</span>
        <span style="color:var(--muted);font-size:0.68rem;">${(f.size/1024).toFixed(1)} KB</span>
      </div>
      <div style="display:flex;gap:6px;">
        ${canView ? `<button onclick="viewKbFile('${escHtml(f.name)}')" style="border:none;background:#d1fae5;color:#065f46;border-radius:4px;padding:4px 10px;font-size:0.72rem;cursor:pointer;font-weight:600;">View</button>` : ''}
        <button onclick="downloadKbFile('${escHtml(f.name)}')" style="border:none;background:#d1fae5;color:#065f46;border-radius:4px;padding:4px 10px;font-size:0.72rem;cursor:pointer;font-weight:600;">Download</button>
        <button onclick="deleteKbFile('${escHtml(f.name)}')" style="border:none;background:#fee2e2;color:var(--red);border-radius:4px;padding:4px 10px;font-size:0.72rem;cursor:pointer;font-weight:600;margin-left:auto;">✕</button>
      </div>
    </div>`;
  }).join('');
}

async function viewKbFile(name) {
  const modal = document.getElementById('kb-view-modal');
  document.getElementById('kb-view-title').textContent = 'Viewing: ' + name;
  document.getElementById('kb-view-content').textContent = 'Loading...';
  modal.classList.add('open');
  try {
    const r = await fetch(`/api/kb/${encodeURIComponent(name)}/view`);
    const d = await r.json();
    document.getElementById('kb-view-content').textContent = d.content || d.error || 'Empty file';
  } catch(e) { document.getElementById('kb-view-content').textContent = 'Error: ' + e.message; }
}

function closeKbView() { document.getElementById('kb-view-modal').classList.remove('open'); }
function downloadKbFile(name) { window.location.href = `/api/kb/${encodeURIComponent(name)}/download`; }
async function deleteKbFile(name) {
  if (!confirm(`Delete ${name}?`)) return;
  await fetch('/api/kb/' + encodeURIComponent(name), {method:'DELETE'}); refreshKb();
}

// ── Utils ─────────────────────────────────────────────────────────────────────
function escHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function stripAnsi(s) { return String(s).replace(/\x1b\[[0-9;]*m/g,''); }

// ── Copy ─────────────────────────────────────────────────────────────────────
const COPY_SVG = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';

async function copyToClip(text, btn) {
  try {
    await navigator.clipboard.writeText(text);
    if (btn) { const o = btn.innerHTML; btn.classList.add('copied'); btn.innerHTML = '✓'; setTimeout(()=>{btn.classList.remove('copied');btn.innerHTML=o;},1500); }
  } catch(e) {}
}
function copyCell(idx) { const el=document.getElementById('src-'+idx); if(el) copyToClip(el.innerText, document.getElementById('copybtn-src-'+idx)); }
function copyCellOut(idx) { const el=document.getElementById('outbody-'+idx); if(el) copyToClip(el.innerText, document.getElementById('copybtn-out-'+idx)); }

// ── Syntax highlight ──────────────────────────────────────────────────────────
function applyCommentHighlight(el) {
  const text = el.innerText;
  if (!text.trim()) return;
  el.innerHTML = text.split('\n').map(line => {
    const m = line.match(/^(\s*)(#.*)$/);
    return m ? escHtml(m[1])+'<span class="py-comment">'+escHtml(m[2])+'</span>' : escHtml(line);
  }).join('\n');
}

// ── Slug title ────────────────────────────────────────────────────────────────
async function loadSlug() {
  try {
    const r = await fetch('/api/active-slug');
    const d = await r.json();
    if (d.slug) document.getElementById('notebook-title').textContent = d.slug + '.ipynb';
  } catch(e) {}
}

// ── Init ──────────────────────────────────────────────────────────────────────
loadNotebook();
loadSlug();
loadCredsStatus();
loadChatHistory();
setInterval(() => { if (!notebook) loadNotebook(); }, 3000);
setInterval(loadNotebook, 15000);
</script>
</body>
</html>
"""
