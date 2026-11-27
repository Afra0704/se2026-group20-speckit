(() => {
  const main=document.querySelector('main'), form=document.getElementById('join');
  const message=document.getElementById('message'), button=form.querySelector('button');
  const group=document.getElementById('join-group'), groupError=document.getElementById('join-group-error');
  const errors={JOIN_DENIED:'查無此課堂',INVALID_REQUEST:'請輸入課堂碼與組別。',INVALID_CSRF:'頁面驗證已過期，請重新整理後再試。',TOO_MANY_ATTEMPTS:'嘗試次數過多，請稍後再試。',TEMPORARILY_UNAVAILABLE:'服務忙碌，請稍後重試。'};
  let pending=false;
  let attempt=null;
  errors.CLASSROOM_GROUP_IN_USE='這個瀏覽器在本堂已有其他組別在線。請使用原組，或等原組最後一頁離線後再試。';
  function clearGroupError(){
    group.removeAttribute('aria-invalid');
    groupError.hidden=true;
    groupError.textContent='';
  }
  function showGroupError(){
    message.textContent='';
    group.setAttribute('aria-invalid','true');
    groupError.textContent='請輸入 1 到 999 的半形數字，開頭不可為 0。';
    groupError.hidden=false;
    group.focus();
  }
  group.addEventListener('input',clearGroupError);
  group.addEventListener('invalid',event=>{event.preventDefault();showGroupError();});
  form.addEventListener('submit',async event=>{
    event.preventDefault();if(pending)return;
    clearGroupError();
    const submittedGroup=group.value;
    const groupNumber=submittedGroup.trim();
    if(!/^[1-9][0-9]{0,2}$/.test(groupNumber)){showGroupError();return;}
    const body=Object.fromEntries(new FormData(form));
    body.group_name=groupNumber;
    const signature=JSON.stringify(body);
    const tabProtocol=main.dataset.pageProtocol==='1';
    pending=true;button.disabled=true;message.textContent='正在加入…';
    try{
      if(tabProtocol){
        if(attempt?.signature!==signature){
          attempt={signature,page_id:crypto.randomUUID(),request_id:crypto.randomUUID()};
        }
        Object.assign(body,{page_protocol:1,page_id:attempt.page_id,request_id:attempt.request_id});
      }
      const response=await fetch('/classroom-memberships',{method:'POST',cache:'no-store',headers:{'Content-Type':'application/json','X-CSRF-Token':main.dataset.csrf},body:JSON.stringify(body)});
      const data=await response.json();
      if(!response.ok){
        if(response.status<500)attempt=null;
        throw new Error(data.error);
      }
      if(typeof data.classroom_id!=='string'||!data.classroom_id)throw new Error('INVALID_RESPONSE');
      if(tabProtocol){
        if(typeof data.resume_id!=='string'||!data.resume_id)throw new Error('INVALID_RESPONSE');
        sessionStorage.setItem('classroom-tab:'+data.classroom_id,JSON.stringify({resume:data.resume_id}));
      }
      window.location.assign('/student/classrooms/'+encodeURIComponent(data.classroom_id));
    }catch(error){
      if(error.message==='INVALID_GROUP_NUMBER'){
        if(group.value===submittedGroup)showGroupError();
        else message.textContent='';
      }else{
        message.textContent=errors[error.message]||'暫時無法加入，請確認連線後重試。';message.focus();
      }
    }
    finally{pending=false;button.disabled=false;}
  });
})();
