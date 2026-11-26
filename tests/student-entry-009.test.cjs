const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
function setup(response){
 const button={disabled:false}, message={textContent:'',focus(){}};
 const form={querySelector:()=>button,addEventListener(_,handler){this.submit=handler;}};
 const main={dataset:{csrf:'test'}};
 const calls=[], destinations=[];
 const ctx=vm.createContext({document:{querySelector:()=>main,getElementById:id=>id==='join'?form:message},
 FormData:class{*[Symbol.iterator](){yield ['code','AB123'];yield ['group_name','A'];}},
 window:{location:{assign:path=>destinations.push(path)}},
 fetch:async(path,options)=>{calls.push([path,options]);return typeof response==='function'?response():response;}});
 vm.runInContext(fs.readFileSync('src/guided_notes/static/student-entry.js','utf8'),ctx);
 return {form,button,message,calls,destinations};
}
test('join has no background request, then navigates using server classroom identity',async()=>{
 const x=setup({ok:true,json:async()=>({classroom_id:'new-room'})});
 assert.equal(x.calls.length,0);
 await x.form.submit({preventDefault(){}});
 assert.deepEqual(x.destinations,['/student/classrooms/new-room']);
 assert.equal(x.calls[0][0],'/classroom-memberships');
 assert.equal(x.calls[0][1].headers['X-CSRF-Token'],'test');
});
test('invalid code stays on join page and allows retry',async()=>{
 const x=setup({ok:false,json:async()=>({error:'JOIN_DENIED'})});
 await x.form.submit({preventDefault(){}});
 assert.equal(x.message.textContent,'查無此課堂');
 assert.deepEqual(x.destinations,[]);
 assert.equal(x.button.disabled,false);
});

test('pending join ignores double submit then permits a deliberate retry',async()=>{
 let release;
 const x=setup(()=>new Promise(r=>release=r));
 const first=x.form.submit({preventDefault(){}});
 await x.form.submit({preventDefault(){}});
 assert.equal(x.calls.length,1);assert.equal(x.button.disabled,true);
 release({ok:false,json:async()=>({error:'JOIN_DENIED'})});await first;
 const retry=x.form.submit({preventDefault(){}});
 assert.equal(x.calls.length,2);
 release({ok:true,json:async()=>({classroom_id:'B'})});await retry;
 assert.deepEqual(x.destinations,['/student/classrooms/B']);
});

for(const error of ['INVALID_CSRF','TOO_MANY_ATTEMPTS','TEMPORARILY_UNAVAILABLE']){
 test(`${error} remains on entry page and restores the action`,async()=>{
  const x=setup({ok:false,json:async()=>({error})});
  await x.form.submit({preventDefault(){}});
  assert.deepEqual(x.destinations,[]);assert.equal(x.button.disabled,false);
  assert.ok(x.message.textContent.length>0);
 });
}

test('network failure remains retryable and has no background rejoin',async()=>{
 const x=setup(()=>{throw new Error('offline');});
 await x.form.submit({preventDefault(){}});
 assert.equal(x.calls.length,1);assert.equal(x.button.disabled,false);
 assert.deepEqual(x.destinations,[]);
});
