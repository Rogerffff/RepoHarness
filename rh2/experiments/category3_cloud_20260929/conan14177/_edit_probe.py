# 复核者提出的变体（在 base 的 apply_conandata_patches 上构造）。PROBE 选择一种。
import os
from pathlib import Path
probe = os.environ["PROBE"]
p = Path("conan/tools/files/patches.py")
s = p.read_text()
sig_old = "def apply_conandata_patches(conanfile):"
sig_new = {"kwonly": "def apply_conandata_patches(conanfile, *, verbose=False):"}.get(probe, "def apply_conandata_patches(conanfile, verbose=False):")
s = s.replace(sig_old, sig_new, 1)
OLD = '''            entry = it.copy()
            patch_file = os.path.join(conanfile.export_sources_folder, entry.pop("patch_file"))
            patch(conanfile, patch_file=patch_file, **entry)
'''
assert OLD in s
body = {
 # 应用成功后才记录
 "post": '''            entry = it.copy()
            name = entry.pop("patch_file")
            patch_file = os.path.join(conanfile.export_sources_folder, name)
            patch(conanfile, patch_file=patch_file, **entry)
            if verbose:
                conanfile.output.info("Applied: {}".format(name))
''',
 # 记录绝对路径
 "abspath": '''            entry = it.copy()
            patch_file = os.path.join(conanfile.export_sources_folder, entry.pop("patch_file"))
            if verbose:
                conanfile.output.info("Applying: {}".format(patch_file))
            patch(conanfile, patch_file=patch_file, **entry)
''',
 # 有描述时把文件名并入描述行，无描述时单独一行
 "merged": '''            entry = it.copy()
            name = entry.pop("patch_file")
            patch_file = os.path.join(conanfile.export_sources_folder, name)
            if verbose:
                if entry.get("patch_description"):
                    entry["patch_description"] = "{} [{}]".format(entry["patch_description"], name)
                else:
                    conanfile.output.info("Applying: {}".format(name))
            patch(conanfile, patch_file=patch_file, **entry)
''',
 # 仅关键字参数（签名不同于题面）
 "kwonly": '''            entry = it.copy()
            name = entry.pop("patch_file")
            patch_file = os.path.join(conanfile.export_sources_folder, name)
            if verbose:
                conanfile.output.info("Applying: {}".format(name))
            patch(conanfile, patch_file=patch_file, **entry)
''',
 # 日志各模式都对（含描述行），但从不应用补丁
 "logonly_v": '''            entry = it.copy()
            name = entry.pop("patch_file")
            if verbose:
                conanfile.output.info("Applying: {}".format(name))
            ptype, pdesc = entry.get("patch_type"), entry.get("patch_description")
            if ptype or pdesc:
                conanfile.output.info("Apply patch{}{}".format(" ({})".format(ptype) if ptype else "",
                                                               ": {}".format(pdesc) if pdesc else ""))
''',
 # 只记录 basename（不能对应到 conandata 中的补丁路径）
 "basename": '''            entry = it.copy()
            name = entry.pop("patch_file")
            patch_file = os.path.join(conanfile.export_sources_folder, name)
            if verbose:
                conanfile.output.info("Applying: {}".format(os.path.basename(name)))
            patch(conanfile, patch_file=patch_file, **entry)
''',
}
if probe == "header":
    body_text = body["kwonly"]
    s = s.replace("    for it in entries:\n", "    if verbose:\n        conanfile.output.info(\"apply_conandata_patches(): {} patch(es) selected\".format(len(entries)))\n    for it in entries:\n", 1)
else:
    body_text = body[probe]
s = s.replace(OLD, body_text)
p.write_text(s)
