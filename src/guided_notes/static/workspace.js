const main = document.querySelector('main');
export async function api(path, body) {
  const headers = {'Accept':'application/json'};
  const options = {headers, cache:'no-store'};
  if(body !== undefined){Object.assign(headers,{'Content-Type':'application/json','X-CSRF-Token':main.dataset.csrf});Object.assign(options,{method:'POST',body:JSON.stringify(body)});}
  const response = await fetch(path, options);
  const data = response.status === 204 ? {} : await response.json();
  if(!response.ok){const e=new Error(data.error?.message || data.error?.code || data.error || '操作未完成');e.code=data.error?.code || data.error;e.data=data;throw e;}
  return data;
}
export function report(error){document.getElementById('message').textContent=error.message;}
for(const [selector, path, destination] of [
  ['[data-create-course]','/teacher/courses',d=>`/teacher/workspace/courses/${encodeURIComponent(d.course_id)}`],
  ['[data-create-room]',`/teacher/courses/${encodeURIComponent(main.dataset.courseId)}/classrooms`,d=>`/teacher/workspace/courses/${encodeURIComponent(main.dataset.courseId)}/classrooms/${encodeURIComponent(d.classroom_id)}`]
]){document.querySelector(selector)?.addEventListener('submit',async event=>{event.preventDefault();const button=event.target.querySelector('button');button.disabled=true;try{const data=await api(path,Object.fromEntries(new FormData(event.target)));location.assign(destination(data));}catch(error){report(error);button.disabled=false;}});}
