// 捕获网页预置示例与图表状态，不调用真实模型评测。
const fs=require('fs'),path=require('path');const {chromium}=require('playwright');const root=path.resolve(__dirname,'..');
(async()=>{const b=await chromium.launch({channel:'chrome',headless:true});
async function setup(id){const p=await b.newPage({viewport:{width:1440,height:1080},deviceScaleFactor:1.5});await p.goto('https://cognition.com/blog/'+id,{waitUntil:'networkidle'});for(let i=0;i<8;i++){const x=p.getByRole('button').filter({hasText:/Show/}).first();if(!await x.count())break;await x.click();await p.waitForLoadState('networkidle')};fs.mkdirSync(path.join(root,id,'states'),{recursive:true});return p}
async function save(p,id,name,el){const dir=path.join(root,id,'states');await el.scrollIntoViewIfNeeded();await el.screenshot({path:path.join(dir,name+'.png'),animations:'disabled'});fs.writeFileSync(path.join(dir,name+'.txt'),await el.innerText());fs.writeFileSync(path.join(dir,name+'.html'),await el.evaluate(e=>e.outerHTML));console.log(id,name)}
let id='swe-2',p; if(!process.env.FRONTIER_ONLY){p=await setup(id);
await p.locator('[data-step]').first().waitFor();const panel=p.getByRole('button',{name:/Example trajectories/}).locator('..');
for(const task of ['one','matplotlib','Mattermost']){await p.getByRole('button',{name:task,exact:true}).click();await save(p,id,'trajectory-'+task,panel)}
// 记录工具分布菜单的实际可选指标，逐项截图。
await p.getByRole('button',{name:'Steps per run',exact:true}).click();fs.writeFileSync(path.join(root,id,'states','metric-menu.txt'),await p.locator('body').innerText());
console.log('swe2menu',await p.getByRole('button').allInnerTexts());await p.close();
id='swe-1-7';p=await setup(id);
for(const [kind,names] of [['cot',['protonmail/webclients-b387b241','ansible/ansible-1a4644ff','future-architect/vuls-5af1a227']],['trajectory',['fizzy-implement-authorization','matplotlib-bug-stackplot','uv-frozen-uv-lock-check-fails']]]){
 const panel=p.getByRole('button',{name:kind==='cot'?/Condensed chain-of-thought/:/Example trajectories/}).locator('..');
 for(const name of names){await p.getByRole('button',{name,exact:true}).click();await save(p,id,kind+'-'+name.replaceAll('/','_'),panel)}
}await p.close();
id='frontier-code';p=await setup(id);await save(p,id,'prompt-comparison',p.getByRole('button',{name:/Compare example prompts/}).locator('..'));
for(const model of ['Opus 4.8','GPT-5.5']){await p.getByRole('button',{name:model,exact:true}).click();await p.getByRole('button',{name:'Run eval',exact:true}).click();await p.getByRole('button',{name:'Run again',exact:true}).waitFor();const panel=p.locator('figure').filter({has:p.getByRole('button',{name:'Run again',exact:true})});await save(p,id,'eval-'+model.replaceAll(' ','-'),panel);fs.writeFileSync(path.join(root,id,'states','buttons-'+model+'.json'),JSON.stringify(await panel.getByRole('button').allInnerTexts(),null,2))}await p.close();
}id='frontier-code-1.1';p=await setup(id);await save(p,id,'fair-internet-use-prompt',p.getByRole('button',{name:/View the fair-internet/}).locator('..'));
for(const [name,key] of [['Flagged: opened the PR diff','flagged'],['Allowed: read the docs','allowed']]){await p.getByRole('button',{name,exact:true}).click();const panel=p.locator('figure').filter({has:p.getByRole('button',{name,exact:true})});await save(p,id,'playback-'+key+'-initial',panel);if(await p.getByRole('button',{name:'Play',exact:true}).count())await p.getByRole('button',{name:'Play',exact:true}).click();await p.getByRole('button',{name:'Replay',exact:true}).waitFor({timeout:45000});await save(p,id,'playback-'+key+'-complete',panel)}
await p.close();await b.close()})().catch(e=>{console.error(e);process.exitCode=1});
