const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(process.env.PREVIEW_SOURCE || 'src/guided_notes/static/classroom.js', 'utf8');

class Element {
  constructor(tag = 'div') {
    this.tag = tag; this.children = []; this.dataset = {}; this.listeners = {};
    this.disabled = false; this.value = ''; this.textContent = '';
  }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; }
  addEventListener(event, callback) { this.listeners[event] = callback; }
  querySelectorAll(selector) {
    const tags = selector.split(',').map(v => v.trim().split(' ').at(-1));
    const result = [];
    for (const child of this.children) {
      if (!(child instanceof Element)) continue;
      if (tags.includes(child.tag)) result.push(child);
      result.push(...child.querySelectorAll(selector));
    }
    return result;
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}

async function setup(role = 'student') {
  const ids = Object.fromEntries(['state','message','questions','recover','results','courses','activities',
    'close-room','create-activity','catalogs'].map(id => [id, new Element()]));
  ids['create-activity'].append(new Element('button'));
  ids.catalogs.value = JSON.stringify(['catalog', 1]);
  const main = new Element(); main.dataset = {role, csrf:'test'};
  main.querySelectorAll = selector => [ids.questions, ids.activities].flatMap(n => n.querySelectorAll(selector));
  let data, failState = false, failHistory = false, delay, release, createError = false;
  let activities = [];
  const responses = [];
  const context = vm.createContext({
    document:{querySelector:s => s === 'main' ? main : null, getElementById:id => ids[id],
      createElement:tag => new Element(tag), addEventListener(){}},
    localStorage:{getItem:()=>null,setItem(){},removeItem(){}},
    window:{addEventListener(){},confirm:()=>true}, setInterval(){},
    FormData:class { *[Symbol.iterator]() { yield ['title','Lecture']; } },
    Option:function(text,value){this.text=text;this.value=value;},
    fetch:async (path, options) => {
      let body;
      if (path === '/teacher/courses') body = {courses:[]};
      else if (path.endsWith('/state')) {
        if (failState) throw new Error('offline');
        body = data;
        if (delay) { delay = false; await new Promise(resolve => release = resolve); }
      } else if (path.endsWith('/activities') && options.method === 'POST') {
        if (createError) return {ok:false, headers:{get:()=> 'application/json'}, json:async()=>({error:'ACTIVITY_IN_PROGRESS'})};
        activities = [{activity_id:'a',phase:'PREPARING',title:'Lecture'}];
        data = state('PREPARING', 2);
        body = {activity_id:'a',phase:'PREPARING'};
      } else if (path.endsWith('/activities')) {
        if (failHistory) throw new Error('history offline');
        body = {activities};
      } else if (path.endsWith('/results')) body={activities:[]};
      else { responses.push(path); body={}; }
      return {ok:true,headers:{get:()=> 'application/json'},json:async()=>body};
    }
  });
  vm.runInContext(source, context);
  await new Promise(setImmediate);
  vm.runInContext('setRoom("room")', context);
  return {ids, context, responses,
    async update(phase, version = 1, id = 'a') {
      data = state(phase, version, id);
      activities = phase ? [{activity_id:id,phase,title:data.activity.title}] : [];
      await vm.runInContext('refresh()',context);
    },
    async offline(value) { failState=value; await vm.runInContext('refresh()',context); },
    async historyOffline(value) { failHistory=value; await vm.runInContext('historyNeedsRefresh=true; refresh()',context); },
    createError(value) {createError=value;},
    delay() {delay=true;}, release() {release();}
  };
}
function state(phase, version=1, id='a') {
  return {classroom_id:'room',classroom_state:'OPEN',state_version:version,
    activity:phase ? {activity_id:id,phase,title:'<b>Lecture</b>',questions:[
      {question_id:'q1',display_number:'1',items:[{item_id:'i1',subitem_label:null}]},
      {question_id:'q2',display_number:'2',items:[{item_id:'i2',subitem_label:'(1)'},{item_id:'i3',subitem_label:'(2)'}]}
    ]} : null};
}
const controls = ui => ui.ids.questions.querySelectorAll('input, button');

test('PREPARING renders all fields disabled; same id LIVE enables; CLOSED disables', async () => {
  const ui = await setup();
  await ui.update('PREPARING');
  assert.equal(ui.ids.questions.children.length,2);
  assert.equal(ui.ids.questions.querySelectorAll('input').length,3);
  assert.ok(controls(ui).every(n=>n.disabled));
  assert.match(ui.ids.state.textContent, /<b>Lecture<\/b>.*尚未開放搶答/);
  assert.equal(ui.ids.questions.querySelectorAll('label')[1].children[0], '(1)');
  const input=ui.ids.questions.querySelector('input');
  await ui.update('LIVE',2);
  assert.equal(ui.ids.questions.querySelector('input'),input);
  assert.ok(controls(ui).every(n=>!n.disabled));
  await ui.update('CLOSED',3);
  assert.ok(controls(ui).every(n=>n.disabled));
  await ui.update('LIVE',2);
  assert.ok(controls(ui).every(n=>n.disabled));
});

test('offline disables input, recovery reenables, new activity clears old values', async()=>{
  const ui=await setup(); await ui.update('LIVE');
  ui.ids.questions.querySelector('input').value='old answer';
  await ui.offline(true); assert.ok(controls(ui).every(n=>n.disabled));
  await ui.offline(false); assert.ok(controls(ui).every(n=>!n.disabled));
  await ui.update('PREPARING',2,'b');
  assert.equal(ui.ids.questions.querySelector('input').value,'');
  assert.ok(controls(ui).every(n=>n.disabled));
});

test('teacher cannot create during preparation/live; can finish preparation; history failure recovers', async()=>{
  const ui=await setup('teacher'); const button=ui.ids['create-activity'].querySelector('button');
  assert.equal(button.disabled,true);
  await ui.update(null); assert.equal(button.disabled,false);
  await ui.update('PREPARING',2); assert.equal(button.disabled,true);
  assert.deepEqual(ui.ids.activities.querySelectorAll('button').map(n=>n.textContent),['開啟搶答','結束活動']);
  await ui.update('LIVE',3); assert.equal(button.disabled,true);
  await ui.update('CLOSED',4); assert.equal(button.disabled,false);
  await ui.historyOffline(true); assert.equal(button.disabled,true);
  await ui.historyOffline(false); assert.equal(button.disabled,false);
});

test('create form finally preserves business disabled state after success or conflict', async()=>{
  for (const conflict of [false,true]) {
    const ui=await setup('teacher'); await ui.update(null);
    ui.createError(conflict);
    await ui.ids['create-activity'].listeners.submit({preventDefault(){}});
    assert.equal(ui.ids['create-activity'].querySelector('button').disabled,true);
    if(conflict) assert.match(ui.ids.message.textContent,/先結束目前活動/);
  }
});

test('late state from former classroom is ignored', async()=>{
  const ui=await setup(); await ui.update('LIVE');
  ui.delay(); const pending=ui.update('LIVE',2);
  await new Promise(setImmediate);
  vm.runInContext('setRoom("other-room")',ui.context);
  ui.release(); await pending;
  assert.equal(ui.ids.questions.children.length,0);
});
