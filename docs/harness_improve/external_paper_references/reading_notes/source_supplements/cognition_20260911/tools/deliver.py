from pathlib import Path
import json,zipfile,hashlib,re
root=Path(__file__).resolve().parent.parent;delivery=root/'delivery';delivery.mkdir(exist_ok=True)
groups=[('01_SWE2_and_baselines',['swe-2'],['opo_2505.23585v2','greensmith_2004','kool_2019_POSTER_ONLY']),('02_SWE17_16_15',['swe-1-7','swe-1-6-preview','swe-1-5'],[]),('03_FrontierCode',['frontier-code','frontier-code-1.1'],[]),('04_DSpark',[],['dspark_2607.05147v1']),('05_SpecForge',['specforge-v0-3'],['specforge_2603.18567']),('06_SWECheck_and_SWEgrep',['swe-check','swe-grep'],[])]
results=[]
for name,topics,papers in groups:
 entries=set();notes=['# '+name+'：来源补充附件','','采集于 2026-09-11。请先读对应原文，再用这些附件补充图表、公式和交互示例。它们不构成精读结论，也不代表训练复现。阅读应覆盖完整正文、附录和图表，不要只围绕资料补缺项作答。','','## 阅读入口','']
 for topic in topics:
  d=root/topic;j=json.loads((d/'capture.json').read_text());notes += ['### '+j['title'],'','原始网页：'+j['url'],'',f'- [{topic}/reading_text.md]({topic}/reading_text.md)：网页提取正文。',f'- [{topic}/visual_supplement.pdf]({topic}/visual_supplement.pdf)：图表截图 PDF；逐页文件映射见 [{topic}/VISUAL_INDEX.md]({topic}/VISUAL_INDEX.md)。']
  for file in ['reading_text.md','visual_supplement.pdf','VISUAL_INDEX.md','capture.json','equations.tex']:entries.add(d/file)
  for v in j['visuals']:
   if v.get('src','').startswith('https://cognition.com/_next/image?'):continue
   entries.add(d/v['file']);svg=(d/v['file']).with_suffix('.svg')
   if svg.exists():entries.add(svg)
   if v.get('original_file'):entries.add(d/v['original_file'])
  entries.update((d/'original_assets').glob('*'))
  for sub in ['states','embedded']:
   for f in (d/sub).glob('*'):
    if f.suffix in ['.txt','.json','.png','.html']:entries.add(f)
   if (d/sub).exists():notes.append(f'- `{topic}/{sub}/`：'+('交互状态截图与文本。' if sub=='states' else '官网脚本中的完整示例；先看 manifest.json。'))
  if (d/'embedded/manifest.json').exists():
   for x in json.loads((d/'embedded/manifest.json').read_text()):entries.add((d/'embedded'/x['source_script']).resolve())
  p=root/'public_data/data'/topic
  if p.exists():entries.update(p.glob('*.json'));notes.append(f'- `public_data/data/{topic}/`：官网公开 JSON 原文件。')
  notes.append('')
 for paper in papers:
  for ext in ['.pdf','.txt']:entries.add(root/'papers'/(paper+ext))
  notes.append(f'- [{paper}.pdf](papers/{paper}.pdf)'+('：**仅作者海报，不能代替全文。**' if 'POSTER_ONLY' in paper else '：原始论文 PDF；同名 TXT 是布局文本提取。'))
 if papers:entries.add(root/'papers/validation.json');entries.add(root/'papers/downloads.json')
 if name.startswith('05'):
  entries.update((root/'specforge-code').glob('*'));notes += ['','代码固定在 `3d64e7a61f5fcc7f7d78ba6164c881f831943947`，详见 `specforge-code/revision.json`；这是采集时 main，不能当作论文/v0.3 发布原始提交。']
 if name.startswith('01'):notes += ['','## SWE-2 特别说明','','优先读 public_data/data/swe-2/figures.json（KL、接受率、散点）与 trajectories.json（12 条网页展示轨迹）。坐标只有相对刻度时，不能把内部坐标当作实际训练 step。','基线来源的唯一未补齐项是 Kool et al. 2019 全文：OpenReview 验证未通过，作者 Drive 链接失效。POSTER_ONLY 是作者海报。OPO 与 Greensmith 全文可读。']
 if name.startswith('02'):notes += ['','1.7 的 embedded/array-139353.json 包含 3 个 CoT 示例；array-151019.json 包含 3 个轨迹示例。网页内部字段 swe2 对应页面的 SWE-1.7 栏，不能仅凭字段名认定为 SWE-2。']
 if name.startswith('03'):notes += ['','## 交互示例入口','','FrontierCode：embedded/array-576.json 是 10 项 rubric；array-2002.json 是两模型的 patch 与评分，每模型 8 个文件、10 项结果。','FrontierCode 1.1：states/fair-internet-use-prompt.txt 是完整展开提示；embedded/array-2876.json 包含 14 步 flagged 示例与 12 步 allowed 示例。','Run eval 是网页播放预置数据的动画，本次没有运行真实评测。截图中的滚动框只显示部分内容，完整 patch / 步骤请看 JSON。']
 if name.startswith('06'):notes += ['','Check 的四张公式为 visuals/image-04.png 至 image-07.png；grep 的重要性权重与 loss 公式为 visuals/image-06.png 与 image-07.png。original_assets/ 保存去掉 CDN 缩放参数的原始图片；GIF 截图不代表整个动画，原始 GIF 已保留。']
 notes+=['','## 使用边界','','截图 PDF 是本次制作的视觉附件，不是作者发布的 PDF。网页公开的展示轨迹不等于完整训练日志。来源没有披露的训练配方和数值，不得由示意图或脚本变量名推断成事实。','本地完整 HTML/MHTML 底稿单独保留；本 ZIP 优先携带 Pro 可直接阅读的 Markdown、JSON、PDF 与图像。']
 task='\n'.join(notes)+'\n';manifest=[]
 with zipfile.ZipFile(delivery/(name+'.zip'),'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  z.writestr('TASK_README.md',task)
  for f in sorted(entries):
   assert f.exists(),f
   rel=str(f.resolve().relative_to(root));data=f.read_bytes();z.writestr(rel,data);manifest.append({'file':rel,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
  z.writestr('MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
 (delivery/(name+'.md')).write_text(task);results.append({'file':name+'.zip','bytes':(delivery/(name+'.zip')).stat().st_size,'entries':len(entries)+2})
(delivery/'README.md').write_text('# 交给外部 Pro 的六组附件\n\n每组 ZIP 内先读 TASK_README.md。若 Pro 不能解压，请本地解压后上传 Markdown、JSON 和 PDF。完整缺口说明见 [上级资料入口](../README.md)。\n\n'+'\n'.join(f'- [{x["file"]}]({x["file"]})：{x["bytes"]/1024/1024:.2f} MiB' for x in results)+'\n')
(root/'delivery_summary.json').write_text(json.dumps(results,indent=2))
with zipfile.ZipFile(root/'Cognition_Pro_source_supplements_20260911.zip','w',zipfile.ZIP_STORED) as z:
 z.writestr('README.md','# 外部 Pro 精读补充包\n\n本包包含六组任务附件。进入 delivery/，按任务选择 ZIP，解压后先读各包的 TASK_README.md。若 Pro 不能解压 ZIP，请上传解压后的 Markdown、JSON 和 PDF。\n\n重要缺口：Kool et al. 2019 全文仍未取得，只有 POSTER_ONLY 海报；不能代替全文。此次仅采集来源，没有进行独立精读审查或训练复现。\n\n'+''.join('- [说明：'+n+'](delivery/'+n+'.md)；[附件](delivery/'+n+'.zip)\n' for n,_,_ in groups))
 for f in sorted(delivery.glob('*')):z.write(f,'delivery/'+f.name)
print(json.dumps(results,indent=2))
