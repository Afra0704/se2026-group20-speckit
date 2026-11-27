const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

async function screen(beaconAccepted, holdFirstHeartbeat = false) {
  const listeners = {}, docListeners = {}, timers = [], calls = [];
  const beacons = [];
  const element = () => ({hidden: false, textContent: '', children: [],
    replaceChildren(...children) { this.children = children; },
    append(...children) { this.children.push(...children); }, querySelectorAll: () => []});
  const nodes = Object.fromEntries(['room-content', 'state', 'message', 'questions', 'results',
    'access-notice', 'closed-notice', 'recover', 'activity-title'].map(id => [id, element()]));
  const document = {hidden: false, querySelector: () => ({dataset: {classroomId: 'room', csrf: 'csrf'}}),
    getElementById: id => nodes[id], createElement: element,
    addEventListener: (event, handler) => { docListeners[event] = handler; }};
  let nonce = 0;
  let firstHeartbeat = true, releaseHeartbeat;
  const context = {document, AbortController, Uint8Array, URLSearchParams,
    crypto: {getRandomValues(bytes) { bytes.fill(++nonce); return bytes; }},
    window: {addEventListener: (event, handler) => { listeners[event] = handler; }},
    setInterval: (handler, milliseconds) => timers.push({handler, milliseconds}),
    async fetch(path, options) {
      calls.push({path, options});
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
  return {calls, beacons, listeners, docListeners, document, flush,
    releaseHeartbeat: () => releaseHeartbeat(),
    heartbeat: () => timers.filter(timer => timer.milliseconds === 1000).at(-1).handler()};
}

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
