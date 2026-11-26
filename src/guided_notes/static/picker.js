import {api} from './workspace.js';
let library;
function load(){if(!library)library=new Promise((resolve,reject)=>{const script=document.createElement('script');script.src='https://apis.google.com/js/api.js';script.onload=()=>gapi.load('picker',{callback:resolve,onerror:()=>reject(new Error('無法載入Google選檔，請重試或改用連結。'))});script.onerror=()=>{library=null;reject(new Error('無法連線Google，請重試或改用連結。'));};document.head.append(script);});return library;}
export async function pick(base){
  await load();let delivery=await api(base+'/picker/token',{});let picker;
  return new Promise((resolve,reject)=>{
    let done=false;const timer=setTimeout(()=>finish(null,new Error('選檔已逾時，請重新開啟。')),Math.min(delivery.expires_in,delivery.ticket_expires_in)*1000);
    function finish(result,error){if(done)return;done=true;clearTimeout(timer);delivery=null;if(picker){picker.setVisible(false);picker.dispose?.();picker=null;}window.removeEventListener('pagehide',leave);error?reject(error):resolve(result);}
    const leave=()=>finish(null);window.addEventListener('pagehide',leave,{once:true});
    try{
      const view=new google.picker.DocsView(google.picker.ViewId.SPREADSHEETS).setMimeTypes('application/vnd.google-apps.spreadsheet');
      picker=new google.picker.PickerBuilder().addView(view).setOAuthToken(delivery.access_token).setDeveloperKey(delivery.api_key).setAppId(delivery.app_id).setOrigin(location.origin).setCallback(data=>{
        if(data.action===google.picker.Action.CANCEL)finish(null);
        if(data.action===google.picker.Action.PICKED){const docs=data.docs;if(!docs || docs.length!==1){finish(null,new Error('請只選擇一份Google Sheets。'));return;}finish({file_id:docs[0].id,ticket_id:delivery.ticket_id});}
      }).build();picker.setVisible(true);
    }catch{finish(null,new Error('選檔視窗無法開啟，請檢查瀏覽器設定或改用連結。'));}
  });
}
