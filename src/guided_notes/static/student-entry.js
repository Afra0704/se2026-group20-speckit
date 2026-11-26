(() => {
  const main=document.querySelector('main'), form=document.getElementById('join');
  const message=document.getElementById('message'), button=form.querySelector('button');
  const errors={JOIN_DENIED:'查無此課堂',INVALID_REQUEST:'請輸入課堂碼與組別。',INVALID_CSRF:'頁面驗證已過期，請重新整理後再試。',TOO_MANY_ATTEMPTS:'嘗試次數過多，請稍後再試。',TEMPORARILY_UNAVAILABLE:'服務忙碌，請稍後重試。'};
  let pending=false;
  form.addEventListener('submit',async event=>{
    event.preventDefault();if(pending)return;
    pending=true;button.disabled=true;message.textContent='正在加入…';
    try{
      const response=await fetch('/classroom-memberships',{method:'POST',cache:'no-store',headers:{'Content-Type':'application/json','X-CSRF-Token':main.dataset.csrf},body:JSON.stringify(Object.fromEntries(new FormData(form)))});
      const data=await response.json();
      if(!response.ok)throw new Error(data.error);
      if(typeof data.classroom_id!=='string'||!data.classroom_id)throw new Error('INVALID_RESPONSE');
      window.location.assign('/student/classrooms/'+encodeURIComponent(data.classroom_id));
    }catch(error){message.textContent=errors[error.message]||'暫時無法加入，請確認連線後重試。';message.focus();}
    finally{pending=false;button.disabled=false;}
  });
})();
