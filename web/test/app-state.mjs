// Exercise the actual page controller with a controlled worker and minimal DOM.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const nodes = new Map();
function element(id = '') {
  return { id, hidden: true, value: '', files: [], listeners: {},
    classList: {add(){},remove(){},toggle(){}},
    addEventListener(n, f) { (this.listeners[n] ||= []).push(f); },
    emit(n, extra = {}) { for (const f of this.listeners[n] || []) f.call(this, {preventDefault(){}, target:this, ...extra}); },
    appendChild(){}, removeAttribute(){}, focus(){}, remove(){}, click(){} };
}
for (const id of ['form','table','profile','gff3','genome','clear-genome','drop','run','status-text','progress','results','report','verdict','results-title','engine-version','gff3-chosen','genome-chosen']) nodes.set(id, element(id));
nodes.get('form').elements = {header:{value:'auto'}};
let ready, worker;
const downloads=[];
const button=element(); button.getAttribute=()=> 'json';
const document={getElementById:id=>nodes.get(id),addEventListener:(_,f)=>{ready=f;},querySelectorAll:()=>[button],body:{appendChild:a=>downloads.push(a)},createElement:()=>element()};
class Worker {constructor(){worker=this;} postMessage(m){this.sent=m;} deliver(m){this.onmessage({data:m});}}
const url = class extends URL {}; url.createObjectURL=()=> 'blob:test'; url.revokeObjectURL=()=>{};
vm.runInNewContext(fs.readFileSync(new URL('../app.js',import.meta.url),'utf8'), {document, Worker, URL:url, Blob, location:{href:'https://example.org/'},fetch:async u=>({ok:true,json:async()=>({}),text:async()=>''}),setTimeout(){}});
ready();
await new Promise(resolve=>setImmediate(resolve));
worker.deliver({type:'ready',facts:{tables:[],profiles:[]}});
const file=name=>({name,size:1});
function select(name){nodes.get('gff3').files=[file(name)];nodes.get('gff3').emit('change');}
const result={ok:true,valid:true,summary:'valid',seconds:1,html:'report A',json:'{}'};
select('A.gff3'); nodes.get('form').emit('submit');
assert.equal(worker.sent.file.name,'A.gff3');
select('B.gff3'); worker.deliver({type:'result',result});
assert.equal(nodes.get('results').hidden,true);
button.emit('click'); assert.equal(downloads.length,0);
nodes.get('form').emit('submit'); worker.deliver({type:'result',result});
assert.equal(nodes.get('verdict').textContent,'B.gff3: valid');
button.emit('click'); assert.equal(downloads[0].download,'B.gff3.report.json');
select('C.gff3'); assert.equal(nodes.get('results').hidden,true);
for (const id of ['table','profile','genome']) {
  nodes.get('form').emit('submit');
  nodes.get(id).emit('change');
  worker.deliver({type:'result',result});
  assert.equal(nodes.get('results').hidden,true,id);
}
nodes.get('form').emit('submit');
nodes.get('form').emit('change',{target:{name:'header'}});
worker.deliver({type:'result',result});
assert.equal(nodes.get('results').hidden,true);
console.log('Page controller attribution and input invalidation checks passed');
