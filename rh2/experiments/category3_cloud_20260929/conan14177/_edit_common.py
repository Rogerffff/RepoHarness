from pathlib import Path
p = Path("conan/tools/files/patches.py")
s = p.read_text()
s = s.replace("def apply_conandata_patches(conanfile):", "def apply_conandata_patches(conanfile, verbose=False):", 1)
OLD = '''            entry = it.copy()
            patch_file = os.path.join(conanfile.export_sources_folder, entry.pop("patch_file"))
            patch(conanfile, patch_file=patch_file, **entry)
'''
assert OLD in s
