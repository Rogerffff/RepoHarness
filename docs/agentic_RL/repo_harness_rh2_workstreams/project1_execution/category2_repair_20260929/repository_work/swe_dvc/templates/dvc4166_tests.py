

def test_directory_rule_prunes_directory(tmp_dir, dvc):
    tmp_dir.gen({"blocked": {"leaf": "directory data"}})
    tmp_dir.gen(DvcIgnore.DVCIGNORE_FILE, "blocked/\n")
    assert not dvc.tree.isdir("blocked")
    assert not dvc.tree.exists("blocked")


def test_directory_rule_keeps_regular_file(tmp_dir, dvc):
    tmp_dir.gen("blocked", "regular file data")
    tmp_dir.gen(DvcIgnore.DVCIGNORE_FILE, "blocked/\n")
    assert dvc.tree.isfile("blocked")
    with dvc.tree.open("blocked") as stream:
        assert stream.read() == "regular file data"


def test_negated_directory_rule_recovers_non_example(tmp_dir, dvc):
    tmp_dir.gen({"kept": {"leaf": "visible"}, "other": {"leaf": "hidden"}})
    tmp_dir.gen(DvcIgnore.DVCIGNORE_FILE, "/*\n!/kept/\n")
    assert dvc.tree.isdir("kept")
    assert _files_set("kept", dvc.tree) == {"kept/leaf"}
    assert not dvc.tree.exists("other")
