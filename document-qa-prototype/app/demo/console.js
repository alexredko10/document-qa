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
  $('ask').disabled = value || ($('use-context').checked && !documentId);
  $('compare').disabled = value || !documentId;
  $('use-context').disabled = value;
  $('sample').disabled = value;
  $('file').disabled = value;
  $('document').disabled = value;
  $('question').disabled = value;
}
function markChanged() {
  documentId = null;
  show('answer', 'Your answer will appear here.');
  show('source-count', '0'); $('source-list').replaceChildren(); $('sources').open = false;
  renderMetadata(null); show('retrieval', '—'); $('comparison').replaceChildren(); $('comparison').hidden = true; $('single-result').hidden = false;
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
$('use-context').addEventListener('change', () => { setBusy(busy); show('ask-status', $('use-context').checked && !documentId ? 'Upload a document to get started.' : 'Ready to ask.'); });
const errors = {501:'Context-free answers require a real generative provider; StubLLM does not support this mode.', 404:'Document not found. Upload it again; the service may have restarted.', 413:'Document exceeds the 1 MiB or semantic indexing chunk limit.', 422:'Please check the document or question and try again.', 429:'Too many requests. Please wait and try again.', 503:'The embedding or language model service is unavailable or incompatible. Please try again or re-upload the document.'};
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
  const entry = {time:new Date().toLocaleTimeString(), operation, status:response.status, requestId:response.headers.get('X-Request-ID') || 'Unavailable', duration:Math.round(performance.now()-started), model:display(data?.llm?.actual_model)};
  activity.unshift(entry); activity.splice(10); renderActivity();
  if (!response.ok) { const error = new Error(errors[response.status] || `Request failed (HTTP ${response.status}). Please try again.`); error.entry = entry; throw error; }
  return {data, entry};
}
$('upload').addEventListener('click', async () => {
  if (!$('document').value.trim()) { show('document-status', 'Add document content before uploading.'); return; }
  setBusy(true); show('document-status', 'Uploading document…');
  try { const {data} = await request('Upload', '/documents', {text:$('document').value}); documentId = data.document_id; $('document-status').classList.add('ready'); show('document-status', 'Document ready for questions'); show('ask-status', 'Document ready. Ask your first question.'); $('ask-status').classList.remove('error'); }
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
  if (($('use-context').checked && !documentId) || !question) { show('ask-status', 'Enter a question and upload a document if using context.'); $('ask-status').classList.add('error'); return; }
  setBusy(true); $('ask-status').classList.remove('error'); show('ask-status', 'Finding an answer…');
  try {
    const {data, entry} = await request($('use-context').checked ? 'Ask · RAG' : 'Ask · no RAG', '/ask', {document_id:documentId, question, use_context:$('use-context').checked});
    $('comparison').hidden = true; $('single-result').hidden = false;
    show('retrieval', retrievalLabel(data.retrieval));
    show('single-mode', data.use_context ? 'With RAG' : 'Without RAG'); show('single-request-id', entry.requestId); show('single-http-duration', `${entry.duration} ms`);
    $('sources').hidden = !data.use_context;
    show('answer', data.answer || 'No answer returned.'); show('source-count', data.source_chunks.length); $('source-list').replaceChildren();
    for (const chunk of data.source_chunks) { const item = document.createElement('div'); item.className = 'source-item'; const meta = document.createElement('div'); meta.className = 'source-meta'; meta.textContent = `CHUNK ${chunk.index} · SCORE ${Number(chunk.score).toFixed(3)}`; const text = document.createElement('div'); text.textContent = chunk.text; item.append(meta, text); $('source-list').append(item); }
    renderMetadata(data.llm); show('ask-status', 'Answer received.');
  } catch (error) { show('ask-status', error.message); $('ask-status').classList.add('error'); }
  finally { setBusy(false); }
});
$('question').addEventListener('keydown', event => { if (event.key === 'Enter' && !$('ask').disabled) { event.preventDefault(); $('ask').click(); } });

function retrievalLabel(retrieval) {
  if (!retrieval?.embedding_provider) return 'N/A';
  const kind = retrieval.embedding_provider === 'hash' ? 'SHA-256 lexical baseline' : 'Semantic embeddings';
  return `${kind} · ${display(retrieval.embedding_model)} · ${display(retrieval.retrieval_duration_ms)} ms`;
}
function comparisonResult(mode, result) {
  const section = document.createElement('section'); section.className = 'comparison-result';
  const title = document.createElement('h3'); title.textContent = mode ? 'With RAG' : 'Without RAG'; section.append(title);
  const answer = document.createElement('p'); answer.textContent = result.status === 'fulfilled' ? result.value.data.answer : result.reason.message; section.append(answer);
  const entry = result.status === 'fulfilled' ? result.value.entry : result.reason.entry;
  const info = result.status === 'fulfilled' ? result.value.data.llm : null;
  const list = document.createElement('dl');
  for (const [label, value] of [['Context mode', mode ? 'With RAG' : 'Without RAG'], ['Retrieval', retrievalLabel(result.status === 'fulfilled' ? result.value.data.retrieval : null)], ['Actual model', display(info?.actual_model)], ['Input / output tokens', `${display(info?.input_tokens)} / ${display(info?.output_tokens)}`], ['LLM duration', info?.duration_ms != null ? `${info.duration_ms} ms` : 'N/A'], ['HTTP duration', entry ? `${entry.duration} ms` : 'N/A'], ['Request ID', entry?.requestId || 'Unavailable']]) {
    const dt = document.createElement('dt'); dt.textContent = label; const dd = document.createElement('dd'); dd.textContent = value; list.append(dt, dd);
  }
  section.append(list);
  if (mode && result.status === 'fulfilled') {
    const details = document.createElement('details'); details.className = 'sources'; const summary = document.createElement('summary'); summary.textContent = `Source chunks (${result.value.data.source_chunks.length})`; details.append(summary);
    for (const chunk of result.value.data.source_chunks) { const item = document.createElement('div'); item.className = 'source-item'; const meta = document.createElement('div'); meta.className = 'source-meta'; meta.textContent = `CHUNK ${chunk.index} · SCORE ${Number(chunk.score).toFixed(3)}`; const text = document.createElement('div'); text.textContent = chunk.text; item.append(meta, text); details.append(item); }
    section.append(details);
  }
  return section;
}
$('compare').addEventListener('click', async () => {
  const question = $('question').value.trim();
  if (!documentId || !question) { show('ask-status', 'Upload a document and enter a question to compare.'); $('ask-status').classList.add('error'); return; }
  setBusy(true); $('ask-status').classList.remove('error'); show('ask-status', 'Running both requests…');
  $('single-result').hidden = true; $('comparison').hidden = false; $('comparison').replaceChildren();
  try {
    const results = await Promise.allSettled([
      request('Compare · RAG', '/ask', {document_id:documentId, question, use_context:true}),
      request('Compare · no RAG', '/ask', {question, use_context:false}),
    ]);
    $('comparison').append(comparisonResult(true, results[0]), comparisonResult(false, results[1]));
    show('ask-status', results.some(result => result.status === 'rejected') ? 'One or more requests failed; see details below.' : 'Comparison complete.');
  } finally { setBusy(false); }
});
