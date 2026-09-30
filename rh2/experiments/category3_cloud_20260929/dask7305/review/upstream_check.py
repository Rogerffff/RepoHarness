"""上游对照（只作佐证，不作公开依据）：从 PyPI 下载 dask wheel，核对 sha256，看 partitionquantiles.py 的两处写法。
在宿主机运行（需要访问 pypi.org 与 files.pythonhosted.org）；不在评分容器内运行。
"""
import hashlib, io, json, re, urllib.request, zipfile

for ver in ["2021.3.0", "2024.1.0", "2025.9.1"]:
    meta = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/dask/{ver}/json", timeout=60))
    whl = next(f for f in meta["urls"] if f["filename"].endswith(".whl"))
    data = urllib.request.urlopen(whl["url"], timeout=120).read()
    assert hashlib.sha256(data).hexdigest() == whl["digests"]["sha256"]
    src = zipfile.ZipFile(io.BytesIO(data)).read("dask/dataframe/partitionquantiles.py").decode()
    print(ver, whl["filename"], whl["digests"]["sha256"][:12])
    print("   process_val_weights array:", re.findall(r"vals = np\.array\(vals[^\n]*", src))
    print("   under-sampled branch:     ", re.findall(r"rv = np\.interp\([^\n]*", src))
