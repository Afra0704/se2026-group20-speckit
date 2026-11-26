const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
function scope(){
 const ctx=vm.createContext({});
 vm.runInContext(fs.readFileSync('src/guided_notes/static/student-room.js','utf8'),ctx);
 return ctx.StudentRoomState('A');
}
test('closed terminal rejects even an authorized old snapshot arriving late',()=>{
 const s=scope(), first=s.generation;
 assert.equal(s.accept({classroom_id:'A',classroom_state:'OPEN',state_version:1},first),true);
 assert.equal(s.accept({classroom_id:'A',classroom_state:'CLOSED',state_version:2},first),true);
 assert.equal(s.closed,true);
 assert.equal(s.accept({classroom_id:'A',classroom_state:'OPEN',state_version:1},first),false);
 assert.equal(s.accept({classroom_id:'B',classroom_state:'OPEN',state_version:99},s.generation),false);
});
test('returning to an old page invalidates earlier requests without changing its room',()=>{
 const s=scope(), first=s.generation;
 s.invalidate();
 assert.equal(s.accept({classroom_id:'A',classroom_state:'OPEN',state_version:1},first),false);
 assert.equal(s.accept({classroom_id:'A',classroom_state:'OPEN',state_version:2},s.generation),true);
 assert.equal(s.accept({classroom_id:'A',classroom_state:'OPEN',state_version:1},s.generation),false);
});

class Element {
 constructor(tag='div'){this.tag=tag;this.children=[];this.hidden=false;this.ownText='';this.dataset={};}
 get textContent(){return this.ownText+this.children.map(child=>child.textContent).join('');}
 set textContent(value){this.ownText=value;this.children=[];}
 append(...items){this.children.push(...items);}
 replaceChildren(...items){this.children=items;}
 querySelectorAll(selector){const tags=selector.split(',');return this.children.filter(x=>tags.includes(x.tag)).concat(this.children.flatMap(x=>x.querySelectorAll?.(selector)||[]));}
}
async function dom(initialPhase='CLOSED'){
 const ids=Object.fromEntries(['room-content','questions','results','state','message','closed-notice','access-notice','activity-title','recover'].map(x=>[x,new Element()]));
 const main=new Element();main.dataset={classroomId:'A',csrf:'test'};
 let closed=false,delay=false,fail=false,release,currentGroup=1,resultStatus='settled',activityId='quiz',phase=initialPhase;
 const timers=[],listeners={};
 const ctx=vm.createContext({document:{hidden:false,querySelector:()=>main,getElementById:x=>ids[x],createElement:x=>new Element(x),addEventListener:(e,f)=>listeners[e]=f},
 window:{addEventListener:(e,f)=>listeners[e]=f},AbortController,setInterval:f=>timers.push(f),
 fetch:async path=>{
  let data;
  if(path.endsWith('/state'))data={classroom_id:'A',classroom_state:closed?'CLOSED':'OPEN',state_version:closed?2:1,group_name:'A',activity:{activity_id:activityId,phase,group_id:currentGroup,questions:[]}};
  else if(path.startsWith('/classrooms/'))data={activities:[{activity_id:'quiz',title:'Original result'},{activity_id:'other',title:'Other result'}]};
  else {
   const original=path.includes('/quiz/');
   if(delay&&original){await new Promise(r=>release=r);if(fail)throw new Error('Network failure');}
   data={status:resultStatus,results:[{question_id:'q',winner_name:'A',winner_answer:original?'original answer':'other answer',own:{answer:'own answer',rank:1}}]};
  }
  return {ok:true,status:200,json:async()=>data};
 }});
 vm.runInContext(fs.readFileSync('src/guided_notes/static/student-room.js','utf8'),ctx);
 const flush=async()=>{await new Promise(setImmediate);await new Promise(setImmediate);};
 await flush();
 return {ids,flush,async tick(){timers[0]();await flush();},close(){closed=true;},endActivity(){phase='CLOSED';},next(){activityId='next';phase='PREPARING';},pending(){resultStatus='pending';},changeGroup(){currentGroup=2;},delay({reject=false}={}){delay=true;fail=reject;},release(){release();},listeners};
}
test('a selected result remains visible across ordinary classroom polling',async()=>{
 const x=await dom();await x.ids.results.children[0].onclick();
 assert.ok(x.ids.results.children.some(e=>e.textContent.includes('original answer')));
 await x.tick();
 assert.ok(x.ids.results.children.some(e=>e.textContent.includes('original answer')));
});
test('late result response cannot restore content after classroom closure',async()=>{
 const x=await dom();x.delay();const pending=x.ids.results.children[0].onclick();await x.flush();
 x.close();await x.tick();
 assert.equal(x.ids['closed-notice'].hidden,false);assert.equal(x.ids['room-content'].hidden,true);
 x.release();await pending;
 assert.equal(x.ids.results.children.length,0);assert.equal(x.ids.questions.children.length,0);
});
test('another tab changing the group never transfers the old page or its draft',async()=>{
 const x=await dom();x.changeGroup();await x.tick();
 assert.equal(x.ids['room-content'].hidden,true);
 assert.equal(x.ids['access-notice'].hidden,false);
 assert.equal(x.ids.questions.children.length,0);
});

test('automatic result polling does not block the classroom closing',async()=>{
 const x=await dom();
 x.pending();await x.ids.results.children[0].onclick();
 x.delay();await x.tick();
 x.close();await x.tick();
 assert.equal(x.ids.state.textContent,'課堂已結束');
 assert.equal(x.ids['room-content'].hidden,true);
 x.release();await x.flush();
 assert.equal(x.ids.results.children.length,0);
});
test('an obsolete result request failure leaves the new selection visible',async()=>{
 const x=await dom();
 x.delay({reject:true});const pending=x.ids.results.children[0].onclick();await x.flush();
 await x.ids.results.children[1].onclick();
 x.release();await pending;
 assert.equal(x.ids['room-content'].hidden,false);
 assert.ok(x.ids.results.children.some(e=>e.textContent.includes('other answer')));
});

test('ending the current activity opens results without a click and hides the answer area',async()=>{
 const x=await dom();
 assert.equal(x.ids.questions.hidden,true);
 assert.ok(x.ids.results.textContent.includes('original answer'));
});
test('a manually selected history result stays visible until the next activity',async()=>{
 const x=await dom();
 await x.ids.results.children[1].onclick();
 await x.tick();
 assert.ok(x.ids.results.textContent.includes('other answer'));
 await x.next();await x.tick();
 assert.equal(x.ids.questions.hidden,false);
 assert.equal(x.ids.results.textContent.includes('other answer'),false);
});

test('a late automatic result does not replace manually selected history',async()=>{
 const x=await dom('LIVE');
 x.delay();x.endActivity();await x.tick();
 await x.ids.results.children[1].onclick();
 x.release();await x.flush();
 assert.ok(x.ids.results.textContent.includes('other answer'));
 assert.equal(x.ids.results.textContent.includes('original answer'),false);
});
