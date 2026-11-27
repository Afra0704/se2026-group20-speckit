(() => {
  function stateFor(room){
    let generation=0,version=-1,closed=false;
    return {get generation(){return generation;},get closed(){return closed;},
      invalidate(){generation++;},
      close(){closed=true;generation++;},
      accept(data,requestGeneration){
        if(closed||requestGeneration!==generation||data.classroom_id!==room||data.state_version<version)return false;
        version=data.state_version;
        if(data.classroom_state==='CLOSED'){closed=true;generation++;}
        return true;
      }};
  }
  globalThis.StudentRoomState=stateFor;
  if(typeof document==='undefined')return;
  const main=document.querySelector('main'), room=main.dataset.classroomId, state=stateFor(room);
  const byId=id=>document.getElementById(id), content=byId('room-content');
  let activity=null,group=null,view=null,polling=false,controller=new AbortController(),recovering=false;
  let historyKey=null,selectedResult=null,resultOutput=null;
  let historyRequest=null;
  let historyFailed=false,historyNotice=null;
  let scopeBlocked=false;
  const phaseText={PREPARING:'尚未開放搶答',LIVE:'搶答中',CLOSED:'活動已結束'};
  function clear(){content.hidden=true;byId('questions').replaceChildren();byId('results').replaceChildren();activity=null;view=null;historyKey=null;selectedResult=null;resultOutput=null;historyFailed=false;historyNotice=null;}
  function ended(){if(!state.closed)state.close();controller.abort();clear();byId('access-notice').hidden=true;byId('closed-notice').hidden=false;byId('state').textContent='課堂已結束';byId('message').textContent='';}
  async function api(path,body,key){
    const options={cache:'no-store',signal:controller.signal,headers:{'X-Activity-Role':'student'}};
    if(body!==undefined){options.method='POST';Object.assign(options.headers,{'Content-Type':'application/json','X-CSRF-Token':main.dataset.csrf});options.body=JSON.stringify(body);}
    if(key)options.headers['Idempotency-Key']=key;
    const response=await fetch(path,options), data=response.status===204?null:await response.json();
    if(!response.ok){const error=new Error(data?.error||'REQUEST_FAILED');error.status=response.status;throw error;}
    return data;
  }
  function valid(gen,id){return !state.closed&&gen===state.generation&&(!id||activity===id);}
  function error(error,gen){
    if(gen!==state.generation||error.name==='AbortError')return;
    if(error.message==='CLASSROOM_CLOSED'){ended();return;}
    if(['AUTH_REQUIRED','FORBIDDEN','RECOVERY_DENIED'].includes(error.message)){
      state.invalidate();clear();byId('access-notice').hidden=false;byId('state').textContent='請重新驗證本堂資格';
    }else{state.invalidate();clear();byId('state').textContent='連線中斷，正在重新連線…';}
  }
  function textAnswer(value){return typeof value==='string'?value:Object.values(value||{}).join('、');}
  function describeRow(row) {
    const winner=row.winner_items?.map(i=>`${i.subitem_label||''} ${i.answer_text}`).join('；')||textAnswer(row.winner_answer);
    const own=row.own?.items?.map(i=>`${i.subitem_label||''} ${i.answer_text}`).join('；')||textAnswer(row.own?.answer);
    return `${row.display_number||row.question_id} · ${row.winner_name?`勝組 ${row.winner_name}：${winner}`:'無勝組'}${row.own?`\n本組：${own}（順位 ${row.own.rank}）`:'\n本組未提交'}`;
  }
  function questions(data){
    const current=data.activity, id=current?.activity_id||null;
    if(activity!==id||!view){
      byId('questions').replaceChildren();activity=id;
      for(const q of current?.questions||[]){
        const li=document.createElement('li'),form=document.createElement('form');
        const title=document.createElement('h2');title.textContent=`題目 ${q.display_number}`;li.append(title);
        for(const item of q.items){
          const label=document.createElement('label'),prompt=document.createElement('p'),input=document.createElement('input');
          prompt.className='question-prompt';prompt.textContent=[item.subitem_label,item.prompt_text??'此版本缺少完整題目，請老師選擇完整版本。'].filter(Boolean).join(' ');
          input.name=item.item_id;input.required=true;label.append(prompt,input);form.append(label);
        }
        const button=document.createElement('button');button.textContent='提交';form.append(button);li.append(form);byId('questions').append(li);
        const gen=state.generation;
        const context=()=>valid(gen,id)&&group!==null?{room,activity:id,group,live:view?.phase==='LIVE'}:null;
        const send=(aid,body,key)=>api(`/activities/${encodeURIComponent(aid)}/submissions`,body,key);
        const accepted=()=>{if(valid(gen,id))byId('message').textContent='答案已受理';};
        const failed=e=>{if(!valid(gen,id))return;if(['CLASSROOM_CLOSED','AUTH_REQUIRED','FORBIDDEN'].includes(e.message))error(e,gen);else byId('message').textContent=e.message==='QUIZ_UNAVAILABLE'?'正式搶答服務尚未接入，請告知老師。':'送答未完成，請確認連線後重試。';};
        form.quizUpdate=QuizSubmission.attach(form,button,q.question_id,context,send,accepted,failed);
      }
    }
    view=current;
    for(const input of byId('questions').querySelectorAll('input,button'))input.disabled=current?.phase!=='LIVE';
    for(const form of byId('questions').querySelectorAll('form'))form.quizUpdate?.();
  }
  async function results(gen){
    if(historyFailed||historyRequest?.generation===gen)return;
    const request={generation:gen};
    historyRequest=request;
    try{await loadHistory(gen);}
    catch(e){
      if(!valid(gen)||e.name==='AbortError')return;
      if(['CLASSROOM_CLOSED','AUTH_REQUIRED','FORBIDDEN','RECOVERY_DENIED'].includes(e.message)){
        error(e,gen);
      }else{
        historyFailed=true;
        if(!historyNotice){
          historyNotice=document.createElement('div');
          historyNotice.setAttribute('role','alert');
          const retry=document.createElement('button');
          retry.type='button';retry.textContent='歷史結果清單讀取失敗，重試';
          retry.onclick=()=>{if(valid(gen)){historyFailed=false;void results(gen);}};
          historyNotice.append(retry);
          byId('results').append(historyNotice);
        }
        historyNotice.hidden=false;
      }
    }
    finally{if(historyRequest===request)historyRequest=null;}
  }
  function output(){
    if(!resultOutput){
      resultOutput=document.createElement('div');
      resultOutput.className='classroom-result-output';
      byId('results').append(resultOutput);
    }
    return resultOutput;
  }
  async function loadHistory(gen){
    const list=await api(`/classrooms/${encodeURIComponent(room)}/results`);
    if(!valid(gen))return;
    const key=JSON.stringify(list.activities||[]),container=byId('results');
    if(key!==historyKey){
      const panel=output();
      historyKey=key;container.replaceChildren();
      for(const item of list.activities||[]){
        const button=document.createElement('button');button.textContent=item.title||'活動結果';button.type='button';
        button.onclick=async()=>{
          if(!valid(gen)||historyKey!==key)return;
          selectedResult={id:item.activity_id,title:item.title,loading:false};
          panel.textContent='';
          await selected(gen);
        };container.append(button);
      }
      container.append(panel);
      if(historyNotice)container.append(historyNotice);
    }
    if(historyNotice)historyNotice.hidden=true;
    void selected(gen);
  }
  async function selected(gen){
    const selection=selectedResult;
    if(!selection||selection.loading||selection.done||!valid(gen))return;
    const isCurrent=()=>valid(gen)&&selectedResult===selection&&resultOutput;
    selection.loading=true;
    try{const data=await api(`/activities/${encodeURIComponent(selection.id)}/results`);
      if(!isCurrent())return;
      selection.done=data.status==='settled'||data.status==='unavailable';
      const title=document.createElement('h2');
      title.textContent=selection.title||'活動結果';
      resultOutput.replaceChildren(title);
      if(data.status==='settled'&&data.results?.length){
        for(const row of data.results){
          const card=document.createElement('p');
          card.className='classroom-result-card';
          card.textContent=describeRow(row);
          resultOutput.append(card);
        }
      }else{
        const status=document.createElement('p');
        status.textContent=data.status==='unavailable'?'此活動沒有可用的正式結果。':
          data.status==='settled'?'沒有已公布的結果。':'結果結算中';
        resultOutput.append(status);
      }
    }catch(e){
      if(!isCurrent())return;
      if(['CLASSROOM_CLOSED','AUTH_REQUIRED','FORBIDDEN','RECOVERY_DENIED'].includes(e.message)){
        error(e,gen);
      }else if(e.name!=='AbortError'){
        selection.done=true;
        const retry=document.createElement('button');
        retry.type='button';
        retry.textContent='結果讀取失敗，重試';
        retry.onclick=()=>{if(isCurrent()){selection.done=false;void selected(gen);}};
        resultOutput.replaceChildren(retry);
      }
    }
    finally{selection.loading=false;}
  }
  async function refresh(){
    if(polling||state.closed||recovering||scopeBlocked)return;
    polling=true;const gen=state.generation;
    try{
      const data=await api(`/classrooms/${encodeURIComponent(room)}/state`);
      if(!state.accept(data,gen))return;
      if(state.closed){ended();return;}
      if(group!==null&&data.activity?.group_id!=null&&group!==data.activity.group_id){
        scopeBlocked=true;state.invalidate();clear();byId('access-notice').hidden=false;byId('recover').hidden=true;
        byId('state').textContent='組別資格已變更，請返回加入頁重新加入。';return;
      }
      byId('access-notice').hidden=true;byId('state').textContent=[data.group_name,phaseText[data.activity?.phase]||'等候老師建立活動'].filter(Boolean).join(' · ');
      const nextId=data.activity?.activity_id||null;
      if(activity!==nextId&&selectedResult){
        selectedResult=null;
        if(resultOutput)resultOutput.replaceChildren();
      }
      group=data.activity?.group_id??group;questions(data);
      byId('questions').hidden=data.activity?.phase==='CLOSED';
      if(data.activity?.phase==='CLOSED'&&!selectedResult){
        selectedResult={id:nextId,title:data.activity.title,loading:false};
        output();
      }
      void selected(gen);
      byId('activity-title').textContent=data.activity?.title||'等候老師建立活動';content.hidden=false;
      void results(gen);
    }catch(e){error(e,gen);}finally{polling=false;}
  }
  byId('recover').onclick=async()=>{
    if(recovering||state.closed)return;
    recovering=true;const gen=state.generation;byId('recover').disabled=true;
    try{await api(`/classrooms/${encodeURIComponent(room)}/result-access`,{});}
    catch(e){error(e,gen);}finally{recovering=false;byId('recover').disabled=false;}
    await refresh();
  };
  function suspend(){state.invalidate();controller.abort();controller=new AbortController();clear();}
  function resume(){suspend();refresh();}
  let leavePresence=()=>{},restorePresence=()=>{};
  window.addEventListener('pagehide',()=>{leavePresence();suspend();});
  window.addEventListener('pageshow',()=>{resume();restorePresence();});
  window.addEventListener('online',()=>{resume();restorePresence();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)suspend();else resume();});
  setInterval(()=>{if(!document.hidden)refresh();},1000);
  const newPageId=()=>globalThis.crypto?.getRandomValues
    ? Array.from(crypto.getRandomValues(new Uint8Array(16)), value=>value.toString(16).padStart(2,'0')).join('') : null;
  let pageId=newPageId();
  if(pageId){
    let presencePending=null,departed=false;
    const beacon=(path)=>{
      if(typeof globalThis.navigator?.sendBeacon!=='function')return false;
      try{
        return navigator.sendBeacon(path,new URLSearchParams({page_id:pageId,csrf_token:main.dataset.csrf}));
      }catch{return false;}
    };
    const heartbeat=async()=>{
      const generation=state.generation;
      if(presencePending?.generation===generation||departed||state.closed||scopeBlocked)return;
      const path=`/classrooms/${encodeURIComponent(room)}/presence`;
      if(document.hidden&&beacon(path))return;
      const request={generation};
      presencePending=request;
      try{await api(path,{page_id:pageId});}
      catch(e){if(valid(generation)&&e.message==='CLASSROOM_CLOSED')ended();}
      finally{if(presencePending===request)presencePending=null;}
    };
    setInterval(heartbeat,1000);
    leavePresence=()=>{
      if(departed||state.closed||scopeBlocked)return;
      departed=true;
      const path=`/classrooms/${encodeURIComponent(room)}/presence/leave`;
      if(beacon(path))return;
      // Independent of the polling AbortController, which pagehide cancels.
      void fetch(path,{
        method:'POST',keepalive:true,cache:'no-store',
        headers:{'Content-Type':'application/json','X-CSRF-Token':main.dataset.csrf},
        body:JSON.stringify({page_id:pageId}),
      }).catch(()=>{});
    };
    restorePresence=()=>{
      if(departed){pageId=newPageId();departed=false;}
      void heartbeat();
    };
    document.addEventListener('visibilitychange',()=>{void heartbeat();});
    void heartbeat();
  }
  refresh();
})();
