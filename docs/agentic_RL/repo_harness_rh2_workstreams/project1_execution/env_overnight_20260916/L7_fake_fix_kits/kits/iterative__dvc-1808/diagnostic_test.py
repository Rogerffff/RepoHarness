"""L7 判别用例 · iterative__dvc-1808

F2P `test_overwrite` 只断言 `main()` 的返回码序列 0 / 1 / 0，不去读 `.dvc/config`。
题面的 Current behavior 抱怨的恰恰是"报错的同时 url 已经被静默覆盖"。

三态预期：base 失败（第二次 add 返回 0）、gold 通过、
fake 失败（返回码对，但 url 已经被第二次的值覆盖）。
"""
import configobj

from dvc.main import main

from tests.basic_env import TestDvc


class TestL7RemoteOverwriteKeepsConfig(TestDvc):
    def test_config_unchanged_when_add_is_rejected(self):
        name = "a"
        first = "s3://bucket/first"
        second = "s3://bucket/second"

        assert main(["remote", "add", name, first]) == 0
        assert main(["remote", "add", name, second]) == 1

        config = configobj.ConfigObj(self.dvc.config.config_file)
        assert config['remote "a"']["url"] == first, config['remote "a"']["url"]
