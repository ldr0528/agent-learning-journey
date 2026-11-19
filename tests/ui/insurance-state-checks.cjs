'use strict';

// Run with: node tests/ui/insurance-state-checks.cjs
// Pure state regressions: no browser, server, npm packages or model requests.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {webcrypto} = require('node:crypto');

const staticDirectory = path.resolve(__dirname, '../../src/agent_learning/insurance/static');
const originalCode = fs.readFileSync(path.join(staticDirectory, 'app.js'), 'utf8');
assert.match(originalCode, /initialize\(\);\s*$/);
const code = originalCode.replace(/initialize\(\);\s*$/, '');
const tests = [];
const test = (name, action) => tests.push({name, action});

function sandbox() {
  const elements = new Map();
  function element(id) {
    if (!elements.has(id)) elements.set(id, {
      id, value: '', style: {}, children: [], scrollHeight: 60,
      hidden: false, disabled: false, textContent: '',
      replaceChildren(...items) { this.children = items; },
      append(...items) { this.children.push(...items); },
      addEventListener() {}, setAttribute() {}, removeAttribute() {},
      querySelectorAll() { return []; }, querySelector() { return null; },
      focus() {}, matches() { return false; },
    });
    return elements.get(id);
  }
  const context = vm.createContext({
    console, Map, Set, URL, Error, Math, Intl, Date, JSON, crypto: webcrypto,
    document: {
      getElementById: element,
      createElement: () => ({textContent: '', addEventListener() {}, append() {}, setAttribute() {}}),
      querySelectorAll: () => [], querySelector: () => null,
    },
    window: {matchMedia: () => ({matches: false, addEventListener() {}})},
    // Delayed polling is recorded by each test; never start real timers or I/O.
    setTimeout: () => 1, clearTimeout() {}, requestAnimationFrame: callback => callback(),
    history: {replaceState() {}}, location: {href: 'http://127.0.0.1/'},
  });
  vm.runInContext(code, context);
  return {run: script => vm.runInContext(script, context), element};
}

function usableReport(subject) {
  subject.run(`state.current = {
    id: 'session-A', brief_version: 2, result_brief_version: 2, result_stale: false,
    revision: 2, result: {status: 'completed_with_gaps', sources: [{evidence_id: 'A1'}]}
  }; state.report = state.current.result;`);
}

test('only completed, evidenced, current reports allow follow-up', () => {
  const subject = sandbox(); usableReport(subject);
  assert.equal(subject.run('canAskReport()'), true);
  for (const status of ['call_limit', 'tool_limit', 'cancelled', 'needs_input', 'model_error']) {
    subject.run(`state.current.result.status = ${JSON.stringify(status)}`);
    assert.equal(subject.run('followupReady()'), false, status);
  }
  subject.run(`state.current.result.status = 'completed'; state.current.result.sources = []`);
  assert.equal(subject.run('followupReady()'), false, 'no evidence');
  subject.run(`state.current.result.sources = [{}]; state.current.result_brief_version = 1`);
  assert.equal(subject.run('followupReady()'), false, 'version mismatch');
  subject.run(`state.current.result_brief_version = 2; state.current.result_stale = true`);
  assert.equal(subject.run('followupReady()'), false, 'stale report');
  subject.run(`state.current.result_stale = false; state.current.proposal = {request: {}}`);
  assert.equal(subject.run('canAskReport()'), false, 'unconfirmed proposal');
  subject.run(`state.current.proposal = null; state.formDirty = true`);
  assert.equal(subject.run('canAskReport()'), false, 'unsaved manual changes');
});

test('lost submission responses and manual recovery reuse the original job key', async () => {
  const subject = sandbox();
  subject.run(`state.current = {id: 'session-A'};
    var attempts = []; var respond = false; var accepted = null;
    api = async (path, options) => {
      attempts.push({path, payload: JSON.parse(options.body)});
      if (!respond) throw new Error('response lost');
      return {id: 'accepted-job', session_id: 'session-A'};
    };
    showNotice = () => {}; updateControls = () => {};
    acceptRun = run => { accepted = run; };
    $('messageInput').value = '原来的问题';`);
  await assert.rejects(subject.run(`submitJob('/api/sessions/session-A/messages', {
    client_request_id: 'original-key', message: '原来的问题', intent: 'intake', mode: 'offline', expected_version: 1
  })`));
  assert.equal(subject.run('attempts.length'), 2);
  assert.equal(subject.run('state.pendingJobs.size'), 1);
  assert.equal(subject.run('isBusy()'), true, 'unknown outcome blocks a new job');
  subject.run('respond = true');
  await subject.run('recoverSubmission()');
  assert.equal(subject.run('attempts[2].payload.client_request_id'), 'original-key');
  assert.equal(subject.run('attempts[2].payload.message'), '原来的问题');
  assert.equal(subject.run('accepted.id'), 'accepted-job');
  assert.equal(subject.element('messageInput').value, '');
  assert.equal(subject.run('state.pendingJobs.size'), 0);
  assert.equal(subject.run('state.pending'), false);
});

test('definitive rejection clears the pending submission and does not retry', async () => {
  const subject = sandbox();
  subject.run(`state.current = {id: 'session-A'}; var attempts = 0;
    api = async () => { attempts++; const error = new Error('conflict'); error.status = 409; throw error; };`);
  await assert.rejects(subject.run(`submitJob('/api/sessions/session-A/messages', {client_request_id: 'key'})`));
  assert.equal(subject.run('attempts'), 1);
  assert.equal(subject.run('state.pendingJobs.size'), 0);
});

test('switching sessions keeps unsent text in its original conversation', () => {
  const subject = sandbox();
  subject.run(`state.current = {id: 'A'}; state.nextIntent = 'intake';
    $('messageInput').value = 'A 的草稿'; rememberDraft();
    state.current = {id: 'B'}; renderIntentControls = () => {}; updateControls = () => {}; restoreDraft();`);
  assert.equal(subject.element('messageInput').value, '');
  subject.run(`$('messageInput').value = 'B 的草稿'; rememberDraft(); state.current = {id: 'A'}; restoreDraft();`);
  assert.equal(subject.element('messageInput').value, 'A 的草稿');
  subject.run(`state.current = {id: 'B'}; restoreDraft();`);
  assert.equal(subject.element('messageInput').value, 'B 的草稿');
});

test('failed navigation resumes the visible task polling', async () => {
  const subject = sandbox();
  subject.run(`state.current = {id: 'A'}; state.run = {id: 'job-A', status: 'running'};
    var resumed = null; rememberDraft = () => {}; updateControls = () => {}; showNotice = () => {};
    pollRun = (id, epoch) => { resumed = {id, epoch}; }; api = async () => { throw new Error('offline'); };`);
  await assert.rejects(subject.run(`openSession('B')`));
  assert.equal(subject.run('resumed.id'), 'job-A');
  assert.equal(subject.run('resumed.epoch === state.epoch'), true);
  assert.equal(subject.run('state.current.id'), 'A');
  assert.equal(subject.run('state.pending'), false);
});

test('terminal polling remains locked until session refresh and ignores a newer task', async () => {
  const subject = sandbox();
  subject.run(`state.epoch = 1; state.run = {id: 'job-A', status: 'running'};
    var resolveSaved; renderJob = () => {}; renderCurrent = () => {}; showNotice = () => {};
    showPanel = () => {}; refreshSessions = async () => {}; announce = () => {};
    api = async path => path.startsWith('/api/runs/')
      ? {id: 'job-A', status: 'succeeded', session_id: 'A', events: [], last_seq: 0}
      : await new Promise(resolve => { resolveSaved = resolve; });`);
  const pending = subject.run(`pollRun('job-A', 1)`);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(subject.run('state.pending'), true);
  subject.run(`state.run = {id: 'job-B', status: 'running'}; state.current = {id: 'newer'}; resolveSaved({id: 'old'});`);
  await pending;
  assert.equal(subject.run('state.current.id'), 'newer');
});

test('manual brief changes cannot be silently replaced by a chat submission', async () => {
  const subject = sandbox(); usableReport(subject);
  subject.run(`state.formDirty = true; $('messageInput').value = '请继续';
    var requests = 0; var panel = ''; var notice = '';
    api = async () => { requests++; }; showPanel = name => { panel = name; };
    showNotice = message => { notice = message; };`);
  await subject.run(`sendMessage({preventDefault() {}})`);
  assert.equal(subject.run('requests'), 0);
  assert.equal(subject.run('panel'), 'brief');
  assert.match(subject.run('notice'), /未确认/);
  assert.equal(subject.element('messageInput').value, '请继续');
});

test('unavailable job status is not presented as a stopped server task', async () => {
  const subject = sandbox();
  subject.run(`state.epoch = 1; state.run = {id: 'job-A', status: 'running'};
    renderJob = () => {}; showNotice = () => {};
    api = async () => { const error = new Error('status unavailable'); error.status = 403; throw error; };`);
  await subject.run(`pollRun('job-A', 1)`);
  assert.equal(subject.run('state.run.status'), 'running', 'keep the last observed server state');
  assert.equal(subject.run('state.run.connection_lost'), true);
  assert.equal(subject.run('isBusy()'), true, 'do not unlock duplicate submission while outcome is unknown');
});

test('historical report follow-up explicitly names the switch to current', () => {
  const subject = sandbox(); usableReport(subject);
  subject.run(`state.report = {status: 'completed', sources: [{}]}; updateReportAction();`);
  assert.equal(subject.element('askReport').disabled, false);
  assert.match(subject.element('askReport').textContent, /切回当前报告/);
  subject.run(`state.current.result.status = 'call_limit'; updateReportAction();`);
  assert.equal(subject.element('askReport').disabled, true);
});

test('composer placeholder follows externally changed intent and report eligibility', () => {
  const subject = sandbox(); usableReport(subject);
  subject.run(`state.nextIntent = 'intake'; renderIntentControls();`);
  assert.match(subject.element('messageInput').placeholder, /补充或修改/);
  // The report action changes intent directly, rather than through a quick chip.
  subject.run(`state.report = state.current.result; state.nextIntent = 'followup'; renderIntentControls();`);
  assert.match(subject.element('messageInput').placeholder, /针对当前报告继续问/);
  subject.run(`state.formDirty = true; renderIntentControls();`);
  assert.equal(subject.run('state.nextIntent'), 'intake');
  assert.match(subject.element('messageInput').placeholder, /未确认的修改/);
});

test('out-of-order history responses cannot replace the newer list', async () => {
  const subject = sandbox();
  subject.run(`var resolvers = []; renderSessions = () => {};
    api = () => new Promise(resolve => resolvers.push(resolve));`);
  const first = subject.run('refreshSessions()');
  const second = subject.run('refreshSessions()');
  subject.run(`resolvers[1]({sessions: [{id: 'new'}]})`); await second;
  subject.run(`resolvers[0]({sessions: [{id: 'old'}]})`); await first;
  assert.equal(subject.run('state.sessions[0].id'), 'new');
});

test('source links reject executable URLs and embedded credentials', () => {
  const subject = sandbox();
  for (const value of ['javascript:alert(1)', 'data:text/html,test', 'file:///x', 'https://user:secret@example.org/', '/relative']) {
    assert.equal(subject.run(`safeUrl(${JSON.stringify(value)})`), null);
  }
  assert.equal(subject.run(`safeUrl('https://example.org/terms')`), 'https://example.org/terms');
  assert.doesNotMatch(originalCode, /\binnerHTML\b|\beval\s*\(/);
});

test('HTML identifiers and labelled tab/form targets agree with the script', () => {
  const html = fs.readFileSync(path.join(staticDirectory, 'index.html'), 'utf8');
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
  assert.equal(new Set(ids).size, ids.length, 'duplicate HTML identifier');
  const names = new Set(ids);
  for (const match of originalCode.matchAll(/\$\('([^']+)'\)/g)) assert.ok(names.has(match[1]), match[1]);
  for (const match of html.matchAll(/\b(?:for|aria-controls|aria-labelledby)="([^"]+)"/g)) {
    for (const name of match[1].split(/\s+/)) assert.ok(names.has(name), name);
  }
});

(async () => {
  for (const {name, action} of tests) {
    await action(); console.log('PASS ' + name);
  }
  console.log(`${tests.length} insurance UI state checks passed (no browser or API).`);
})().catch(error => { console.error(error); process.exitCode = 1; });
