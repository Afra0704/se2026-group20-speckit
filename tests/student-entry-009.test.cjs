const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
function setup(response){
 const button={disabled:false}, message={textContent:'',focus(){}};
 const form={querySelector:()=>button,addEventListener(_,handler){this.submit=handler;}};
 const field={value:'1',attributes:{},focus(){this.focused=true;},setAttribute(k,v){this.attributes[k]=v;},removeAttribute(k){delete this.attributes[k];},addEventListener(k,f){this[k]=f;}}; const fieldError={textContent:'',hidden:true};
 const main={dataset:{csrf:'test'}};
 const calls=[], destinations=[];
 const ctx=vm.createContext({document:{querySelector:()=>main,getElementById:id=>id==='join'?form:id==='join-group'?field:id==='join-group-error'?fieldError:message},
 FormData:class{*[Symbol.iterator](){yield ['code','AB123'];yield ['group_name',field.value];}},
 window:{location:{assign:path=>destinations.push(path)}},
 fetch:async(path,options)=>{calls.push([path,options]);return typeof response==='function'?response():response;}});
 vm.runInContext(fs.readFileSync('src/guided_notes/static/student-entry.js','utf8'),ctx);
 return {form,button,message,calls,destinations,field,fieldError};
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

test('invalid group stays by the field and corrected input is submitted',async()=>{
 const x=setup({ok:true,json:async()=>({classroom_id:'room'})});
 x.field.value='01';
 await x.form.submit({preventDefault(){}});
 assert.equal(x.calls.length,0);
 assert.equal(x.field.value,'01');
 assert.equal(x.field.attributes['aria-invalid'],'true');
 assert.equal(x.field.focused,true);
 assert.equal(x.fieldError.hidden,false);
 x.field.value=' 999 ';x.field.input();
 await x.form.submit({preventDefault(){}});
 assert.equal(JSON.parse(x.calls[0][1].body).group_name,'999');
 assert.equal(x.fieldError.hidden,true);
});

test('server group error is shown at the same field and permits retry',async()=>{
 const x=setup({ok:false,json:async()=>({error:'INVALID_GROUP_NUMBER'})});
 await x.form.submit({preventDefault(){}});
 assert.equal(x.fieldError.hidden,false);
 assert.equal(x.field.attributes['aria-invalid'],'true');
 assert.equal(x.message.textContent,'');
 assert.equal(x.button.disabled,false);
});
