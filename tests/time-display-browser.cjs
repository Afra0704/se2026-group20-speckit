// Optional real-browser evidence; isolated profiles, no existing cookies or Google.
// Run: node tests/time-display-browser.cjs
const {spawn, spawnSync} = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');

async function main() {
  const executable=process.env.TIME_DISPLAY_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
  if (!fs.existsSync(executable)) throw Error('Set TIME_DISPLAY_CHROME to an existing Chromium executable');
  const python=process.env.TIME_DISPLAY_PYTHON || 'D:/os_final/.venv/Scripts/python.exe';
  const fixture=spawnSync(python,['-c',
    "import json; from guided_notes.time_views import activity_time_display; print(json.dumps(activity_time_display({'phase':'CLOSED','phase_version':1,'created_at':'2026-11-26 16:03:59','started_at':None,'closed_at':'2026-11-26 16:04:59'},trusted_lifecycle=True)))"],
    {encoding:'utf8',env:{...process.env,PYTHONPATH:path.resolve('src')},windowsHide:true});
  assert.equal(fixture.status,0,fixture.stderr);
  const metadata=JSON.parse(fixture.stdout);
  const source=fs.readFileSync('src/guided_notes/static/classroom.js','utf8');
  const implementation=source.slice(source.indexOf('async function activityList('),source.indexOf('function addResultButton('));
  const profile=fs.mkdtempSync(path.join(os.tmpdir(),'guided-notes-time-browser-'));
  const child=spawn(executable,['--headless=new','--no-first-run','--no-default-browser-check',
    '--disable-background-networking','--disable-extensions','--disable-sync',
    '--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],
    {windowsHide:true,stdio:['ignore','ignore','pipe']});
  let socket;
  try {
    const address=await new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>reject(Error('Chromium DevTools startup timed out')),15000);
      let log='';
      child.on('error',error=>{clearTimeout(timer);reject(error);});
      child.stderr.on('data',chunk=>{
        log+=chunk.toString();const match=log.match(/DevTools listening on (ws:\/\/[^\s]+)/);
        if(match){clearTimeout(timer);resolve(match[1]);}
      });
      child.on('exit',code=>{clearTimeout(timer);reject(Error(`Chromium exited before connection: ${code}`));});
    });
    socket=new WebSocket(address);
    await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
    let seq=0;const pending=new Map();
    socket.onmessage=({data})=>{
      const message=JSON.parse(data);if(!message.id)return;
      const call=pending.get(message.id);if(!call)return;
      pending.delete(message.id);clearTimeout(call.timer);
      if(message.error)call.reject(Error(message.error.message));else call.resolve(message.result);
    };
    const send=(method,params={},sessionId)=>new Promise((resolve,reject)=>{
      const id=++seq;const timer=setTimeout(()=>{pending.delete(id);reject(Error(`CDP timeout: ${method}`));},10000);
      pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params,...(sessionId?{sessionId}:{})}));
    });
    const version=await send('Browser.getVersion');const observations=[];
    for(const timezoneId of ['UTC','Asia/Taipei','America/New_York']) {
      const {browserContextId}=await send('Target.createBrowserContext');
      try {
        const {targetId}=await send('Target.createTarget',{url:'about:blank',browserContextId});
        const {sessionId}=await send('Target.attachToTarget',{targetId,flatten:true});
        await send('Emulation.setTimezoneOverride',{timezoneId},sessionId);
        const expression=`(async()=>{
          document.body.innerHTML='<ul id="activities"></ul><button id="close-room" disabled></button>';
          let historyRequest=0,selection=1,version=1,room='room',historyNeedsRefresh=false,historyUnfinished=false;
          let returnSelectionPending=true,selectedResult=null,activeId='a';
          const role='teacher',returnedResultId='a';
          const main={dataset:{}},url=encodeURIComponent,byId=id=>document.getElementById(id);
          function updateCreateAvailability(){} function addResultButton(){}
          function note(){throw Error('original activity selection was lost');}
          async function api(){return {activities:[{activity_id:'a',title:'<b>安全純文字</b>',phase:'CLOSED',time_display:${JSON.stringify(metadata)}}]};}
          ${implementation}
          await activityList('room');
          return {timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,text:byId('activities').textContent,
            selectedActivity: selectedResult?.id,
            unsafeElements:byId('activities').querySelectorAll('b').length};
        })()`;
        const result=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true},sessionId);
        assert.equal(result.exceptionDetails,undefined,JSON.stringify(result.exceptionDetails));
        const value=result.result.value;
        assert.equal(value.timezone,timezoneId);
        assert.equal(value.unsafeElements,0);
        assert.equal(value.selectedActivity,'a');
        assert.ok(value.text.includes('建立：2026-11-27 00:03'),value.text);
        assert.ok(value.text.includes('開始：未開始即結束'),value.text);
        assert.ok(value.text.includes('結束：2026-11-27 00:04'),value.text);
        observations.push(value);
      } finally {await send('Target.disposeBrowserContext',{browserContextId});}
    }
    assert.equal(new Set(observations.map(v=>v.text)).size,1);
    console.log(JSON.stringify({browser:version.product,observations,passed:true},null,2));
    await send('Browser.close');
  } finally {
    socket?.close();child.kill();
  }
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
