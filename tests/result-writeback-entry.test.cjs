const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

class Element {
  constructor(tag) { this.tag=tag; this.children=[]; this.dataset={}; this.textContent=''; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children=items; }
  addEventListener() {}
  querySelectorAll() { return []; }
}
function setup(role='teacher', returned=null) {
  const main=new Element('main'); main.dataset={role,csrf:'csrf-test'};
  const ids={message:new Element('p'),results:new Element('section'),activities:new Element('ul'),
    'close-room':new Element('button')};
  if(returned) { ids['selected-activity']=new Element('span');ids['selected-activity'].dataset.selectedActivityId=returned; }
  let result={status:'settled',results:[]};
  const context=vm.createContext({document:{querySelector:s=>s==='main'?main:null,getElementById:id=>ids[id],
    createElement:tag=>new Element(tag),addEventListener(){}},
    localStorage:{getItem:()=>null,setItem(){},removeItem(){}},window:{addEventListener(){}},setInterval(){},
    fetch:async path=>({ok:true,headers:{get:()=> 'application/json'},json:async()=>path==='/teacher/courses'?{courses:[]}:result})});
  vm.runInContext(fs.readFileSync('src/guided_notes/static/classroom.js','utf8'),context);
  return {ids,context,setResult:r=>{result=r;}};
}

test('teacher form pins selected activity and CSRF rather than recent activity',async()=>{
  const {ids,context}=setup();
  await vm.runInContext('selectedResult={id:"original",title:"Original",context:selection,currentActivity:activeId}; refreshResult()',context);
  const form=ids.results.children.find(x=>x.tag==='form');
  assert.equal(form.method,'post');assert.equal(form.action,'/teacher/notes/export-previews');
  assert.equal(form.children.find(x=>x.name==='activity_id').value,'original');
  assert.equal(form.children.find(x=>x.name==='csrf_token').value,'csrf-test');
});

test('pending result keeps selected activity but disables preview action',async()=>{
  const {ids,context,setResult}=setup();setResult({status:'pending'});
  await vm.runInContext('selectedResult={id:"original",context:selection,currentActivity:activeId}; refreshResult()',context);
  assert.equal(ids.results.children.find(x=>x.tag==='form').children.at(-1).disabled,true);
});

test('students do not receive teacher export action',async()=>{
  const {ids,context}=setup('student');
  await vm.runInContext('selectedResult={id:"original",context:selection,currentActivity:activeId}; refreshResult()',context);
  assert.equal(ids.results.children.some(x=>x.tag==='form'),false);
});

test('return selection restores original history once and preserves manual selections',async()=>{
  const {context,setResult}=setup('teacher','original');
  setResult({activities:[{activity_id:'original',title:'Original',phase:'CLOSED'},
    {activity_id:'latest',title:'Latest',phase:'CLOSED'}]});
  await vm.runInContext('room="room"; activityList("room")',context);
  assert.equal(vm.runInContext('selectedResult.id',context),'original');
  vm.runInContext('selectedResult.id="latest"',context);
  await vm.runInContext('activityList("room")',context);
  assert.equal(vm.runInContext('selectedResult.id',context),'latest');
});

test('late history result cannot replace the new export form',async()=>{
  const {ids,context}=setup();
  let release;
  const original=context.fetch;
  context.fetch=async(path,options)=>path==='/activities/old/results'
    ? {ok:true,headers:{get:()=> 'application/json'},json:()=>new Promise(resolve=>{release=()=>resolve({status:'settled',results:[]});})}
    : original(path,options);
  const pending=vm.runInContext('selectedResult={id:"old",context:selection,currentActivity:activeId}; refreshResult()',context);
  await new Promise(setImmediate);
  await vm.runInContext('selectedResult={id:"new",context:selection,currentActivity:activeId}; refreshResult()',context);
  release();await pending;
  assert.equal(ids.results.children.find(x=>x.tag==='form').children.find(x=>x.name==='activity_id').value,'new');
});
