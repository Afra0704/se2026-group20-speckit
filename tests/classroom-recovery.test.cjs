const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('src/guided_notes/static/classroom.js', 'utf8');
function node() { return {disabled:false, value:'', children:[], dataset:{}, textContent:'',
  append(x){this.children.push(x);}, replaceChildren(){this.children=[];}, addEventListener(){}, querySelectorAll(){return[];}}; }
async function run(mode) {
  const ids = Object.fromEntries(['courses','classrooms','catalogs','notes','code','activities','results','state','message','close-room'].map(id=>[id,node()]));
  const buttons = () => ids.activities.children.flatMap(line=>line.children.filter(child=>child.tag==='button'));
  let stateFailure=false, historyFailure=mode==='history', historyReads=0, delayNext=false, release;
  const context=vm.createContext({
    document:{querySelector:selector=>selector==='main'?({dataset:{role:'teacher',csrf:'test'},querySelectorAll:buttons}):null,
      getElementById:id=>ids[id],addEventListener(){},createElement(tag){return Object.assign(node(),{tag});}},
    localStorage:{getItem:()=>null,setItem(){},removeItem(){}}, window:{addEventListener(){}},setInterval(){},
    Option:function(text,value){this.text=text;this.value=value;},
    fetch:async path=>{
      let data;
      if(path==='/teacher/courses') data={courses:[]};
      else if(path.endsWith('/state')) {
        if(stateFailure){stateFailure=false;throw new Error('temporary network failure');}
        data={classroom_id:'room',classroom_state:'OPEN',state_version:1,activity:null};
      } else if(path.endsWith('/activities')) {
        historyReads++;
        if(historyFailure){historyFailure=false;throw new Error('temporary history failure');}
        data={activities:[{activity_id:'prepared-'+historyReads,title:'Lecture-'+historyReads,phase:'PREPARING',created_at:'now'}]};
        if(delayNext){delayNext=false;await new Promise(resolve=>{release=resolve;});}
      } else throw new Error(path);
      return {ok:true,headers:{get:()=> 'application/json'},json:async()=>data};
    }
  });
  vm.runInContext(source,context);
  await new Promise(setImmediate);
  vm.runInContext('setRoom("room")',context);
  await vm.runInContext('refresh()',context);
  if(mode==='state') {
    assert.equal(buttons()[0].disabled,false);
    stateFailure=true;
    await vm.runInContext('refresh()',context);
    assert.equal(buttons()[0].disabled,true);
  }
  if(mode==='stale') {
    delayNext=true;
    const old = vm.runInContext('activityList("room")',context);
    await vm.runInContext('activityList("room")',context);
    release(); await old;
    assert.match(ids.activities.children[0].textContent,/Lecture-3/);
  } else {
    await vm.runInContext('refresh()',context);
    assert.equal(ids['close-room'].disabled,false);
    assert.equal(buttons()[0].disabled,false);
    assert.equal(historyReads,2);
  }
}
(async()=>{for(const mode of ['state','history','stale']) await run(mode);
  console.log('Teacher network recovery, history retry and stale history response: passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
