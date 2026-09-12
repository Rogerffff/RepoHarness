# 将已采集的原文与截图整理成阅读附件，不改写来源中的公式或结论。
from pathlib import Path
import sys,json,math
sys.path.insert(0,'/tmp/cognition-json5')
from bs4 import BeautifulSoup,NavigableString
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
root=Path(__file__).resolve().parent.parent
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
summary=[]
for meta in sorted(root.glob('*/capture.json')):
 d=meta.parent;j=json.loads(meta.read_text());topic=d.name
 soup=BeautifulSoup((d/'expanded.html').read_text(),'html.parser')
 for e in soup.select('script,style,nav,header,footer'):e.decompose()
 for e in soup.select('.katex'):
  a=e.select_one('annotation[encoding="application/x-tex"]')
  if a:e.replace_with(NavigableString(' $'+a.get_text()+'$ '))
 for e in soup.select('img'):
  e.replace_with(NavigableString('\n[原网页图片：'+e.get('alt','')+'；地址：'+e.get('src','')+']\n'))
 txt=soup.get_text('\n',strip=True)
 (d/'reading_text.md').write_text('# '+j['title']+'\n\n原始来源：'+j['url']+'\n\n采集时间：'+j['captured_at']+'。以下为网页正文提取，不是精读报告；交互示例的完整数据另见 states/、embedded/ 与公共 JSON。数学公式优先保留网页自身的 TeX；图片公式请查看图表 PDF。\n\n---\n\n'+txt+'\n')
 visuals=[v for v in j['visuals'] if not v.get('src','').startswith('https://cognition.com/_next/image?')]
 files=[(v['file'],d/v['file']) for v in visuals]
 files += [(str(f.relative_to(d)),f) for f in sorted((d/'states').glob('*.png')) if not f.stem.endswith('-initial')]
 output=d/'visual_supplement.pdf';c=canvas.Canvas(str(output));c.setTitle(j['title']+' - visual source supplement');c.setAuthor('RepoHarness source capture')
 index=['# '+topic+' 图表与交互状态索引','','原始网页：'+j['url'],'','图表 PDF 由原网页截图排版；不是作者发布的 PDF。图像中的数据和措辞没有重绘或改写。横纵轴只有相对刻度时，不得从 JSON 内部坐标推断实际训练 step 数。','', '| PDF 页 | 图片 | 说明 |','| --- | --- | --- |'];page=0
 for name,f in files:
  im=Image.open(f).convert('RGB');w,h=im.size;scale=770/w
  # 长截图分段分页，每段保留原像素；完整文本另存，不能依赖滚动框截图代表全文。
  chunk_h=max(1,int(980/scale));parts=math.ceil(h/chunk_h)
  for part in range(parts):
   y0=part*chunk_h;piece=im.crop((0,y0,w,min(h,y0+chunk_h)));ph=piece.height*scale;pageh=max(595,ph+110);c.setPageSize((842,pageh));c.setFont('STSong-Light',12);c.drawString(36,pageh-28,topic+' / '+name+(f'（第 {part+1}/{parts} 段）' if parts>1 else ''));c.setFont('Helvetica',8);c.drawString(36,pageh-45,j['url']);c.drawInlineImage(piece,36,pageh-65-ph,width=770,height=ph);c.setFont('STSong-Light',9);page+=1;c.drawString(36,24,f'网页视觉补充 / 2026-09-11 / 第 {page} 页 / 完整内容请结合正文、原图与示例数据');c.showPage()
   index.append(f'| {page} | [{name}]({name}) | '+('交互状态；滚动框完整文本另存' if name.startswith('states/') else '网页图表 / 图片')+' |')
 c.save();(d/'VISUAL_INDEX.md').write_text('\n'.join(index)+'\n');summary.append({'topic':topic,'source':j['url'],'visual_items':len(files),'pdf_pages':page,'math_expressions':len(j['math'])})
(root/'package_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,indent=2))
