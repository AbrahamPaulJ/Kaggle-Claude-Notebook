NEW_HTML = r"""<!DOCTYPE html>
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
    else if (o.output_type === 'execute_result' || o.output_type === 'display_data')
      html += `<span class="out-result">${escHtml(o.data?.['text/plain'] || '')}</span>`;
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
  let currentText = '';

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
  const r = await fetch('/api/server-url');
  const d = await r.json();
  document.getElementById('url-input').value = d.url;
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
      status.textContent = '✓ Session started — click Save & Reconnect';
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

// ── Utils ─────────────────────────────────────────────────────────────────────
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function stripAnsi(s) { return String(s).replace(/\x1b\[[0-9;]*m/g,''); }

// ── Init ──────────────────────────────────────────────────────────────────────
loadNotebook();
loadCredsStatus();
setInterval(loadNotebook, 15000);
</script>
</body>
</html>
"""

print("HTML length:", len(NEW_HTML))
