const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('src/guided_notes/static/classroom.js', 'utf8');
const implementation = source.slice(source.indexOf('async function activityList('), source.indexOf('function addResultButton('));

class Element {
  constructor() {this.textContent='';this.children=[];}
  append(value) {this.children.push(value);}
  replaceChildren() {this.children=[];}
}
function context(activities, delay) {
  const list=new Element();
  const sandbox={historyRequest:0,selection:1,version:1,room:'room',historyNeedsRefresh:false,
    returnSelectionPending:false,role:'teacher',
    main:{dataset:{}},document:{createElement:()=>new Element()},url:encodeURIComponent,
    updateCreateAvailability(){},addResultButton(){},byId:id=>id==='activities'?list:{disabled:true},
    api:async()=>{if(delay) await delay;return {activities};}};
  vm.createContext(sandbox);vm.runInContext(implementation,sandbox);
  return {sandbox,list};
}
const activity = time_display => ({activity_id:'a',title:'<img onerror=bad>',phase:'CLOSED',
  created_at:'raw-must-not-be-parsed',time_display});
const metadata={version:1,timezone:'Asia/Taipei',utc_offset:'+08:00',
  created_at:{label:'建立',status:'known',text:'2026-11-27 11:00'},
  started_at:{label:'開始',status:'skipped_start',text:'未開始即結束'},
  closed_at:{label:'結束',status:'known',text:'2026-11-27 11:04'}};

test('renders three server event texts without reparsing or rounding',async()=>{
  const {sandbox,list}=context([activity(metadata)]);
  sandbox.Date=class{constructor(){throw Error('must not parse dates');}};
  await vm.runInContext('activityList("room")',sandbox);
  const text=list.children[0].textContent;
  for(const expected of ['建立：2026-11-27 11:00','開始：未開始即結束','結束：2026-11-27 11:04']) assert.ok(text.includes(expected),text);
  assert.ok(text.includes('<img onerror=bad>'));
  assert.equal(list.children[0].innerHTML,undefined);
  assert.ok(!text.includes('raw-must-not-be-parsed'));
});
test('missing or unknown metadata never falls back to raw time',async()=>{
  for(const value of [undefined,{...metadata,version:2}]) {
    const {sandbox,list}=context([activity(value)]);
    await vm.runInContext('activityList("room")',sandbox);
    assert.match(list.children[0].textContent,/時間資料尚未提供/);
    assert.ok(!list.children[0].textContent.includes('raw-must-not-be-parsed'));
  }
});
test('late history cannot overwrite a changed classroom',async()=>{
  let release;const delay=new Promise(resolve=>release=resolve);
  const {sandbox,list}=context([activity(metadata)],delay);
  const pending=vm.runInContext('activityList("room")',sandbox);
  sandbox.room='other';sandbox.selection++;release();await pending;
  assert.equal(list.children.length,0);
});
