const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

class Element{
 constructor(tag='div'){this.tag=tag;this.children=[];this.hidden=false;this.textContent='';this.dataset={};}
 setAttribute(name,value){(this.attributes??={})[name]=value;}
 removeAttribute(name){delete this.attributes?.[name];}
 focus(){this.focused=true;}
 addEventListener(name,fn){this['on'+name]=fn;}
 append(...items){this.children.push(...items);}
 replaceChildren(...items){this.children=items;}
 querySelectorAll(selector){const tags=selector.split(',');return this.children.filter(x=>tags.includes(x.tag)).concat(this.children.flatMap(x=>x.querySelectorAll?.(selector)||[]));}
}

async function classroom(questions=[{question_id:'q',display_number:'1',items:[{item_id:'i',prompt_text:'Question'}]}]){
 const ids=Object.fromEntries(['room-content','questions','results','state','message','closed-notice','access-notice','activity-title','recover'].map(id=>[id,new Element()]));
 const main=new Element();main.dataset={classroomId:'A',csrf:'synthetic'};
 const storage=new Map(),requests=[],timers=[];let sequence=0,failPoll=false;
 const context=vm.createContext({AbortController,
  crypto:{randomUUID:()=>`00000000-0000-4000-8000-${String(++sequence).padStart(12,'0')}`},
  sessionStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},
  FormData:class{constructor(form){this.form=form;}*[Symbol.iterator](){for(const input of this.form.querySelectorAll('input'))yield[input.name,input.value??'original answer'];}},
  document:{hidden:false,querySelector:()=>main,getElementById:id=>ids[id],createElement:tag=>new Element(tag),addEventListener(){}},
  window:{addEventListener(){}},setInterval:f=>timers.push(f),
  fetch:async(path,options)=>{
   if(path.endsWith('/submissions'))return new Promise((resolve,reject)=>requests.push({key:options.headers['Idempotency-Key'],body:options.body,resolve:(status,payload)=>resolve({ok:status===201,status,json:async()=>payload??(status===201?{status:'accepted'}:{error:'INVALID_PHASE'})}),reject}));
   if(path.endsWith('/state')){
    if(failPoll){failPoll=false;throw new TypeError('temporary polling failure');}
    return {ok:true,status:200,json:async()=>({classroom_id:'A',classroom_state:'OPEN',state_version:1,group_name:'A',activity:{activity_id:'quiz',phase:'LIVE',group_id:1,questions}})};
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
 assert.equal(x.storage.size,0);assert.equal(newForm.children.at(-2).textContent,'答案已受理');
});

test('blank Unicode input is marked inline without a request and corrected text remains unchanged',async()=>{
 const x=await classroom(),form=x.form(),input=form.querySelectorAll('input')[0];
 const event={preventDefault(){}};
 input.value='\u0085\u001c';
 await form.onsubmit(event);
 assert.equal(x.requests.length,0);
 assert.equal(input.attributes['aria-invalid'],'true');
 assert.ok(input.attributes['aria-describedby']);
 assert.equal(input.focused,true);
 input.value=' \ufeff ';
 input.oninput();
 assert.equal(input.attributes['aria-invalid'],undefined);
 const sending=form.onsubmit(event);
 assert.equal(form.children.at(-2).textContent,'送出中');
 assert.equal(JSON.parse(x.requests[0].body).items[0].answer_text,' \ufeff ');
 x.requests[0].resolve(201);
 await sending;
 assert.equal(form.children.at(-2).textContent,'答案已受理');
 assert.equal(x.ids.message.textContent,'');
});

test('a missing subitem does not affect other inputs or the next question',async()=>{
 const x=await classroom([
  {question_id:'first',display_number:'1',items:[{item_id:'a'},{item_id:'b'}]},
  {question_id:'second',display_number:'2',items:[{item_id:'c'}]},
 ]);
 const [first,second]=x.ids.questions.querySelectorAll('form');
 const [a,b]=first.querySelectorAll('input');
 const event={preventDefault(){}};
 a.value='保留我';
 b.value='';
 await first.onsubmit(event);
 assert.equal(x.requests.length,0);
 assert.equal(a.value,'保留我');
 assert.equal(a.attributes['aria-invalid'],undefined);
 assert.equal(b.attributes['aria-invalid'],'true');
 assert.equal(b.focused,true);
 assert.equal(second.children.at(-2).textContent,'');
 const sent=second.onsubmit(event);
 x.requests[0].resolve(201);
 await sent;
 await x.tick();
 assert.equal(second.children.at(-2).textContent,'答案已受理');
 assert.equal(first.children.at(-2).textContent,'請填寫標示的答案欄位。');
});

test('a malformed success response remains unknown and keeps the original request',async()=>{
 const x=await classroom(),form=x.form();
 const sending=form.onsubmit({preventDefault(){}});
 x.requests[0].resolve(201,{status:'unexpected'});
 await sending;
 assert.match(form.children.at(-2).textContent,/結果未確認/);
 const retry=form.children.at(-1).onclick();
 assert.equal(x.requests[0].key,x.requests[1].key);
 assert.equal(x.requests[0].body,x.requests[1].body);
 x.requests[1].resolve(201);
 await retry;
 assert.equal(form.children.at(-2).textContent,'答案已受理');
});
