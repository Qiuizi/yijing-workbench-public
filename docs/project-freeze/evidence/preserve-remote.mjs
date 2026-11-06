import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {Readable} from 'node:stream';
import {pipeline} from 'node:stream/promises';
const root='D:/Qiuizi/project/yijing';
const ev=path.join(root,'docs/project-freeze/evidence');
const out=path.join(root,'.qa-work/project-freeze-20261106/remote-archives');
fs.mkdirSync(out,{recursive:true});
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const artifacts=read(path.join(ev,'artifacts.json')).artifacts;
const releases=read(path.join(ev,'releases.json'));
const token=execFileSync('C:/Program Files/GitHub CLI/gh.exe',['auth','token'],{encoding:'utf8',windowsHide:true}).trim();
const jobs=[...artifacts.filter(a=>!a.expired).map(a=>({kind:'actions-artifact',id:a.id,name:a.name,url:a.archive_download_url,digest:a.digest,size:a.size_in_bytes,run:a.workflow_run,expires_at:a.expires_at,file:path.join(out,`artifact-${a.id}.zip`)})),...releases.flatMap(r=>r.assets.map(a=>({kind:'release-asset',id:a.id,release:r.tag_name,name:a.name,url:a.url,digest:a.digest,size:a.size,file:path.join(out,r.tag_name,a.name)})))];
const results=[];
function save(){fs.writeFileSync(path.join(ev,'remote-preservation.json'),JSON.stringify({observed_at:new Date().toISOString(),archive_root:out,total:jobs.length,completed:results.length,files:results},null,2));}
async function hash(file){const h=crypto.createHash('sha256');for await(const chunk of fs.createReadStream(file))h.update(chunk);return h.digest('hex');}
let index=0;
async function worker(){while(index<jobs.length){const j=jobs[index++];fs.mkdirSync(path.dirname(j.file),{recursive:true});let row;
try{if(!fs.existsSync(j.file)){const response=await fetch(j.url,{headers:{Authorization:`Bearer ${token}`,Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'},signal:AbortSignal.timeout(900000)});if(!response.ok)throw new Error(`HTTP ${response.status}`);await pipeline(Readable.fromWeb(response.body),fs.createWriteStream(j.file,{flags:'wx'}));}
const sha=await hash(j.file);const size=fs.statSync(j.file).size;row={...j,url:undefined,sha256:sha,actual_size:size,status:size===j.size&&(!j.digest||j.digest===`sha256:${sha}`)?'VERIFIED':'DIGEST_OR_SIZE_MISMATCH'};
}catch(error){row={...j,url:undefined,status:'FAILED',error:error.message.replace(/https?:\/\/\S+/g,'[URL]')};}
results.push(row);save();console.log(`${results.length}/${jobs.length} ${j.kind} ${j.id} ${row.status}`);}}
await Promise.all(Array.from({length:4},worker));save();
console.log(JSON.stringify({total:jobs.length,verified:results.filter(x=>x.status==='VERIFIED').length,failed:results.filter(x=>x.status!=='VERIFIED').length}));

