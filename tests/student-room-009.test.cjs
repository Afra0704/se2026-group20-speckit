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
 constructor(tag='div'){this.tag=tag;this.children=[];this.hidden=false;this.textContent='';this.dataset={};}
 append(...items){this.children.push(...items);}
 replaceChildren(...items){this.children=items;}
 querySelectorAll(selector){const tags=selector.split(',');return this.children.filter(x=>tags.includes(x.tag)).concat(this.children.flatMap(x=>x.querySelectorAll?.(selector)||[]));}
}
async function dom(){
 const ids=Object.fromEntries(['room-content','questions','results','state','message','closed-notice','access-notice','activity-title','recover'].map(x=>[x,new Element()]));
 const main=new Element();main.dataset={classroomId:'A',csrf:'test'};
 let closed=false,delay=false,release,currentGroup=1;
 const timers=[],listeners={};
 const ctx=vm.createContext({document:{hidden:false,querySelector:()=>main,getElementById:x=>ids[x],createElement:x=>new Element(x),addEventListener:(e,f)=>listeners[e]=f},
 window:{addEventListener:(e,f)=>listeners[e]=f},AbortController,setInterval:f=>timers.push(f),
 fetch:async path=>{
  let data;
  if(path.endsWith('/state'))data={classroom_id:'A',classroom_state:closed?'CLOSED':'OPEN',state_version:closed?2:1,group_name:'A',activity:{activity_id:'quiz',phase:'CLOSED',group_id:currentGroup,questions:[]}};
  else if(path.startsWith('/classrooms/'))data={activities:[{activity_id:'quiz',title:'Original result'}]};
  else {if(delay)await new Promise(r=>release=r);data={status:'settled',results:[{question_id:'q',winner_name:'A',winner_answer:'original answer',own:{answer:'own answer',rank:1}}]};}
  return {ok:true,status:200,json:async()=>data};
 }});
 vm.runInContext(fs.readFileSync('src/guided_notes/static/student-room.js','utf8'),ctx);
 const flush=async()=>{await new Promise(setImmediate);await new Promise(setImmediate);};
 await flush();
 return {ids,flush,async tick(){timers[0]();await flush();},close(){closed=true;},changeGroup(){currentGroup=2;},delay(){delay=true;},release(){release();},listeners};
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
