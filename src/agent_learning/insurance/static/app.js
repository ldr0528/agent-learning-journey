'use strict';

// The server owns conversations, confirmed briefs and run state. The browser
// renders returned facts and never invents progress or product information.
const $ = (id) => document.getElementById(id);
const state = {
  csrf: '', dimensions: [], products: [], sessions: [], catalog: 'demo', current: null,
  run: null, events: [], lastSeq: 0, pollTimer: null, epoch: 0, pending: false,
  localMessage: null, report: null, reportVersions: [], nextIntent: 'intake',
  pendingCatalog: null, retryAction: null, evidenceTrigger: null, formDirty: false,
};
const terminalStates = new Set(['succeeded', 'failed', 'cancelled', 'interrupted']);
const statusLabels = {
  needs_input: '等待补充需求', needs_confirmation: '等待确认需求', ready: '需求已确认',
  completed: '比较已整理', completed_with_gaps: '比较已整理 · 有待确认项',
  call_limit: '达到请求上限 · 部分结果', tool_limit: '达到查证上限 · 部分结果',
  model_error: '本次处理未完成', cancelled: '已停止', interrupted: '任务已中断',
  queued: '等待开始', running: '正在处理', cancelling: '正在停止',
  answered: '依据现有资料说明', partial_answer: '部分问题仍缺少依据', needs_report: '请先确认需求并查证',
  draft: '需求草稿', failed: '处理未完成', succeeded: '处理已结束',
};
const scenarios = {
  self: '我想给自己了解医疗险，主要关心普通门诊是否保障和以后怎样续保。请先帮我整理比较需求。',
  parents: '我想帮父母了解医疗险，比较关注续保条件和医院范围。哪些信息需要先确认？',
  compare: '我想从已收录的两份医疗险资料中比较保障差异，重点看普通门诊和续保。请让我确认产品和资料版本。',
};
const emptyRequest = () => ({question: '', profile: {focus: [], age: null, annual_budget: null, social_insurance: 'unknown'}, selections: []});
function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined && text !== null) element.textContent = String(text);
  if (className) element.className = className;
  return element;
}
function button(text, className, action) {
  const element = node('button', text, className);
  element.type = 'button';
  if (action) element.addEventListener('click', action);
  return element;
}
function showNotice(message, error = false) {
  $('notice').textContent = message;
  $('notice').className = 'notice' + (error ? ' error' : '');
  $('notice').hidden = !message;
}
function announce(message) { $('liveAnnouncement').textContent = message; }
function isRunning() { return state.run && !terminalStates.has(state.run.status); }
function isBusy() { return state.pending || Boolean(isRunning()); }
function updateControls() {
  const busy = isBusy();
  $('sendMessage').disabled = busy || !$('messageInput').value.trim();
  $('briefFields').disabled = busy;
  $('confirmBrief').disabled = busy;
  $('catalogSelect').disabled = busy;
  $('modeSelect').disabled = busy;
  $('messageInput').disabled = state.pending;
  for (const element of document.querySelectorAll('#newSession, #mobileNewSession, .session-item')) element.disabled = state.pending;
  $('sendLabel').textContent = busy ? '处理中' : '发送';
  $('cancelRun').disabled = !isRunning() || state.run.status === 'cancelling';
  $('cancelRun').hidden = !isRunning();
  $('cancelRun').textContent = state.run?.status === 'cancelling' ? '正在停止' : '停止查证';
  $('composerHint').textContent = isRunning()
    ? '正在处理当前任务，完成后可继续发送'
    : state.nextIntent === 'followup' ? '正在追问当前报告 · 可切换为补充需求' : 'Enter 发送 · Shift + Enter 换行';
}
async function api(path, options = {}) {
  const headers = {...options.headers};
  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    headers['X-CSRF-Token'] = state.csrf;
  }
  let response;
  try { response = await fetch(path, {...options, headers, cache: 'no-store'}); }
  catch { throw new Error('暂时无法连接本机服务。已保存的咨询仍在本机，请检查服务后重试。'); }
  let payload;
  try { payload = await response.json(); }
  catch { throw new Error('服务返回内容无法读取，请稍后重试。'); }
  if (!response.ok) {
    const error = new Error(payload.error || '操作未完成，请稍后重试。');
    error.status = response.status;
    throw error;
  }
  return payload;
}
const post = (path, payload) => api(path, {method: 'POST', body: JSON.stringify(payload)});
async function submitJob(path, payload) {
  // Retrying the same job key is safe when the response was lost after acceptance.
  try { return await post(path, payload); }
  catch (error) {
    if (error.status) throw error;
    return post(path, payload);
  }
}
function requestId() { return crypto.randomUUID(); }
function setLocation(id) {
  const url = new URL(location.href);
  if (id) url.searchParams.set('session', id); else url.searchParams.delete('session');
  history.replaceState(null, '', url);
}
function catalogDescription() {
  return state.catalog === 'official'
    ? '官方公开资料节选：快照不代表完整合同或当前在售；未摘录内容保持待确认。'
    : '自拟教学案例：用于理解保障差异，不对应在售保险产品。';
}
function updateMode() {
  const live = $('modeSelect').value === 'live';
  $('modeNote').textContent = live
    ? '模型辅助会调用已配置的模型服务；产品事实仍以所选版本的资料为依据。'
    : '资料模式使用固定规则整理需求与已有资料，不调用模型。';
  $('modeNote').className = 'mode-note' + (live ? ' live' : '');
}
async function loadProducts(kind) {
  const result = await api('/api/products?catalog=' + encodeURIComponent(kind));
  return result.products || [];
}
function dateLabel(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat('zh-CN', {month: 'numeric', day: 'numeric'}).format(date);
}
function renderSessions() {
  for (const target of [$('sessionList'), $('mobileSessionList')]) {
    target.replaceChildren();
    if (!state.sessions.length) {
      target.append(node('p', '还没有咨询记录。\n从一个你关心的问题开始。', 'sidebar-empty'));
      continue;
    }
    for (const session of state.sessions) {
      const item = button('', 'session-item' + (session.id === state.current?.id ? ' active' : ''), () => {
        $('navDialog').close();
        openSession(session.id).catch(error => showNotice(error.message, true));
      });
      item.setAttribute('aria-current', session.id === state.current?.id ? 'true' : 'false');
      item.disabled = state.pending;
      item.append(node('span', session.title || '医疗险资料咨询', 'session-name'));
      const detail = node('span', null, 'session-detail');
      const active = session.active_run && !terminalStates.has(session.active_run.status);
      detail.append(node('span', null, 'dot' + (active ? ' running' : '')),
        node('span', active ? '正在处理' : session.result_stale ? '需求已更新' : (statusLabels[session.status] || '咨询记录')),
        node('span', dateLabel(session.updated_at)));
      item.append(detail);
      target.append(item);
    }
  }
}
async function refreshSessions() {
  const result = await api('/api/sessions');
  state.sessions = result.sessions || [];
  renderSessions();
}
function renderFocus(selected) {
  $('focusOptions').replaceChildren();
  for (const dimension of state.dimensions) {
    const label = node('label', null, 'focus-chip');
    const input = document.createElement('input');
    input.type = 'checkbox'; input.name = 'focus'; input.value = dimension.key;
    input.checked = selected.includes(dimension.key);
    label.append(input, node('span', dimension.label));
    $('focusOptions').append(label);
  }
}
function updateSelectionCount() {
  const count = $('productList').querySelectorAll('input:checked').length;
  $('selectionCount').textContent = count ? `已选 ${count} 份` : '尚未选择';
}
function renderProducts(selected) {
  const selectedKeys = new Set(selected.map(item => item.product_id + '@' + item.version));
  $('productList').replaceChildren();
  for (const product of state.products) {
    const card = node('label', null, 'product-card');
    const top = node('div', null, 'product-top');
    const input = document.createElement('input');
    input.type = 'checkbox'; input.name = 'product';
    input.dataset.productId = product.product_id; input.dataset.version = product.version;
    input.checked = selectedKeys.has(product.product_id + '@' + product.version);
    input.addEventListener('change', () => {
      if ($('productList').querySelectorAll('input:checked').length > 3) {
        input.checked = false;
        showNotice('一次最多比较三份资料，请先取消其中一份。');
      }
      updateSelectionCount();
    });
    const text = node('div');
    text.append(node('span', product.name, 'product-title'), node('span', '资料版本：' + product.version, 'product-version'),
      node('span', product.data_kind === 'official_excerpt' ? '官方资料节选' : '教学资料', 'product-kind'));
    top.append(input, text); card.append(top);
    const preview = (product.preview?.facts || []).find(fact => fact.dimension === 'coverage' && fact.status === 'known');
    if (preview?.text) {
      const details = node('details', null, 'product-description');
      details.append(node('summary', '查看已收录的保障说明'), node('p', preview.text));
      // Details are outside the checkbox's activation path when clicked.
      details.addEventListener('click', event => event.stopPropagation());
      card.append(details);
    }
    $('productList').append(card);
  }
  updateSelectionCount();
}
function renderBrief() {
  const proposal = state.current?.proposal;
  const request = proposal?.request || state.current?.request || emptyRequest();
  const profile = request.profile || {};
  $('briefQuestion').value = request.question || '';
  $('ageInput').value = profile.age ?? '';
  $('budgetInput').value = profile.annual_budget ?? '';
  $('socialInput').value = profile.social_insurance || 'unknown';
  renderFocus(profile.focus || []);
  renderProducts(request.selections || []);
  $('catalogDescription').textContent = catalogDescription();
  $('clarifyList').replaceChildren(...(proposal?.questions || []).map(question => node('li', question)));
  $('clarifyCallout').hidden = !(proposal?.questions || []).length;
  const summary = proposal?.summary;
  $('briefIntro').textContent = typeof summary === 'string' && summary ? summary : '需求可以随时补充；比较前请确认产品与资料版本。';
  $('briefState').textContent = state.current?.result_stale
    ? '需求已改变。已有报告属于之前的需求，确认后将重新查证。'
    : state.current?.confirmed_version === state.current?.brief_version && state.current
      ? '当前需求已确认。修改产品或关注点后，将按新需求重新查证。'
      : '确认后，按所选产品版本查证全部九个维度。';
  state.formDirty = false;
}
function readBrief() {
  return {
    question: $('briefQuestion').value.trim(),
    profile: {
      focus: [...$('focusOptions').querySelectorAll('input:checked')].map(input => input.value),
      age: $('ageInput').value === '' ? null : Number($('ageInput').value),
      annual_budget: $('budgetInput').value === '' ? null : Number($('budgetInput').value),
      social_insurance: $('socialInput').value,
    },
    selections: [...$('productList').querySelectorAll('input:checked')].map(input => ({product_id: input.dataset.productId, version: input.dataset.version})),
  };
}
function showPanel(name = 'brief') {
  if (name === 'report' && !state.report) return;
  $('resultPanel').hidden = false;
  $('workArea').classList.add('has-panel');
  for (const tab of document.querySelectorAll('[data-panel]')) {
    const selected = tab.dataset.panel === name;
    tab.setAttribute('aria-selected', String(selected)); tab.tabIndex = selected ? 0 : -1;
  }
  $('briefPanel').hidden = name !== 'brief'; $('reportPanel').hidden = name !== 'report';
  $('panelScroll').scrollTop = 0;
}
function closePanel() {
  $('resultPanel').hidden = true;
  $('workArea').classList.remove('has-panel');
}
function safeUrl(value) {
  try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password ? url.href : null; }
  catch { return null; }
}
function showEvidence(fact, trigger) {
  state.evidenceTrigger = trigger;
  const source = fact.source || {};
  const content = $('evidenceContent'); content.replaceChildren();
  content.append(node('div', fact.product_name || fact.product_id || '所选资料', 'source-product'),
    node('p', '资料版本：' + (fact.version || '未标明'), 'source-meta'),
    node('p', fact.data_kind === 'official_excerpt' ? '官方资料节选；以所标片段和条件为准。' : '自拟教学资料，不对应在售保险产品。', 'source-meta'),
    node('div', '资料内容', 'source-label'), node('div', fact.text || '该项未提供明确内容。', 'source-text'));
  if (fact.conditions?.length) {
    content.append(node('div', '一起阅读这些条件', 'source-label'));
    const list = node('ul', null, 'source-conditions');
    list.append(...fact.conditions.map(condition => node('li', condition))); content.append(list);
  }
  content.append(node('div', '来源与定位', 'source-label'), node('p', source.title || '教学目录', 'source-meta'),
    node('p', fact.locator || source.locator || '未标明条款位置', 'source-meta'));
  if (source.checked_at) content.append(node('p', '核对日期：' + source.checked_at, 'source-meta'));
  if (fact.data_kind === 'official_excerpt') content.append(node('p', source.effective_date ? '生效日期：' + source.effective_date : '资料快照不是合同生效版本；生效日期尚未核实。', 'source-meta'));
  const url = safeUrl(source.url);
  if (url) { const link = node('a', '打开原始来源 ↗', 'source-link'); link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer'; content.append(link); }
  content.append(node('p', fact.evidence_id || '', 'source-id'));
  if (!$('evidenceDialog').open) $('evidenceDialog').showModal();
}
function sourceButton(fact, label) {
  const element = button(label || '查看依据 ↗', 'citation');
  element.setAttribute('aria-label', '查看依据：' + (fact.product_name || '') + ' ' + (fact.locator || fact.evidence_id || ''));
  element.addEventListener('click', () => showEvidence(fact, element));
  return element;
}
function messageContent(content, sources) {
  const body = node('div', null, 'message-body');
  const lookup = new Map(sources.map((fact, index) => [fact.evidence_id, {fact, index}]));
  const text = typeof content === 'string' ? content : '';
  const pattern = /\[([^\]\n]{1,160})\]/g;
  let last = 0;
  for (const match of text.matchAll(pattern)) {
    body.append(document.createTextNode(text.slice(last, match.index)));
    const found = lookup.get(match[1]);
    body.append(found ? sourceButton(found.fact, '依据 ' + (found.index + 1)) : document.createTextNode(match[0]));
    last = match.index + match[0].length;
  }
  body.append(document.createTextNode(text.slice(last)));
  return body;
}
function renderMessages() {
  const messages = [...(state.current?.messages || [])];
  const last = messages[messages.length - 1];
  if (state.localMessage && !(last?.role === 'user' && last.content === state.localMessage)) messages.push({role: 'user', content: state.localMessage});
  $('welcome').hidden = messages.length > 0 || Boolean(state.current?.result);
  $('messageList').replaceChildren();
  for (const message of messages) {
    const human = message.role === 'user';
    if (!['user', 'assistant'].includes(message.role)) continue;
    const row = node('article', null, 'message ' + (human ? 'user' : 'assistant'));
    if (!human) row.append(node('span', '知', 'avatar'));
    const content = node('div', null, 'message-content');
    if (!human) content.append(node('div', '知保 · ' + (message.kind === 'report' ? '资料比较' : message.mode === 'offline' ? '资料整理' : '咨询助手'), 'message-role'));
    const sources = Array.isArray(message.sources) ? message.sources : [];
    content.append(messageContent(message.content, sources));
    if (!human && sources.length) {
      const citations = node('div', null, 'citations');
      sources.forEach((fact, index) => citations.append(sourceButton(fact, '依据 ' + (index + 1)))); content.append(citations);
    }
    if (!human && message.kind === 'intake' && state.current?.proposal) {
      const actions = node('div', null, 'message-actions'); actions.append(button('查看并确认比较需求 →', 'message-action', () => showPanel('brief'))); content.append(actions);
    }
    if (!human && message.kind === 'report') {
      const index = state.reportVersions.findIndex(item => item.revision === message.report_revision);
      const actions = node('div', null, 'message-actions');
      const open = button('查看第 ' + message.report_revision + ' 版报告 →', 'message-action', () => {
        const selected = state.reportVersions[index];
        if (!selected) return;
        $('reportVersion').value = String(index); renderReport(selected.result); showPanel('report');
      });
      open.disabled = index < 0;
      if (index < 0) open.title = '该版报告已不在最近保存的历史中。';
      actions.append(open); content.append(actions);
    }
    if (!human && message.report_revision && message.kind !== 'report') content.append(node('p', '依据第 ' + message.report_revision + ' 版报告；后续需求变化不会改写此条记录。', 'message-note'));
    if (!human && ['model_error', 'cancelled', 'needs_report', 'partial_answer'].includes(message.status)) content.append(node('p', statusLabels[message.status], 'message-note'));
    row.append(content); $('messageList').append(row);
  }
  if (state.current?.result && !messages.some(message => message.role === 'assistant' && message.kind === 'report')) {
    const entry = node('article', null, 'message assistant'); entry.append(node('span', '知', 'avatar'));
    const content = node('div', null, 'message-content');
    content.append(node('div', '本次资料比较', 'message-role'), node('p', state.current.result_stale ? '已有一份较早需求的报告。确认新需求后，可以重新查证。' : (statusLabels[state.current.result.status] || '已有比较结果') + '。可以查看关注点与完整对照，也可以继续追问。', 'message-body'));
    const actions = node('div', null, 'message-actions'); actions.append(button('查看比较报告 →', 'message-action', () => showPanel('report'))); content.append(actions); entry.append(content); $('messageList').append(entry);
  }
}
function scrollToLatest() { requestAnimationFrame(() => { $('conversationScroll').scrollTop = $('conversationScroll').scrollHeight; }); }
function renderIntentControls() {
  const validReport = state.current?.result && !state.current.result_stale;
  $('quickFollowups').replaceChildren();
  $('quickFollowups').hidden = !validReport;
  if (!validReport) { state.nextIntent = 'intake'; return; }
  const setIntent = (intent, text = '') => {
    state.nextIntent = intent;
    if (text) $('messageInput').value = text;
    $('messageInput').placeholder = intent === 'intake' ? '补充或修改你的关注点；新需求需确认后重新查证。' : '针对当前报告继续问，例如：两份资料的续保条件有何不同？';
    renderIntentControls(); updateControls(); $('messageInput').focus();
  };
  const ask = button('追问报告', '', () => setIntent('followup'));
  const edit = button('补充需求', '', () => setIntent('intake'));
  ask.setAttribute('aria-pressed', String(state.nextIntent === 'followup'));
  edit.setAttribute('aria-pressed', String(state.nextIntent === 'intake'));
  $('quickFollowups').append(ask, edit,
    button('为什么报价仍待确认？', '', () => setIntent('followup', '为什么预算已经填写，仍然不能判断哪份方案符合预算？')));
}
function appendCellContent(target, cell, sourceMap, showProduct = false) {
  if (showProduct) target.append(node('span', cell.product_name || cell.product_id, 'fact-product'));
  if (cell.status && cell.status !== 'known') target.append(node('span', cell.status === 'conflict' ? '资料存在冲突' : '资料待确认', 'fact-state ' + cell.status));
  target.append(node('p', cell.text || '尚未取得该项资料。', 'fact-text'));
  if (cell.conditions?.length) { const list = node('ul', null, 'fact-conditions'); list.append(...cell.conditions.map(condition => node('li', condition))); target.append(list); }
  const citations = node('div', null, 'citations');
  for (const id of cell.evidence_ids || []) { const fact = sourceMap.get(id); if (fact) citations.append(sourceButton(fact)); }
  if (citations.childElementCount) target.append(citations);
}
function renderReport(report) {
  state.report = report;
  $('reportTab').disabled = !report;
  if (!report) return;
  const sourceMap = new Map((report.sources || []).map(fact => [fact.evidence_id, fact]));
  $('reportStatus').textContent = statusLabels[report.status] || '查看比较结果';
  $('reportStatus').className = 'status-tag' + (report.status !== 'completed' ? ' gaps' : '');
  $('reportQuestion').textContent = report.request?.question || '';
  const isCurrent = report === state.current?.result;
  $('reportDataNote').textContent = (isCurrent && state.current.result_stale ? '这是较早需求的结果，请确认新需求后重新查证。 ' : !isCurrent ? '正在查看历史结果；追问使用当前有效报告。 ' : '') + catalogDescription();
  const rows = report.rows || [];
  const focus = report.request?.profile?.focus || [];
  const ordered = [...rows].sort((a, b) => {
    const index = row => focus.includes(row.dimension) ? focus.indexOf(row.dimension) : focus.length + rows.indexOf(row);
    return index(a) - index(b);
  });
  $('focusSummary').replaceChildren();
  for (const row of ordered.filter(row => focus.includes(row.dimension))) {
    const card = node('section', null, 'focus-card'); card.append(node('h3', row.label || row.dimension));
    for (const cell of row.cells || []) { const block = node('div', null, 'product-fact'); appendCellContent(block, cell, sourceMap, true); card.append(block); }
    $('focusSummary').append(card);
  }
  if (!$('focusSummary').childElementCount) $('focusSummary').append(node('p', '当前还没有可展示的关注项证据。请先补充需求或继续查证。', 'field-help'));
  $('gapsList').replaceChildren(...(report.gaps || []).map(gap => node('li', gap)));
  if (!$('gapsList').childElementCount) $('gapsList').append(node('li', '当前资料未标出其他缺口，仍需结合适用条件阅读。'));
  $('nextStepsList').replaceChildren(...(report.next_steps || []).map(step => node('li', step)));
  const table = $('comparisonTable'); table.tHead.replaceChildren(); table.tBodies[0].replaceChildren();
  const selections = report.request?.selections || [];
  const header = node('tr'); const corner = node('th', '比较维度'); corner.scope = 'col'; header.append(corner);
  for (const selected of selections) {
    const cell = rows.flatMap(row => row.cells || []).find(item => item.product_id === selected.product_id && item.version === selected.version);
    const th = node('th', cell?.product_name || selected.product_id); th.scope = 'col'; th.append(node('span', selected.version, 'table-version')); header.append(th);
  }
  table.tHead.append(header); $('mobileMatrix').replaceChildren();
  for (const row of ordered) {
    const tr = node('tr'); const title = node('th', row.label || row.dimension); title.scope = 'row'; tr.append(title);
    const mobile = node('details', null, 'mobile-dimension'); mobile.open = focus.includes(row.dimension); mobile.append(node('summary', row.label || row.dimension));
    for (const selection of selections) {
      const cell = (row.cells || []).find(item => item.product_id === selection.product_id && item.version === selection.version);
      const td = node('td');
      if (cell) { appendCellContent(td, cell, sourceMap); const block = node('div', null, 'product-fact'); appendCellContent(block, cell, sourceMap, true); mobile.append(block); }
      else td.append(node('span', '尚未取得依据', 'fact-state'));
      tr.append(td);
    }
    table.tBodies[0].append(tr); $('mobileMatrix').append(mobile);
  }
}
function renderVersions() {
  const saved = state.current;
  state.reportVersions = saved?.result ? [{revision: saved.revision, result: saved.result, current: true}, ...(saved.history || []).slice().reverse().filter(item => item.result)] : [];
  $('reportVersion').replaceChildren();
  state.reportVersions.forEach((item, index) => {
    const option = node('option', (item.current ? '当前 · ' : '历史 · ') + '第 ' + (item.revision || index + 1) + ' 版'); option.value = String(index); $('reportVersion').append(option);
  });
  renderReport(saved?.result || null);
}
function renderCurrent() {
  const firstQuestion = state.current?.messages?.find(message => message.role === 'user')?.content;
  $('sessionTitle').textContent = state.current?.proposal?.request?.question || state.current?.title || firstQuestion || state.current?.request?.question || '新的咨询';
  $('sessionSubtitle').textContent = state.current ? (state.current.result_stale ? '需求已更新 · 请重新确认并查证' : '已保存在本机 · 可继续补充与追问') : '看清保障，也看清条件';
  $('catalogSelect').value = state.catalog;
  renderBrief(); renderVersions(); renderMessages(); renderIntentControls(); renderSessions(); updateControls();
}
function stopPolling() { if (state.pollTimer) clearTimeout(state.pollTimer); state.pollTimer = null; }
async function openSession(id) {
  const epoch = ++state.epoch;
  stopPolling(); state.pending = true; updateControls(); showNotice('');
  try {
    const saved = await api('/api/sessions/' + encodeURIComponent(id));
    const products = await loadProducts(saved.catalog_kind || 'demo');
    if (epoch !== state.epoch) return;
    state.current = saved; state.catalog = saved.catalog_kind || 'demo'; state.products = products;
    state.localMessage = null; state.report = null; state.run = null; state.events = []; state.lastSeq = 0;
    state.nextIntent = saved.result && !saved.result_stale && !saved.proposal ? 'followup' : 'intake';
    $('modeSelect').value = 'offline'; updateMode(); setLocation(saved.id || id); renderCurrent();
    if (saved.proposal || !saved.result) showPanel('brief'); else showPanel('report');
    $('jobCard').hidden = true;
    if (saved.active_run && !terminalStates.has(saved.active_run.status)) {
      state.run = {...saved.active_run, session_id: id}; renderJob(); pollRun(saved.active_run.id, epoch);
    }
    scrollToLatest();
  } finally { if (epoch === state.epoch) { state.pending = false; updateControls(); } }
}
async function newSession(kind = state.catalog) {
  const epoch = ++state.epoch;
  stopPolling(); state.pending = true; updateControls();
  try {
    const products = await loadProducts(kind);
    if (epoch !== state.epoch) return;
    state.current = null; state.catalog = kind; state.products = products; state.run = null;
    state.events = []; state.lastSeq = 0; state.localMessage = null; state.nextIntent = 'intake'; state.retryAction = null;
    $('messageInput').value = ''; $('modeSelect').value = 'offline'; $('jobCard').hidden = true;
    $('messageInput').placeholder = '例如：我想了解普通门诊和续保，先帮我理清需要比较什么。';
    updateMode(); setLocation(null); renderCurrent(); closePanel(); showNotice(''); $('navDialog').close();
    $('messageInput').focus();
  } finally { if (epoch === state.epoch) { state.pending = false; updateControls(); } }
}
async function ensureSession() {
  if (state.current) return state.current;
  const created = await post('/api/sessions', {catalog: state.catalog});
  state.current = await api('/api/sessions/' + encodeURIComponent(created.session_id));
  setLocation(state.current.id); return state.current;
}
function readableEvent(event) {
  if (typeof event.message === 'string' && event.message) return event.message;
  return ({queued: '任务已加入队列', started: '开始处理当前任务', completed: '当前步骤已完成', cancelling: '已请求停止，等待当前操作结束'})[event.type] || '';
}
function renderJob() {
  if (!state.run) { $('jobCard').hidden = true; return; }
  $('jobCard').hidden = false;
  const finished = terminalStates.has(state.run.status);
  $('jobCard').className = 'job-card' + (finished ? ' finished' : '');
  const noun = state.run.kind === 'comparison' ? '查证资料' : state.run.kind === 'followup' ? '核对你的追问' : '整理比较需求';
  $('jobTitle').textContent = finished
    ? ({succeeded: '本次处理已结束', cancelled: '本次任务已停止', interrupted: '任务已中断', failed: '本次任务未完成'})[state.run.status]
    : state.run.status === 'cancelling' ? '正在停止当前任务' : state.run.status === 'queued' ? '任务已收到' : '正在' + noun;
  $('jobDescription').textContent = state.run.error || (state.run.status === 'cancelling' ? '当前请求结束后停止；已取得的资料会保留。' : finished ? '结果与后续说明已保留在这次咨询中。' : '下面显示已发生的步骤；你可以离开页面，稍后恢复。');
  $('jobIndicator').className = 'job-indicator' + (finished ? (state.run.status === 'succeeded' ? ' finished' : ' stopped') : '');
  const events = state.events.filter(event => readableEvent(event));
  $('eventList').hidden = finished;
  $('eventList').replaceChildren(...events.slice(-5).map(event => node('li', readableEvent(event))));
  $('eventDetails').textContent = events.map(event => `${event.seq}. ${readableEvent(event)}`).join('\n');
  updateControls();
}
async function pollRun(id, epoch) {
  if (epoch !== state.epoch || state.run?.id !== id) return;
  try {
    const run = await api('/api/runs/' + encodeURIComponent(id) + '?after_seq=' + state.lastSeq);
    if (epoch !== state.epoch || state.run?.id !== id) return;
    for (const event of run.events || []) if (event.seq > state.lastSeq) state.events.push(event);
    state.lastSeq = Math.max(state.lastSeq, run.last_seq || 0, ...state.events.map(event => event.seq || 0));
    state.run = run; renderJob();
    if (terminalStates.has(run.status)) {
      const saved = await api('/api/sessions/' + encodeURIComponent(run.session_id));
      if (epoch !== state.epoch) return;
      state.current = saved; state.localMessage = null; state.pending = false;
      state.nextIntent = saved.result && !saved.result_stale && !saved.proposal ? 'followup' : 'intake';
      renderCurrent(); renderJob();
      if (run.kind === 'comparison' && saved.result) showPanel('report');
      else if (saved.proposal) {
        if (window.matchMedia('(min-width: 761px)').matches) showPanel('brief');
        else closePanel();
      }
      if (run.status === 'failed' || run.status === 'interrupted') showNotice(run.error || '本次任务未完成，已有需求与结果已保留。', true);
      else showNotice('');
      await refreshSessions(); scrollToLatest(); announce('本次处理结束，请查看消息与结果。');
      return;
    }
    state.pollTimer = setTimeout(() => pollRun(id, epoch), 850);
  } catch (error) {
    if (epoch !== state.epoch) return;
    showNotice('暂时无法取得任务状态，正在重新连接。不会重复提交任务。', true);
    state.pollTimer = setTimeout(() => pollRun(id, epoch), 2500);
  }
}
function acceptRun(run) {
  stopPolling(); state.run = run; state.events = run.events || [];
  state.lastSeq = run.last_seq || 0; state.pending = false; state.retryAction = null;
  renderMessages(); renderJob(); scrollToLatest();
  pollRun(run.id, state.epoch);
  refreshSessions().catch(() => {});
}
async function sendMessage(event) {
  event.preventDefault();
  const message = $('messageInput').value.trim();
  if (!message || isBusy()) return;
  if (message.length > 1500) { showNotice('每条消息最多 1500 字，请拆成几条发送。', true); return; }
  const epoch = state.epoch;
  state.pending = true; state.localMessage = message; showNotice(''); updateControls(); renderMessages(); scrollToLatest();
  try {
    const saved = await ensureSession();
    if (epoch !== state.epoch) return;
    const intent = state.nextIntent;
    const payload = {message, intent, mode: $('modeSelect').value, expected_version: saved.brief_version, client_request_id: requestId()};
    const run = await submitJob('/api/sessions/' + encodeURIComponent(saved.id) + '/messages', payload);
    if (epoch !== state.epoch) return;
    $('messageInput').value = ''; $('messageInput').style.height = '';
    acceptRun(run);
  } catch (error) {
    if (epoch !== state.epoch) return;
    state.pending = false; state.localMessage = null; renderMessages(); showNotice(error.message, true);
    if (error.status === 409 && state.current) { await openSession(state.current.id).catch(() => {}); showNotice(error.message, true); }
  } finally { if (epoch === state.epoch) { state.pending = false; updateControls(); } }
}
async function confirmBrief(event) {
  event.preventDefault();
  if (isBusy() || !$('briefForm').reportValidity()) return;
  const request = readBrief();
  if (!request.profile.focus.length) { showNotice('请先选择至少一个关注维度。'); $('focusOptions').querySelector('input')?.focus(); return; }
  if (request.selections.length < 2 || request.selections.length > 3) { showNotice('请选择两到三份资料，再确认比较。'); $('productList').querySelector('input')?.focus(); return; }
  const epoch = state.epoch; state.pending = true; showNotice(''); updateControls();
  try {
    const saved = await ensureSession();
    if (epoch !== state.epoch) return;
    const confirmed = await post('/api/sessions/' + encodeURIComponent(saved.id) + '/brief', {request, expected_version: saved.brief_version, confirm: true});
    if (epoch !== state.epoch) return;
    state.current = confirmed; state.formDirty = false;
    const run = await submitJob('/api/sessions/' + encodeURIComponent(saved.id) + '/runs', {mode: $('modeSelect').value, max_calls: 6, expected_version: confirmed.brief_version, client_request_id: requestId()});
    if (epoch !== state.epoch) return;
    renderCurrent(); acceptRun(run);
    if (window.matchMedia('(max-width: 760px)').matches) closePanel();
  } catch (error) {
    if (epoch !== state.epoch) return;
    showNotice(error.message, true);
    if (error.status === 409 && state.current) { await openSession(state.current.id).catch(() => {}); showNotice(error.message, true); }
  } finally { if (epoch === state.epoch) { state.pending = false; updateControls(); } }
}
function selectView(view) {
  for (const tab of document.querySelectorAll('[data-view]')) { const selected = tab.dataset.view === view; tab.setAttribute('aria-selected', String(selected)); tab.tabIndex = selected ? 0 : -1; }
  $('summaryView').hidden = view !== 'summary'; $('matrixView').hidden = view !== 'matrix';
}
function initializeEvents() {
  $('messageForm').addEventListener('submit', sendMessage);
  $('briefForm').addEventListener('submit', confirmBrief);
  $('briefForm').addEventListener('input', () => { state.formDirty = true; $('briefState').textContent = '有尚未确认的修改。确认后，按这些需求重新查证。'; });
  $('messageInput').addEventListener('input', () => { $('messageInput').style.height = 'auto'; $('messageInput').style.height = Math.min($('messageInput').scrollHeight, 180) + 'px'; updateControls(); });
  $('messageInput').addEventListener('paste', event => {
    const input = event.currentTarget;
    const pasted = event.clipboardData?.getData('text') || '';
    if (input.value.length - (input.selectionEnd - input.selectionStart) + pasted.length > 1500) {
      event.preventDefault(); showNotice('每条消息最多 1500 字，请拆成几条发送，避免遗漏内容。', true);
    }
  });
  $('messageInput').addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey && !event.isComposing && !event.metaKey && !event.ctrlKey) { event.preventDefault(); $('messageForm').requestSubmit(); } });
  for (const scenario of document.querySelectorAll('[data-scenario]')) scenario.addEventListener('click', () => { $('messageInput').value = scenarios[scenario.dataset.scenario]; updateControls(); $('messageInput').focus(); });
  for (const id of ['newSession', 'mobileNewSession']) $(id).addEventListener('click', () => newSession().catch(error => showNotice(error.message, true)));
  $('refreshHistory').addEventListener('click', () => refreshSessions().catch(error => showNotice(error.message, true)));
  $('openNav').addEventListener('click', () => $('navDialog').showModal());
  $('openBrief').addEventListener('click', () => showPanel('brief'));
  $('closePanel').addEventListener('click', () => { closePanel(); $('openBrief').focus(); });
  for (const tab of document.querySelectorAll('[data-panel]')) tab.addEventListener('click', () => showPanel(tab.dataset.panel));
  for (const tab of document.querySelectorAll('[data-view]')) tab.addEventListener('click', () => selectView(tab.dataset.view));
  for (const group of document.querySelectorAll('[role=tablist]')) group.addEventListener('keydown', event => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    const tabs = [...group.querySelectorAll('[role=tab]')].filter(tab => !tab.disabled);
    const index = tabs.indexOf(document.activeElement); if (index < 0) return;
    event.preventDefault(); const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
    tabs[next].click(); tabs[next].focus();
  });
  for (const closer of document.querySelectorAll('[data-close]')) closer.addEventListener('click', () => $(closer.dataset.close).close());
  for (const dialog of document.querySelectorAll('dialog')) dialog.addEventListener('click', event => { if (event.target === dialog) { const rect = dialog.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close(); } });
  $('evidenceDialog').addEventListener('close', () => state.evidenceTrigger?.focus());
  $('modeSelect').addEventListener('change', updateMode);
  $('catalogSelect').addEventListener('change', () => {
    const kind = $('catalogSelect').value;
    if (state.current || $('messageInput').value.trim() || state.formDirty) { state.pendingCatalog = kind; $('catalogSelect').value = state.catalog; $('changeCatalogDialog').showModal(); }
    else newSession(kind).catch(error => showNotice(error.message, true));
  });
  $('confirmCatalogChange').addEventListener('click', () => { $('changeCatalogDialog').close(); newSession(state.pendingCatalog || state.catalog).catch(error => showNotice(error.message, true)); });
  $('cancelRun').addEventListener('click', async () => {
    if (!isRunning()) return;
    $('cancelRun').disabled = true;
    try { const run = await post('/api/runs/' + encodeURIComponent(state.run.id) + '/cancel', {}); if (state.run?.id === run.id) { state.run = run; renderJob(); } }
    catch (error) { showNotice(error.message, true); updateControls(); }
  });
  $('reportVersion').addEventListener('change', () => { const selected = state.reportVersions[Number($('reportVersion').value)]; if (selected) renderReport(selected.result); });
  $('downloadReport').addEventListener('click', () => {
    if (!state.report) return;
    const blob = new Blob([JSON.stringify(state.report, null, 2)], {type: 'application/json;charset=utf-8'});
    const url = URL.createObjectURL(blob); const link = node('a'); link.href = url; link.download = '医疗险资料比较.json'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  $('downloadReport').title = '下载当前展示的 JSON 报告';
  $('editNeeds').addEventListener('click', () => { state.nextIntent = 'intake'; showPanel('brief'); renderIntentControls(); updateControls(); $('briefQuestion').focus(); });
  $('askReport').addEventListener('click', () => { state.nextIntent = state.current?.result_stale ? 'intake' : 'followup'; renderIntentControls(); updateControls(); if (window.matchMedia('(max-width: 760px)').matches) closePanel(); $('messageInput').focus(); });
}
async function initialize() {
  initializeEvents(); state.pending = true; updateControls();
  try {
    const bootstrap = await api('/api/bootstrap'); state.csrf = bootstrap.csrf_token; state.dimensions = bootstrap.dimensions || [];
    const labels = {demo: '教学案例', official: '官方节选'};
    $('catalogSelect').replaceChildren(...(bootstrap.catalogs || []).map(catalog => { const option = node('option', labels[catalog.id] || catalog.label); option.value = catalog.id; return option; }));
    state.catalog = bootstrap.default_catalog || 'demo'; state.products = await loadProducts(state.catalog);
    renderCurrent(); await refreshSessions();
    const id = new URLSearchParams(location.search).get('session');
    if (id) await openSession(id);
  } catch (error) { showNotice(error.message, true); }
  finally { state.pending = false; updateControls(); }
}
initialize();
