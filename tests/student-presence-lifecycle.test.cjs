const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

async function screen(beaconAccepted, holdFirstHeartbeat = false, tab = null) {
  const listeners = {}, docListeners = {}, timers = [], calls = [];
  const beacons = [];
  const element = () => ({hidden: false, textContent: '', children: [],
    replaceChildren(...children) { this.children = children; },
    append(...children) { this.children.push(...children); }, querySelectorAll: () => []});
  const nodes = Object.fromEntries(['room-content', 'state', 'message', 'questions', 'results',
    'access-notice', 'closed-notice', 'recover', 'rejoin', 'activity-title'].map(id => [id, element()]));
  const dataset = {classroomId: 'room', csrf: 'csrf'};
  if (tab) dataset.pageProtocol = '1';
  const document = {hidden: false, querySelector: () => ({dataset}),
    getElementById: id => nodes[id], createElement: element,
    addEventListener: (event, handler) => { docListeners[event] = handler; }};
  let nonce = 0;
  let firstHeartbeat = true, releaseHeartbeat;
  let accessCount = 0;
  const saved = new Map(tab ? [['classroom-tab:room', JSON.stringify(tab.stored)]] : []);
  if (tab?.otherRoomClosed) saved.set('classroom-tab:other-room', JSON.stringify({closed: true}));
  const assigned = [], prompts = [];
  const context = {document, AbortController, Uint8Array, URLSearchParams,
    crypto: {getRandomValues(bytes) { bytes.fill(++nonce); return bytes; }},
    window: {addEventListener: (event, handler) => { listeners[event] = handler; },
      confirm: message => {prompts.push(message); return tab.confirm;},
      location: {assign: path => assigned.push(path)}},
    performance: {getEntriesByType: () => [{type: tab?.navigation}]},
    QuizSubmission: {hasPending: () => !!tab?.pending, clearScope: () => { tab.pending = false; }},
    sessionStorage: {getItem: key => saved.get(key), setItem: (key, value) => saved.set(key, value),
      removeItem: key => saved.delete(key)},
    setInterval: (handler, milliseconds) => timers.push({handler, milliseconds}),
    async fetch(path, options) {
      calls.push({path, options});
      if (path.endsWith('/tab-access')) {
        const count = ++accessCount;
        if (tab.loseResponse && count === 1) throw new Error('lost response');
        const body = JSON.parse(options.body);
        return {ok: true, status: 200, json: async () => ({
          group_id: 1, resume_id: 'resume-'+count, page_token: 'token-'+count,
          expires_at: Date.now()/1000+900, continued_operation_scope: !!body.handoff_id,
        })};
      }
      if (path.endsWith('/revoke')) return {ok: true, status: 204};
      if (path.endsWith('/state') && tab?.closed) {
        return {ok: true, status: 200, json: async () => ({
          classroom_id: 'room', classroom_state: 'CLOSED', state_version: 2,
        })};
      }
      if (path.endsWith('/presence') && holdFirstHeartbeat && firstHeartbeat) {
        firstHeartbeat = false;
        await new Promise(resolve => { releaseHeartbeat = resolve; });
      }
      if (path.endsWith('/presence') || path.endsWith('/presence/leave')) return {ok: true, status: 204};
      return {ok: true, status: 200, json: async () => path.endsWith('/state')
        ? {classroom_id: 'room', classroom_state: 'OPEN', state_version: 1, activity: null}
        : {activities: []}};
    },
  };
  if (beaconAccepted !== undefined) context.navigator = {
    sendBeacon(path, body) { beacons.push({path, body}); return beaconAccepted; },
  };
  vm.runInNewContext(fs.readFileSync('src/guided_notes/static/student-room.js', 'utf8'), context);
  const flush = () => new Promise(setImmediate);
  await flush();
  return {calls, beacons, listeners, docListeners, document, flush, saved, nodes, assigned, prompts,
    poll: () => timers[0].handler(),
    releaseHeartbeat: () => releaseHeartbeat(),
    heartbeat: () => timers.filter(timer => timer.milliseconds === 1000).at(-1).handler()};
}

test('a duplicate ignores a copied handoff and waits for its own credential before reading', async () => {
  const page = await screen(true, false, {
    stored: {resume: 'original', scope: 'scope-of-original', handoff: 'original-handoff'},
    navigation: 'navigate',
  });
  const activation = page.calls.find(call => call.path.endsWith('/tab-access'));
  const data = JSON.parse(activation.options.body);
  assert.equal(data.resume_id, 'original');
  assert.equal(data.handoff_id, undefined);
  assert.equal(JSON.parse(page.saved.get('classroom-tab:room')).scope, data.page_id);
  assert.equal(page.calls.find(call => call.path.endsWith('/state')).options.headers['X-Classroom-Tab'], 'token-1');
});

test('reload retries the same activation after a lost response and retains the verified scope', async () => {
  const page = await screen(true, false, {
    stored: {resume: 'original', scope: 'scope-of-original', handoff: 'original-handoff'},
    navigation: 'reload', loseResponse: true,
  });
  assert.equal(page.calls.some(call => call.path.endsWith('/state')), false);
  await page.poll();
  const attempts = page.calls.filter(call => call.path.endsWith('/tab-access'));
  assert.equal(attempts.length, 2);
  assert.equal(attempts[0].options.body, attempts[1].options.body);
  assert.equal(JSON.parse(attempts[1].options.body).handoff_id, 'original-handoff');
  assert.equal(JSON.parse(page.saved.get('classroom-tab:room')).scope, 'scope-of-original');
});

test('returning from the back-forward cache reauthorizes with a fresh document credential', async () => {
  const page = await screen(true, false, {stored: {resume: 'original'}});
  page.listeners.pagehide();
  const leave = page.beacons[0].body;
  assert.equal(leave.get('page_token'), 'token-1');
  page.listeners.pageshow();
  await page.flush();
  const activation = page.calls.filter(call => call.path.endsWith('/tab-access')).at(-1);
  assert.equal(JSON.parse(activation.options.body).handoff_id, leave.get('handoff_id'));
  assert.equal(page.calls.filter(call => call.path.endsWith('/state')).at(-1).options.headers['X-Classroom-Tab'], 'token-2');
});

test('closing the classroom clears this tab and stops further protected polling', async () => {
  const tab = {stored: {resume: 'original'}};
  const page = await screen(true, false, tab);
  tab.closed = true;
  await page.poll();
  await page.flush();
  assert.equal(page.nodes['closed-notice'].hidden, false);
  assert.deepEqual(JSON.parse(page.saved.get('classroom-tab:room')), {closed: true});
  const calls = page.calls.length;
  await page.poll();
  await page.heartbeat();
  assert.equal(page.calls.length, calls);
});

test('reload of an observed closed classroom keeps only a terminal marker and makes no protected requests', async () => {
  const original = await screen(true, false, {stored: {resume: 'original'}, closed: true});
  const stored = JSON.parse(original.saved.get('classroom-tab:room'));
  assert.deepEqual(stored, {closed: true});
  const reloaded = await screen(true, false, {stored, navigation: 'reload'});
  assert.equal(reloaded.nodes['closed-notice'].hidden, false);
  assert.equal(reloaded.nodes['access-notice'].hidden, true);
  assert.equal(reloaded.nodes['room-content'].hidden, true);
  assert.equal(reloaded.nodes.state.textContent, '課堂已結束');
  reloaded.listeners.pageshow();
  await reloaded.poll();
  await reloaded.heartbeat();
  assert.equal(reloaded.calls.length, 0);
});

test('terminal marker for another fixed classroom does not prevent this classroom from authenticating', async () => {
  const page = await screen(true, false, {stored: {resume: 'original'}, otherRoomClosed: true});
  assert.ok(page.calls.some(call => call.path.endsWith('/tab-access')));
  assert.ok(page.calls.some(call => call.path.endsWith('/state')));
  assert.deepEqual(JSON.parse(page.saved.get('classroom-tab:other-room')), {closed: true});
});

test('canceling rejoin keeps pending work and confirmation clears this tab after revocation', async () => {
  const tab = {stored: {resume: 'original'}, pending: true, confirm: false};
  const page = await screen(true, false, tab);
  await page.nodes.rejoin.onclick();
  assert.match(page.prompts[0], /伺服器可能已受理/);
  assert.equal(tab.pending, true);
  assert.equal(page.calls.some(call => call.path.endsWith('/revoke')), false);
  tab.confirm = true;
  await page.nodes.rejoin.onclick();
  assert.equal(tab.pending, false);
  assert.equal(page.saved.has('classroom-tab:room'), false);
  assert.deepEqual(page.assigned, ['/student']);
});

test('pagehide sends an independent keepalive departure and pageshow uses a new page identity', async () => {
  const page = await screen();
  const initial = JSON.parse(page.calls.find(call => call.path.endsWith('/presence')).options.body).page_id;
  page.listeners.pagehide();
  const leave = page.calls.find(call => call.path.endsWith('/presence/leave'));
  assert.equal(leave.options.keepalive, true);
  assert.equal(leave.options.signal, undefined);
  assert.equal(leave.options.headers['X-CSRF-Token'], 'csrf');
  assert.equal(JSON.parse(leave.options.body).page_id, initial);
  const count = page.calls.filter(call => call.path.endsWith('/presence')).length;
  await page.heartbeat();
  assert.equal(page.calls.filter(call => call.path.endsWith('/presence')).length, count);
  page.listeners.pageshow();
  await page.flush();
  const restored = page.calls.filter(call => call.path.endsWith('/presence')).at(-1);
  assert.notEqual(JSON.parse(restored.options.body).page_id, initial);
});

test('visibility change alone never sends departure and hidden pages still schedule heartbeats', async () => {
  const page = await screen();
  page.document.hidden = true;
  page.docListeners.visibilitychange();
  await page.flush();
  const before = page.calls.filter(call => call.path.endsWith('/presence')).length;
  await page.heartbeat();
  assert.equal(page.calls.filter(call => call.path.endsWith('/presence')).length, before + 1);
  assert.equal(page.calls.some(call => call.path.endsWith('/presence/leave')), false);
});

test('pagehide prefers a CSRF-protected Beacon over an unload fetch', async () => {
  const page = await screen(true);
  page.listeners.pagehide();
  const leave = page.beacons.find(call => call.path.endsWith('/presence/leave'));
  assert.ok(leave);
  assert.equal(leave.body.get('csrf_token'), 'csrf');
  assert.ok(leave.body.get('page_id'));
  assert.equal(page.calls.some(call => call.path.endsWith('/presence/leave')), false);
});

test('a rejected Beacon falls back to independent keepalive fetch', async () => {
  const page = await screen(false);
  page.listeners.pagehide();
  assert.equal(page.beacons.length, 1);
  assert.equal(page.calls.find(call => call.path.endsWith('/presence/leave')).options.keepalive, true);
});

test('background pages use Beacon heartbeats without reporting departure', async () => {
  const page = await screen(true);
  page.document.hidden = true;
  page.docListeners.visibilitychange();
  await page.flush();
  await page.heartbeat();
  assert.ok(page.beacons.length >= 1);
  assert.ok(page.beacons.every(call => call.path.endsWith('/presence')));
  assert.ok(page.beacons.every(call => call.body.get('csrf_token') === 'csrf'));
  assert.equal(page.calls.some(call => call.path.endsWith('/presence/leave')), false);
});

test('online sends presence immediately even when the prior generation heartbeat is stuck', async () => {
  const page = await screen(undefined, true);
  assert.equal(page.calls.filter(call => call.path.endsWith('/presence')).length, 1);
  page.listeners.online();
  await page.flush();
  assert.equal(page.calls.filter(call => call.path.endsWith('/presence')).length, 2);
  page.releaseHeartbeat();
  await page.flush();
  await page.heartbeat();
  assert.equal(page.calls.filter(call => call.path.endsWith('/presence')).length, 3);
});
