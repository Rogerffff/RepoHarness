# 退化（§4 第 3 步“抑制症状/不做实际工作”）：保留 gold 的日志形态，但 apply_conandata_patches 对文件补丁只打印、不应用
from pathlib import Path
p = Path("conan/tools/files/patches.py")
s = p.read_text()
s = s.replace("    patch_type = kwargs.get('patch_type')\n",
              "    patch_type = kwargs.get('patch_type') or (\"file\" if patch_file else \"string\")\n", 1)
OLD = '''            entry = it.copy()
            patch_file = os.path.join(conanfile.export_sources_folder, entry.pop("patch_file"))
            patch(conanfile, patch_file=patch_file, **entry)
'''
assert OLD in s
s = s.replace(OLD, '''            entry = it.copy()
            patch_file = entry.pop("patch_file")
            patch_type = entry.get("patch_type") or "file"
            description = entry.get("patch_description") or patch_file
            conanfile.output.info("Apply patch ({}): {}".format(patch_type, description))
''')
p.write_text(s)
