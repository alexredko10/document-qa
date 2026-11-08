'use strict';
const $ = id => document.getElementById(id);
const sample = 'Kubernetes is a platform for running containerized applications. It groups containers into Pods and uses Deployments to manage replicas.\n\nA Service provides a stable network endpoint for a set of Pods. Kubernetes can replace a failed Pod and schedule its replacement on an available node.';
let documentId = null;
let busy = false;
const activity = [];
const show = (id, value) => { $(id).textContent = value; };
const display = value => value === null || value === undefined ? 'N/A' : String(value);
function setBusy(value) {
  busy = value;
  $('upload').disabled = value;
  $('ask').disabled = value || !documentId;
  $('sample').disabled = value;
  $('file').disabled = value;
  $('document').disabled = value;
  $('question').disabled = value;
}
function markChanged() {
  documentId = null;
  show('answer', 'Your answer will appear here.');
  show('source-count', '0'); $('source-list').replaceChildren(); $('sources').open = false;
  renderMetadata(null);
  $('document-status').classList.remove('ready');
  show('document-status', 'Document changed · upload to continue');
  setBusy(busy);
}
$('document').addEventListener('input', markChanged);
$('sample').addEventListener('click', () => { $('document').value = sample; $('question').value = 'What does a Kubernetes Service provide?'; markChanged(); show('file-name', 'Sample document loaded'); });
$('file').addEventListener('change', async event => {
  const file = event.target.files[0];
  if (!file) return;
  if (!file.name.toLowerCase().endsWith('.txt')) { show('file-name', 'Please select a .txt file.'); return; }
  if (file.size > 1024 * 1024) { show('file-name', 'File exceeds the 1 MiB limit.'); return; }
  try { $('document').value = await file.text(); show('file-name', file.name); markChanged(); }
  catch { show('file-name', 'Could not read this file.'); }
});
const errors = {404:'Document not found. Upload it again; the service may have restarted.', 413:'Document is too large. The limit is 1 MiB.', 422:'Please check the document or question and try again.', 429:'Too many requests. Please wait and try again.', 503:'The language model is unavailable. Please try again later.'};
function renderActivity() {
  const body = $('activity-body'); body.replaceChildren();
  if (!activity.length) { const tr = document.createElement('tr'); const td = document.createElement('td'); td.colSpan = 6; td.className = 'empty'; td.textContent = 'No activity yet. Your requests will appear here.'; tr.append(td); body.append(tr); return; }
  for (const entry of activity) {
    const tr = document.createElement('tr'); tr.className = 'activity-row'; tr.tabIndex = 0;
    for (const value of [entry.time, entry.operation, entry.status, entry.requestId, entry.duration + ' ms', entry.model]) { const td = document.createElement('td'); td.textContent = value; tr.append(td); }
    const select = () => show('activity-detail', `${entry.operation} · HTTP ${entry.status} · request ID ${entry.requestId} · browser duration ${entry.duration} ms · model ${entry.model}`);
    tr.addEventListener('click', select); tr.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); select(); } }); body.append(tr);
  }
}
async function request(operation, path, payload) {
  const started = performance.now(); let response; let data;
  try {
    response = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload), cache:'no-store'});
    try { data = await response.json(); } catch { data = null; }
  } catch {
    activity.unshift({time:new Date().toLocaleTimeString(), operation, status:'Network error', requestId:'Unavailable', duration:Math.round(performance.now()-started), model:'N/A'}); activity.splice(10); renderActivity();
    throw new Error('Could not reach the service. Check the connection and try again.');
  }
  activity.unshift({time:new Date().toLocaleTimeString(), operation, status:response.status, requestId:response.headers.get('X-Request-ID') || 'Unavailable', duration:Math.round(performance.now()-started), model:display(data?.llm?.actual_model)}); activity.splice(10); renderActivity();
  if (!response.ok) throw new Error(errors[response.status] || `Request failed (HTTP ${response.status}). Please try again.`);
  return data;
}
$('upload').addEventListener('click', async () => {
  if (!$('document').value.trim()) { show('document-status', 'Add document content before uploading.'); return; }
  setBusy(true); show('document-status', 'Uploading document…');
  try { const data = await request('Upload', '/documents', {text:$('document').value}); documentId = data.document_id; $('document-status').classList.add('ready'); show('document-status', 'Document ready for questions'); show('ask-status', 'Document ready. Ask your first question.'); $('ask-status').classList.remove('error'); }
  catch (error) { documentId = null; $('document-status').classList.remove('ready'); show('document-status', error.message); }
  finally { setBusy(false); }
});
function renderMetadata(info) {
  const invoked = info?.invoked;
  show('provider', invoked ? display(info.provider) : 'Not invoked');
  show('requested-model', invoked ? display(info.requested_model) : 'N/A');
  show('actual-model', invoked ? display(info.actual_model) : 'N/A');
  show('tokens', invoked ? `${display(info.input_tokens)} / ${display(info.output_tokens)}` : 'N/A');
  show('llm-duration', invoked && info.duration_ms != null ? `${info.duration_ms} ms` : 'N/A');
  show('cost', invoked && info.cost_usd != null ? `$${info.cost_usd}` : 'N/A');
}
$('ask').addEventListener('click', async () => {
  const question = $('question').value.trim();
  if (!documentId || !question) { show('ask-status', 'Enter a question first.'); $('ask-status').classList.add('error'); return; }
  setBusy(true); $('ask-status').classList.remove('error'); show('ask-status', 'Finding an answer…');
  try {
    const data = await request('Ask', '/ask', {document_id:documentId, question});
    show('answer', data.answer || 'No answer returned.'); show('source-count', data.source_chunks.length); $('source-list').replaceChildren();
    for (const chunk of data.source_chunks) { const item = document.createElement('div'); item.className = 'source-item'; const meta = document.createElement('div'); meta.className = 'source-meta'; meta.textContent = `CHUNK ${chunk.index} · SCORE ${Number(chunk.score).toFixed(3)}`; const text = document.createElement('div'); text.textContent = chunk.text; item.append(meta, text); $('source-list').append(item); }
    renderMetadata(data.llm); show('ask-status', 'Answer received.');
  } catch (error) { show('ask-status', error.message); $('ask-status').classList.add('error'); }
  finally { setBusy(false); }
});
$('question').addEventListener('keydown', event => { if (event.key === 'Enter' && !$('ask').disabled) { event.preventDefault(); $('ask').click(); } });
