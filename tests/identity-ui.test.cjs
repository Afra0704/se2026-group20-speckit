const test = require('node:test');
const assert = require('node:assert/strict');
const {label,render} = require('../src/guided_notes/static/identity.js');
test('nullable identity display has safe fallback',()=>{assert.equal(label(null),'Google 教師');assert.equal(label({email:'a@example.test'}),'a@example.test');});
test('identity rendering uses plain text',()=>{const node={};render(node,{display_name:'<script>sentinel</script>'});assert.equal(node.textContent,'<script>sentinel</script>');assert.equal(node.innerHTML,undefined);});
const fs=require('node:fs');
const path=require('node:path');
function template(name){return fs.readFileSync(path.join(__dirname,'../src/guided_notes/templates/identity',name+'.html'),'utf8');}
test('home provides separate student and teacher entrances',()=>{const html=template('home');assert.match(html,/我是老師/);assert.match(html,/我是學生/);assert.match(html,/url_for\('student_entry'\)/);assert.match(html,/url_for\('teacher.page'\)/);});
test('Google login uses CSRF POST and contains no password field',()=>{const html=template('login');assert.match(html,/method="post"/);assert.match(html,/google_login.start/);assert.match(html,/name="csrf_token"/);assert.doesNotMatch(html,/type="password"/);assert.match(html,/google_error_message/);});
test('identity offers logout and switch while Sheets consent belongs to import',()=>{const html=template('teacher');for(const endpoint of ['google_login.logout','google_login.start'])assert.ok(html.includes(endpoint));assert.equal((html.match(/name="csrf_token"/g)||[]).length,2);assert.doesNotMatch(html,/google_login\.connect/);assert.doesNotMatch(html,/\|safe/);});
