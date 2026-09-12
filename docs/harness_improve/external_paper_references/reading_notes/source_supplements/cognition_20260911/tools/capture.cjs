// 仅采集公开网页；独立浏览器上下文不使用用户登录信息。
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..');
const pages=[['specforge-v0-3','https://www.lmsys.org/blog/2026-08-04-specforge-v0-3'],['swe-2','https://cognition.com/blog/swe-2'],['frontier-code','https://cognition.com/blog/frontier-code'],['frontier-code-1.1','https://cognition.com/blog/frontier-code-1.1'],['swe-1-7','https://cognition.com/blog/swe-1-7'],['swe-1-6-preview','https://cognition.com/blog/swe-1-6-preview'],['swe-check','https://cognition.com/blog/swe-check-10x-faster'],['swe-grep','https://cognition.com/blog/swe-grep'],['swe-1-5','https://cognition.com/blog/swe-1-5']];
(async()=>{
const browser=await chromium.launch({channel:'chrome',headless:true});
for(const [id,url] of pages.filter(([id])=>!process.env.IDS||process.env.IDS.split(',').includes(id))){
 const dir=path.join(root,id);fs.mkdirSync(path.join(dir,'visuals'),{recursive:true});fs.mkdirSync(path.join(dir,'assets'),{recursive:true});
 const context=await browser.newContext({viewport:{width:1440,height:1080},deviceScaleFactor:1.5}); const p=await context.newPage();
 const errors=[],pending=[],scripts=[];
 p.on('response',r=>{if(r.url().startsWith('https://cognition.com/_next/static/chunks/'))pending.push((async()=>{try{const body=await r.body();const name=crypto.createHash('sha256').update(body).digest('hex').slice(0,16)+'.js';const d=path.join(root,'web_scripts');fs.mkdirSync(d,{recursive:true});fs.writeFileSync(path.join(d,name),body);scripts.push({url:r.url(),file:'../web_scripts/'+name});}catch(e){}})())});
 try{
 const response=await p.goto(url,{waitUntil:'networkidle',timeout:45000});fs.writeFileSync(path.join(dir,'original.html'),await response.text());
 await p.locator('h1').first().waitFor(); await p.evaluate(()=>document.fonts.ready);
 // 只点击已观察到的 Show 展开按钮，不执行外部训练或真实评测。
 const expanded=[];
 for(let k=0;k<20;k++){const b=p.getByRole('button').filter({hasText:/Show/}).first();if(!await b.count())break;const label=await b.innerText();await b.click();expanded.push(label);await p.evaluate(()=>new Promise(requestAnimationFrame));}
 const meta=await p.evaluate(()=>({title:document.title,url:location.href,headings:[...document.querySelectorAll('h1,h2,h3,h4')].map(e=>e.innerText),buttons:[...document.querySelectorAll('button')].map(e=>e.innerText),links:[...document.querySelectorAll('main a,article a')].map(e=>({text:e.innerText,url:e.href})),math:[...document.querySelectorAll('annotation[encoding="application/x-tex"]')].map(e=>e.textContent),images:[...document.images].map(e=>({src:e.currentSrc||e.src,alt:e.alt})),inputs:[...document.querySelectorAll('input,select')].map(e=>({type:e.type,value:e.value,min:e.min,max:e.max,html:e.outerHTML}))}));
 meta.captured_at=new Date().toISOString();meta.expanded=expanded;meta.visuals=[];
 fs.writeFileSync(path.join(dir,'expanded.txt'),await p.locator('body').innerText());fs.writeFileSync(path.join(dir,'readable.txt'),await p.evaluate(()=>{const x=document.body.cloneNode(true);for(const e of x.querySelectorAll('.katex')){const a=e.querySelector('annotation[encoding="application/x-tex"]');if(a)e.replaceWith(document.createTextNode(' $'+a.textContent+'$ '));}x.querySelectorAll('script,style,nav,header,footer').forEach(e=>e.remove());return x.textContent}));fs.writeFileSync(path.join(dir,'equations.tex'),meta.math.join('\n\n% ---\n\n'));fs.writeFileSync(path.join(dir,'expanded.html'),await p.content());
 const svg=p.locator('svg');let n=0;
 for(let i=0;i<await svg.count();i++){const el=svg.nth(i),box=await el.boundingBox();if(!box||box.width<250||box.height<100)continue;n++;const f='visuals/chart-'+String(n).padStart(2,'0');await el.scrollIntoViewIfNeeded();const figure=el.locator('xpath=ancestor::figure[1]');await (await figure.count()?figure:el).screenshot({path:path.join(dir,f+'.png'),animations:'disabled'});fs.writeFileSync(path.join(dir,f+'.svg'),await el.evaluate(e=>e.outerHTML));const info=await el.evaluate(e=>{let a=e;for(let i=0;i<4&&a.parentElement;i++)a=a.parentElement;return {svg_text:e.textContent,nearby_text:a.innerText.slice(0,5000)}});meta.visuals.push({file:f+'.png',...info});}
 const imgs=p.locator('img');let m=0;
 for(let i=0;i<await imgs.count();i++){const el=imgs.nth(i),box=await el.boundingBox();if(!box||box.width<150)continue;m++;const info=await el.evaluate(e=>({src:e.currentSrc||e.src,alt:e.alt,nearby_text:e.parentElement.parentElement.innerText.slice(0,1200)}));let f='visuals/image-'+String(m).padStart(2,'0');try{await el.scrollIntoViewIfNeeded();await el.screenshot({path:path.join(dir,f+'.png')});const r=await context.request.get(info.src);const ext=(r.headers()['content-type']||'').includes('svg')?'svg':(r.headers()['content-type']||'').includes('png')?'png':(r.headers()['content-type']||'').includes('webp')?'webp':'bin';fs.writeFileSync(path.join(dir,'assets',String(m).padStart(2,'0')+'.'+ext),await r.body());meta.visuals.push({file:f+'.png',original_file:'assets/'+String(m).padStart(2,'0')+'.'+ext,...info});}catch(e){errors.push(String(e))}}
 const cdp=await context.newCDPSession(p);const snapshot=await cdp.send('Page.captureSnapshot',{format:'mhtml'});fs.writeFileSync(path.join(dir,'expanded.mhtml'),snapshot.data);
 await Promise.allSettled(pending);meta.scripts=scripts;meta.errors=errors;fs.writeFileSync(path.join(dir,'capture.json'),JSON.stringify(meta,null,2));console.log(id,JSON.stringify({charts:n,images:m,expanded,buttons:meta.buttons,errors}));
 }catch(e){console.log(id,'FAILED',String(e));fs.writeFileSync(path.join(dir,'error.txt'),String(e))}
 await context.close();
}
await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1});
