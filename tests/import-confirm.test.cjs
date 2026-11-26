const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

function setup(stale){
  const handlers={},calls=[],locations=[],errors=[];
  const flow={dataset:{flowId:'flow-A',status:'preview_ready',sourceKind:'link',revision:'5',choiceRevision:'1'},querySelectorAll:()=>[]};
  const form={addEventListener:(event,fn)=>handlers[event]=fn};
  const context={
    document:{querySelector:s=>s==='main'?{dataset:{courseId:'course-A'}}:null,getElementById:id=>id==='import-flow'?flow:id==='confirm-import'?form:null,querySelectorAll:()=>[],addEventListener(){}},
    api:async(path,body)=>{
      calls.push({path,body});
      if(!body)return {preview_id:'preview-B-new'};
      if(stale && body.preview_id==='preview-A-visible')throw Object.assign(new Error('這份預覽已失效，請重新整理並核對最新內容。'),{code:'PREVIEW_STALE'});
      return {course_url:'/lectures'};
    },
    report:error=>errors.push(error.code),
    FormData:class{*[Symbol.iterator](){yield ['existing_import_id',''];yield ['preview_id','preview-A-visible'];}},
    location:{assign:p=>locations.push(p),reload:()=>locations.push('reload')},sessionStorage:{getItem:()=>null},setInterval(){}
  };
  vm.runInNewContext(fs.readFileSync('src/guided_notes/static/import-flow.js','utf8').replace(/^import [^\r\n]*[\r\n]+/,''),context);
  return {calls,locations,errors,submit:()=>handlers.submit({preventDefault(){},target:form})};
}

test('confirm submits the preview displayed in this tab, never fetches a replacement ID',async()=>{
  const s=setup(false);await s.submit();
  assert.equal(s.calls.length,1);
  assert.equal(s.calls[0].body.preview_id,'preview-A-visible');
  assert.deepEqual(s.locations,['/lectures']);
});

test('an old tab reports PREVIEW_STALE and never confirms the other tab\'s preview',async()=>{
  const s=setup(true);await s.submit();
  assert.equal(s.calls.length,1);
  assert.equal(s.calls[0].body.preview_id,'preview-A-visible');
  assert.deepEqual(s.errors,['PREVIEW_STALE']);
  assert.deepEqual(s.locations,[]);
});
