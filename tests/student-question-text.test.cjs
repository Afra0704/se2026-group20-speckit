const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

class Element {
  constructor(tag='div') { this.tag=tag; this.children=[]; this.dataset={}; this.listeners={}; this.value=''; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children=nodes; }
  hasChildNodes() { return this.children.length>0; }
  addEventListener(name, fn) { this.listeners[name]=fn; }
  querySelectorAll(selector) {
    const tags=selector.split(',').map(s=>s.trim().split(' ').at(-1));
    return this.children.filter(n=>n instanceof Element).flatMap(n=>[...(tags.includes(n.tag)?[n]:[]),...n.querySelectorAll(selector)]);
  }
}
function ui(file) {
  const ids=Object.fromEntries(['state','activity-state','questions','results','message'].map(id=>[id,new Element()]));
  const main=new Element();main.dataset={role:'student'};
  const context=vm.createContext({document:{querySelector:()=>main,getElementById:id=>ids[id],createElement:tag=>new Element(tag),addEventListener(){}},
    localStorage:{getItem:()=>null,setItem(){},removeItem(){}},window:{addEventListener(){}},setInterval(){},fetch:async()=>({ok:true,json:async()=>({})})});
  vm.runInContext(fs.readFileSync(`src/guided_notes/static/${file}.js`,'utf8'),context);
  return {ids,context};
}
for(const file of ['classroom','activity-sync']) {
  test(`${file}: safe full text, one form per question, identity and phase preservation`,()=>{
    const {ids,context}=ui(file);
    const prompts=['  中文\n<script>alert(1)</script> Ω🙂  ','長'.repeat(5000)];
    const activity={activity_id:'a',phase:'PREPARING',phase_version:0,question_text_status:'complete',questions:[
      {question_id:'q',display_number:'1',kind:'question_set',items:prompts.map((prompt_text,n)=>({item_id:`i${n}`,subitem_label:`(${n+1})`,prompt_text}))}]};
    context.activity=activity;
    const render=()=>vm.runInContext(file==='classroom'?'showQuestions(activity,true)':'render(activity)',context);
    if(file==='activity-sync') vm.runInContext('setActivity(activity)',context);
    render();
    assert.deepEqual(ids.questions.querySelectorAll('p').map(n=>n.textContent),prompts);
    assert.equal(ids.questions.querySelectorAll('form').length,1);
    assert.deepEqual(ids.questions.querySelectorAll('input').map(n=>n.name),['i0','i1']);
    assert.ok(ids.questions.querySelectorAll('input, button').every(n=>n.disabled));
    const input=ids.questions.querySelectorAll('input')[0];input.value='原答案';
    activity.phase='LIVE';activity.phase_version=1;render();
    assert.equal(ids.questions.querySelectorAll('input')[0],input);
    assert.ok(ids.questions.querySelectorAll('input, button').every(n=>!n.disabled));
    activity.activity_id='b';activity.question_text_status='unavailable';activity.questions[0].items.forEach(i=>i.prompt_text=null);
    if(file==='activity-sync') vm.runInContext('setActivity(activity)',context);
    render();
    assert.notEqual(ids.questions.querySelectorAll('input')[0],input);
    assert.match(ids.questions.querySelectorAll('p')[0].textContent,/完整版本/);
    assert.ok(!fs.readFileSync(`src/guided_notes/static/${file}.js`,'utf8').includes('innerHTML'));
  });
}
test('full text stylesheet wraps without clipping',()=>{
  const css=fs.readFileSync('src/guided_notes/static/question-text.css','utf8');
  assert.match(css,/white-space:\s*pre-wrap/);assert.match(css,/overflow-wrap:\s*anywhere/);
  assert.doesNotMatch(css,/max-height|line-clamp|overflow:\s*hidden/);
});
