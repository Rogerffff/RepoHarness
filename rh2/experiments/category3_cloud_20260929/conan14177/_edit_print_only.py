exec(open("/w/_edit_common.py").read())
s = s.replace(OLD, '''            entry = it.copy()
            patch_file_name = entry.pop("patch_file")
            patch_file = os.path.join(conanfile.export_sources_folder, patch_file_name)
            if verbose:
                conanfile.output.info("Applying: {}".format(patch_file_name))
                continue
            patch(conanfile, patch_file=patch_file, **entry)
''')
p.write_text(s)
