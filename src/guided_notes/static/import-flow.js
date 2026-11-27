import {api,report} from './workspace.js';
const main=document.querySelector('main');
const course=main.dataset.courseId;
const flow=document.getElementById('import-flow');
const base=flow ? `/teacher/workspace/imports/${encodeURIComponent(flow.dataset.flowId)}` : null;
const toggle=document.getElementById('import-toggle');
const menu=document.getElementById('import-menu');
function closeMenu(){if(menu){menu.hidden=true;toggle.setAttribute('aria-expanded','false');toggle.focus();}}
toggle?.addEventListener('click',()=>{menu.hidden=!menu.hidden;toggle.setAttribute('aria-expanded',String(!menu.hidden));});
document.addEventListener('keydown',event=>{if(event.key==='Escape' && menu && !menu.hidden)closeMenu();});
document.addEventListener('click',event=>{if(menu && !menu.hidden && !menu.contains(event.target) && event.target!==toggle)closeMenu();});
async function create(source_kind,spreadsheet_url){const result=await api(`/teacher/workspace/courses/${encodeURIComponent(course)}/imports`,{source_kind,...(spreadsheet_url ? {spreadsheet_url}: {})});location.assign(result.flow_url);}
document.querySelector('[data-cloud]')?.addEventListener('click',()=>create('cloud').catch(report));
document.querySelector('[data-link]')?.addEventListener('click',()=>{closeMenu();const form=document.getElementById('link-import');form.hidden=false;form.querySelector('input').focus();});
const linkForm = document.getElementById('link-import');
if (linkForm) {
  const input = linkForm.querySelector('input');
  const button = linkForm.querySelector('button');
  const fieldError = document.getElementById('spreadsheet-url-error');
  const operationError = document.getElementById('link-import-error');
  const reconnect = document.getElementById('link-import-reconnect');
  const reconnectCodes = new Set(['SHEETS_CONNECT_REQUIRED', 'SHEETS_REAUTH_REQUIRED',
    'GOOGLE_REAUTH_REQUIRED', 'GOOGLE_CREDENTIALS_REFRESH_REQUIRED']);
  let pendingLink = linkForm.dataset?.flowUrl
    ? {url: input.value, flowUrl: linkForm.dataset.flowUrl} : null;

  async function readLink(url) {
    let state;
    if (pendingLink?.url === url) {
      try {
        state = await api(pendingLink.flowUrl);
      } catch (error) {
        if (['FLOW_EXPIRED', 'FLOW_INVALIDATED', 'FLOW_NOT_FOUND'].includes(error.code)) pendingLink = null;
        else throw error;
      }
    } else pendingLink = null;
    if (!pendingLink || ['completed', 'cancelled'].includes(state?.status)) {
      const created = await api(`/teacher/workspace/courses/${encodeURIComponent(course)}/imports`,
        {source_kind: 'link', spreadsheet_url: url});
      pendingLink = {url, flowUrl: created.flow_url};
      state = created;
    }
    if (!['worksheets_ready', 'preview_ready'].includes(state.status)) {
      const action = state.status === 'failed' || (state.status === 'reading' && state.retryable) ? 'retry' : 'read';
      await api(pendingLink.flowUrl + '/' + action, {});
    }
    // Authorization, if needed, continues through the existing browser-bound flow.
    location.assign(pendingLink.flowUrl);
  }

  function clearLinkErrors() {
    fieldError.textContent = '';
    fieldError.hidden = true;
    operationError.textContent = '';
    operationError.hidden = true;
    input.removeAttribute('aria-invalid');
    if (reconnect) reconnect.hidden = true;
  }

  function showLinkError(message) {
    fieldError.textContent = message;
    fieldError.hidden = false;
    input.setAttribute('aria-invalid', 'true');
    input.focus();
  }

  input.addEventListener('invalid', event => {
    event.preventDefault();
    clearLinkErrors();
    showLinkError(input.validity.valueMissing
      ? '請輸入 Google Sheets 連結。'
      : '請輸入有效的 Google Sheets 連結。');
  });
  input.addEventListener('input', clearLinkErrors);

  linkForm.addEventListener('submit', async event => {
    event.preventDefault();
    if (button.disabled) return;
    clearLinkErrors();
    const url = input.value;
    button.disabled = true;
    try {
      await readLink(url);
    } catch (error) {
      if (input.value !== url) return;
      if (error.code === 'INVALID_SHEETS_URL') {
        showLinkError('請輸入有效的 Google Sheets 連結。');
      } else {
        operationError.textContent = error.code
          ? error.message
          : '暫時無法讀取 Google Sheets，請稍後重試。';
        operationError.hidden = false;
        if (reconnect && pendingLink && reconnectCodes.has(error.code)) {
          reconnect.querySelector('[name="return_to"]').value = pendingLink.flowUrl;
          reconnect.hidden = false;
        }
      }
    } finally {
      button.disabled = false;
    }
  });
}
let busy=false;
async function showFailedFlow(action) {
  if (!['read', 'retry', 'previews', 'picker/selection'].includes(action)) return false;
  try {
    const state = await api(base);
    if (state.status === 'failed') {
      // Render the server's error and retry action instead of keeping a stale read button.
      location.reload();
      return true;
    }
  } catch {
    // Keep the original operation error visible when the state cannot be read.
  }
  return false;
}
async function run(action,body={}){if(busy)return;busy=true;const buttons=flow?.querySelectorAll('button')||[];buttons.forEach(b=>b.disabled=true);try{return await api(base+'/'+action,body);}catch(error){if(error.code==='SOURCE_CHANGED')location.reload();else if(!await showFailedFlow(action))report(error);throw error;}finally{busy=false;buttons.forEach(b=>b.disabled=false);}}
async function read(){let result=await run('read');if(result.needs_authorization){result=await run('authorize',{credential_kind:result.needs_authorization});if(result.authorization_url){location.assign(result.authorization_url);return;}}location.reload();}
document.getElementById('read-source')?.addEventListener('click',()=>read().catch(()=>{}));
document.getElementById('open-picker')?.addEventListener('click',async()=>{try{const result=await run('authorize',{credential_kind:'picker'});if(result.authorization_url){location.assign(result.authorization_url);return;}const {pick}=await import('./picker.js');const file=await pick(base);if(file){await run('picker/selection',file);location.reload();}}catch(error){report(error);}});
const preview=document.getElementById('preview-form');
preview?.querySelector('[name=sheet_id]').addEventListener('change',event=>{document.getElementById('name-options').hidden=!event.target.value;});
preview?.addEventListener('submit',async event=>{event.preventDefault();const data=Object.fromEntries(new FormData(preview));data.sheet_id=Number(data.sheet_id);data.choice_revision=Number(flow.dataset.choiceRevision);if(data.name_mode==='source')delete data.custom_title;try{await run('previews',data);location.reload();}catch{}});
document.getElementById('revise-import')?.addEventListener('click',async()=>{try{const result=await run('revise',{expected_revision:Number(flow.dataset.revision)});if(result.previous_choice){sessionStorage.setItem('workspace-choice:'+flow.dataset.flowId,JSON.stringify(result.previous_choice));}location.reload();}catch{}});
// Only non-sensitive form choices may survive a reload; OAuth tokens never enter storage.
if(preview){try{const key='workspace-choice:'+flow.dataset.flowId;const previous=JSON.parse(sessionStorage.getItem(key)||'null');sessionStorage.removeItem(key);if(previous){for(const name of ['sheet_id','name_mode','custom_title']){const node=preview.querySelector(`[name=${name}]`);if(node && previous[name]!=null)node.value=previous[name];}document.getElementById('name-options').hidden=!preview.querySelector('[name=sheet_id]').value;}}catch{}}
document.getElementById('confirm-import')?.addEventListener('submit',async event=>{event.preventDefault();const form=Object.fromEntries(new FormData(event.target));try{const result=await run('confirm',{confirm:true,preview_id:form.preview_id,existing_import_id:form.existing_import_id||null});location.assign(result.course_url);}catch{}});
document.getElementById('retry-import')?.addEventListener('click',async()=>{try{await run('retry');location.reload();}catch{}});
document.getElementById('cancel-import')?.addEventListener('click',async()=>{try{await run('cancel');location.assign(`/teacher/workspace/courses/${encodeURIComponent(course)}/lectures`);}catch{}});
if(flow?.dataset.status==='reading'){setInterval(async()=>{try{const state=await api(base);const button=document.getElementById('retry-import');if(button)button.disabled=!state.retryable;if(state.status!=='reading')location.reload();}catch(error){report(error);}},1000);}
// A source_pending link represents the teacher's earlier explicit Read request.
if(flow?.dataset.status==='source_pending' && (flow.dataset.sourceKind==='link' || flow.dataset.sourceSelected==='true'))read().catch(()=>{});

for(const button of document.querySelectorAll('[data-remove]'))button.addEventListener('click',async()=>{if(!window.confirm(`刪除「${button.dataset.title}」的全部版本？已發生的活動、回填歷史與雲端原檔會保留。`))return;button.disabled=true;try{await api(`/teacher/notes/courses/${encodeURIComponent(course)}/lectures/${encodeURIComponent(button.dataset.remove)}/remove`,{confirm:true});location.reload();}catch(error){report(error);button.disabled=false;}});
