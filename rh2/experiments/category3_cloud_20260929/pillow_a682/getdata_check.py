"""旧接口 getdata：P 图 info 里有整数透明度时，(1) 不传参数、(2) 以参数 transparency=1 传入，是否写出透明标志。"""
import json
from PIL import GifImagePlugin, Image

for label, kw in (("info_only", {}), ("param", {"transparency": 1})):
    im = Image.new("P", (4, 4), 1)
    im.putpalette([0, 0, 0, 255, 0, 0] + [0] * 762)
    im.info["transparency"] = 1
    data = b"".join(GifImagePlugin.getdata(im, **kw))
    gce = data.find(b"!\xf9\x04")
    print(json.dumps({"case": label, "gce_present": gce >= 0,
                      "transparent_flag": (data[gce + 3] & 1) if gce >= 0 else None,
                      "transparent_index": data[gce + 6] if gce >= 0 else None}))
