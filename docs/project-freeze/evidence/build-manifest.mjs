import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const root='D:/Qiuizi/project/yijing';
const dir=path.join(root,'docs/project-freeze');
const ev=path.join(dir,'evidence');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const git=read(path.join(ev,'git-audit.json'));
const audit=read(path.join(ev,'audit-time.json'));
const releases=read(path.join(ev,'releases.json'));
const prs=read(path.join(ev,'pull-requests.json'));
const openPrs=prs.filter(p=>p.state==='open');
const openIssues=read(path.join(ev,'open-issues.json'));
const artifacts=read(path.join(ev,'artifacts.json')).artifacts;
const runs=read(path.join(ev,'recent-runs.json')).workflow_runs;
const cancelled=read(path.join(ev,'cancelled-production-run.json'));
const ident=read(path.join(ev,'public-identities.json'));
const preserved=fs.existsSync(path.join(ev,'remote-preservation.json'))?read(path.join(ev,'remote-preservation.json')):null;
const pick=(arr,n)=>arr.find(x=>x.number===n);
const art=id=>artifacts.find(a=>a.id===id);
const run=id=>runs.find(r=>r.id===id);
const release=t=>releases.find(r=>r.tag_name===t);
const key=p=>ident.identities.find(i=>i.purpose===p);
const docs=['README.md','PROJECT-STATUS.md','RELEASE-HISTORY.md','QA-ACCEPTANCE.md','SECURITY-INVENTORY.md','KNOWN-ISSUES.md','RECOVERY-GUIDE.md','CLEANUP-REPORT.md'].map(f=>({path:'docs/project-freeze/'+f,sha256:sha(path.join(dir,f)),bytes:fs.statSync(path.join(dir,f)).size}));
const qa=[
 {id:'v332-installer-missing-investigation',status:'FAIL',severity:'P0',evidence:['docs/qa/post-release-qa-3.3.2.md'],note:'Official v3.3.2 installer bda356af... lacks main executable'},
 {id:'v333-candidate-independent-verification',status:'PASS',evidence:['.qa-work/v3.3.3/reverify-live/reverify-summary.json','.qa-work/v3.3.3/ACCEPTANCE-REPORT.md'],note:'ephemeral candidate signature, not production'},
 {id:'v333-nsis-contents',status:'PASS',evidence:['.qa-work/v3.3.3/evidence/candidate-nsis-contents.json']},
 {id:'v333-official-install-launch-gui-uninstall',status:'PASS',evidence:['.qa-work/v3.3.3/runner-evidence2/extracted/result.json'],run_id:42032346331,artifact_id:13415419891},
 {id:'sidecar-api',status:'PASS',evidence:['.qa-work/v3.3.3/evidence/api-sidecar-results.json'],note:'37/37 ok'},
 {id:'webview2',status:'PASS',evidence:['.qa-work/v3.3.3/runner-evidence2/extracted/result.json'],note:'existing runtime only'},
 {id:'webview2-clean-machine-missing-runtime',status:'NOT_RUN',evidence:[]},
 {id:'database-migration-matrix',status:'NOT_RUN',evidence:['.qa-work/v3.3.3/evidence/api-sidecar-results.json'],note:'only schema_migrations count equality'},
 {id:'sqlite-backup-restore',status:'PASS',evidence:['.qa-work/v3.3.3/inapp-332/reconstruct-332/evidence/failures-timeline.txt','.qa-work/v3.3.2/evidence/recovery-results.json']},
 {id:'dpapi-same-user',status:'PASS',evidence:['.qa-work/v3.3.3/evidence/api-sidecar-results.json','.qa-work/v3.3.3/inapp-332/reconstruct-332/evidence/upgrade-after-db.json']},
 {id:'dpapi-cross-user',status:'NOT_RUN',evidence:[]},
 {id:'auto-update',status:'PASS',evidence:['.qa-work/v3.3.3/ACCEPTANCE-REPORT.md','.qa-work/v3.3.3/inapp-332/reconstruct-332/evidence/failures-timeline.txt']},
 {id:'inapp-332-to-333-reconstructed-baseline',status:'PASS',evidence:['.qa-work/v3.3.3/inapp-332/reconstruct-332/evidence/upgrade-timeline.txt','.qa-work/v3.3.3/inapp-332/reconstruct-332/evidence/final-timeline.txt','.qa-work/v3.3.3/inapp-332/reconstruct-332/evidence/baseline-install.json'],scope:'reconstructed QA baseline, temporary QA key, local HTTP; NOT production'},
 {id:'official-331-to-333-overlay-upgrade',status:'PASS',evidence:['.qa-work/v3.3.3/upgrade-evidence3/upgrade-result.json'],run_id:42033479080},
 {id:'unsigned-dry-run',status:'PASS',evidence:['.qa-work/v3.3.3/ACCEPTANCE-REPORT.md'],run_id:42032014347},
 {id:'production-sign-dry-run',status:'CANCELLED_BY_FREEZE',evidence:['docs/project-freeze/evidence/cancelled-production-run.json'],run_id:42033806115},
 {id:'production-signed-332-to-333-inapp-upgrade',status:'NOT_RUN',evidence:[]},
 {id:'historical-v332-updaterqa-baseline',status:'BLOCKED',evidence:['.qa-work/v3.3.3/inapp-332/BLOCKED-report.md'],note:'never found; replaced by reconstruction'},
 {id:'old-qa-upgrade-2026-10-27',status:'STALE',evidence:['docs/updater/qa-upgrade-report.md']}
];
const manifest={
  schema:'yijing-project-freeze-manifest/1',
  project:{name:'Yijing Workbench',repository:'Qiuizi/yijing-workbench-public'},
  freeze:{time_local:audit.observed_at,completed_at:new Date().toISOString(),timezone:'Asia/Shanghai',status:'PROJECT_FROZEN_WITH_WARNINGS',phase_reached:'Phase 6 completed; no development resumed'},
  git:{head:git.head,main_commit_date:'2026-11-05T02:31:43Z',main_commit_subject:'release: prepare v3.3.3 installer packaging fix (#62)',branch:'main',ahead_behind:'+0 -0',local_branches:26,remote_tracking_refs:52,remote_branches:git.remote_refs.filter(function(r){return r.indexOf('refs/heads/')>0}).length,tags:['v3.2.2','v3.3.0','v3.3.1','v3.3.2'],worktrees:git.worktrees.length,substantive_uncommitted_changes:0,status_flagged_paths:['frontend/src-tauri/Cargo.toml (stat-dirty; byte-identical to HEAD)'],untracked_directories:['.workbuddy/','docs/review/ui-audit/','docs/review/ui-audit-node-modules-backup/','docs/review/ui-audit-vite-cache-backup/','docs/project-freeze/']},
  releases:{latest:release('v3.3.2')?{tag:'v3.3.2',id:release('v3.3.2').id,published_at:release('v3.3.2').published_at,html_url:release('v3.3.2').html_url,assets:release('v3.3.2').assets.map(a=>({name:a.name,size:a.size,digest:a.digest}))}:null,public_tags:['v3.2.2','v3.3.0','v3.3.1','v3.3.2'],v333_public_release:false,v333_tag:false,website_serves_version:'3.3.2'},
  pull_requests:{checked:[61,62,51,56,60].map(n=>{const p=pick(prs,n);return {number:n,state:p.state,merged_at:p.merged_at,head_sha:p.head.sha,title:p.title}}),open:openPrs.map(p=>({number:p.number,title:p.title})),open_issues:openIssues.map(i=>({number:i.number,title:i.title}))},
  artifacts:{candidate_13383072964:art(13383072964)?{id:13383072964,name:art(13383072964).name,digest:art(13383072964).digest,size:art(13383072964).size_in_bytes,expired:art(13383072964).expired,expires_at:art(13383072964).expires_at,run_id:art(13383072964).workflow_run.id}:null,production_staging_13418007574:art(13418007574)?{id:13418007574,name:art(13418007574).name,digest:art(13418007574).digest,size:art(13418007574).size_in_bytes,expires_at:art(13418007574).expires_at}:null,unsigned_dry_run_staging_13417456279:art(13417456279)?{id:13417456279,digest:art(13417456279).digest}:null,signed_v332_13160435971:art(13160435971)?{id:13160435971,digest:art(13160435971).digest}:null,total_observed:artifacts.length,local_preservation:{root:'.qa-work/project-freeze-20261106/remote-archives',status:preserved?`${preserved.files.filter(f=>f.status==='VERIFIED').length}/${preserved.total} verified`:'in_progress'}},
  key_runs:{candidate_build_41955823250:run(41955823250)?{id:41955823250,conclusion:run(41955823250).conclusion,head_sha:run(41955823250).head_sha}:null,unsigned_dry_run_42032014347:run(42032014347)?{id:42032014347,conclusion:run(42032014347).conclusion,head_sha:run(42032014347).head_sha}:null,production_sign_dry_run_42033806115:{id:cancelled.id,raw_status:cancelled.status,conclusion:cancelled.conclusion,head_sha:cancelled.head_sha,updated_at:cancelled.updated_at,cancelled_by:'project freeze'},qa_acceptance_runs:[42031937030,42032346331,42032895209,42033479080,42042680743,42042741115].map(id=>run(id)?{id,conclusion:run(id).conclusion}:{id,conclusion:'unknown'})},
  qa:{summary:'QA acceptance is complete for the v3.3.3 candidate build under temporary candidate signing; in-app 3.3.2->3.3.3 upgrade passed only with a reconstructed QA baseline, temporary QA key and local HTTP; production-signed path NOT_RUN.',in_app_updater_qa_completed:true,not_completed_code_applied:false,matrix:qa,evidence_inventory:'docs/project-freeze/evidence/qa-inventory.json',evidence_hashes:'docs/project-freeze/evidence/qa-critical-hashes.json'},
  security:{signing_backup:'SIGNING_BACKUP_UNVERIFIED',passphrase_separation:'UNVERIFIED',private_content_read:false,production_private_key:{path:'C:/Users/123/.tauri/yijing-release/yijing-release.key',exists:true,bytes:348,sha256:'00370433a15fab5d3eb8d3d2f6e02a4664952f0b7d86db83a75bdb05590c5354'},production_public_key:{path:'C:/Users/123/.tauri/yijing-release/yijing-release.key.pub',bytes:152,key_id_bytes_hex:key('production-embedded').key_id_bytes_hex,minisign_display_key_id:key('production-embedded').minisign_display_key_id,public_text_sha256:key('production-embedded').public_text_sha256,repository_fingerprint:key('production-embedded').repository_fingerprint,matches_embedded:ident.production_public_file_matches_embedded},candidate_key:{key_id_bytes_hex:key('candidate-ephemeral-41955823250').key_id_bytes_hex,minisign_display_key_id:key('candidate-ephemeral-41955823250').minisign_display_key_id,repository_fingerprint:key('candidate-ephemeral-41955823250').repository_fingerprint},github_release_environment:{exists:true,required_reviewer:'Qiuizi',can_admins_bypass:false,branch_policy:['main'],secret_names:['TAURI_SIGNING_PRIVATE_KEY','TAURI_SIGNING_PRIVATE_KEY_PASSWORD','TAURI_UPDATER_PUBKEY']},repository_secret_count:0,actions_default_permission:'read',sha_pinning_required:false,evidence:'docs/project-freeze/evidence/public-identities.json'},
  unfinished:[
   'Republish a working official installer (v3.3.2 P0)',
    'Publish v3.3.3 with production signing (verify signature key id matches SECURITY-INVENTORY)',
   'Production-signed 3.3.2->3.3.3 in-app upgrade verification',
   'Verify offline signing backup and passphrase separation',
   'Database migration matrix, DPAPI cross-user, clean-machine WebView2, AI success path',
   'Enable requireSignedVersion; localize updater errors; fix aboutVersion display'
  ],
  warnings:['SIGNING_BACKUP_UNVERIFIED','v3.3.2 official installer P0','v3.3.3 not released; production signing cancelled at freeze','production-signed upgrade NOT_RUN'],
  documents:docs,
  evidence_directory:'docs/project-freeze/evidence/',
  next_action:'Wait for the maintainer to request resumption; do not resume development automatically.'
};
fs.writeFileSync(path.join(dir,'FREEZE-MANIFEST.json'),JSON.stringify(manifest,null,2)+'\n');
console.log(JSON.stringify({documents:docs,preservation:manifest.artifacts.local_preservation.status}));


