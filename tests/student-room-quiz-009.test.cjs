const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

class Element{
 constructor(tag='div'){this.tag=tag;this.children=[];this.hidden=false;this.textContent='';this.dataset={};}
 append(...items){this.children.push(...items);}
 replaceChildren(...items){this.children=items;}
 querySelectorAll(selector){const tags=selector.split(',');return this.children.filter(x=>tags.includes(x.tag)).concat(this.children.flatMap(x=>x.querySelectorAll?.(selector)||[]));}
}

async function classroom(){
 const ids=Object.fromEntries(['room-content','questions','results','state','message','closed-notice','access-notice','activity-title','recover'].map(id=>[id,new Element()]));
 const main=new Element();main.dataset={classroomId:'A',csrf:'synthetic'};
 const storage=new Map(),requests=[],timers=[];let sequence=0,failPoll=false;
 const context=vm.createContext({AbortController,
  crypto:{randomUUID:()=>`00000000-0000-4000-8000-${String(++sequence).padStart(12,'0')}`},
  sessionStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},
  FormData:class{constructor(form){this.form=form;}*[Symbol.iterator](){for(const input of this.form.querySelectorAll('input'))yield[input.name,input.value||'original answer'];}},
  document:{hidden:false,querySelector:()=>main,getElementById:id=>ids[id],createElement:tag=>new Element(tag),addEventListener(){}},
  window:{addEventListener(){}},setInterval:f=>timers.push(f),
  fetch:async(path,options)=>{
   if(path.endsWith('/submissions'))return new Promise((resolve,reject)=>requests.push({key:options.headers['Idempotency-Key'],body:options.body,resolve:status=>resolve({ok:status===201,status,json:async()=>status===201?{status:'accepted'}:{error:'INVALID_PHASE'}}),reject}));
   if(path.endsWith('/state')){
    if(failPoll){failPoll=false;throw new TypeError('temporary polling failure');}
    return {ok:true,status:200,json:async()=>({classroom_id:'A',classroom_state:'OPEN',state_version:1,group_name:'A',activity:{activity_id:'quiz',phase:'LIVE',group_id:1,questions:[{question_id:'q',display_number:'1',items:[{item_id:'i',prompt_text:'Question'}]}]}})};
   }
   return {ok:true,status:200,json:async()=>({activities:[]})};
  }
 });
 for(const file of ['quiz-submission.js','student-room.js'])vm.runInContext(fs.readFileSync(`src/guided_notes/static/${file}`,'utf8'),context);
 const flush=async()=>{await new Promise(setImmediate);await new Promise(setImmediate);};
 await flush();
 return {ids,requests,storage,flush,form:()=>ids.questions.querySelectorAll('form')[0],failNextPoll(){failPoll=true;},async tick(){timers[0]();await flush();}};
}

for(const oldStatus of [201,409])test(`009 polling recovery keeps the newer retry when old ${oldStatus} arrives`,async()=>{
 const x=await classroom(),event={preventDefault(){}};
 const oldForm=x.form(),first=oldForm.onsubmit(event);await x.flush();
 x.failNextPoll();await x.tick();assert.equal(x.ids.questions.children.length,0);
 await x.tick();const newForm=x.form();assert.notEqual(newForm,oldForm);
 const second=newForm.onsubmit(event);await x.flush();
 assert.equal(x.requests.length,2);assert.notEqual(x.requests[0].key,x.requests[1].key);
 x.requests[0].resolve(oldStatus);await first;
 assert.notEqual(x.ids.message.textContent,'答案已受理','detached old form must not report success for the new form');
 x.requests[1].reject(new TypeError('new response lost'));await second;
 assert.equal(x.storage.size,1);assert.equal([...x.storage.values()].map(JSON.parse)[0].key,x.requests[1].key);
 const retryButton=newForm.children.at(-1);assert.equal(retryButton.hidden,false);
 const retry=retryButton.onclick();await x.flush();
 assert.equal(x.requests[2].key,x.requests[1].key);assert.equal(x.requests[2].body,x.requests[1].body);
 x.requests[2].resolve(201);await retry;
 assert.equal(x.storage.size,0);assert.equal(x.ids.message.textContent,'答案已受理');
});
