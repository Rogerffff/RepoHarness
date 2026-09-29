# 在 gold 之上构造两种变体（MODE）：
#  alt_ds_only  ：逐 stage 拉取只针对数据源 stage（dvc add/import），其余 stage 的输出靠 run-cache 恢复（按需拉取）
#  gold_guarded ：gold + dry 时不拉取 + 未配置 remote 时跳过拉取（"Try automatically pulling" 的尽力语义）
import os
import subprocess
from pathlib import Path
mode = os.environ["MODE"]
subprocess.run(["git", "apply", "/w/gold.patch"], check=True)
p = Path("dvc/repo/reproduce.py"); s = p.read_text()
per_stage = '''            if kwargs.get("pull") and stage.changed():
                logger.debug("Pulling %s", stage.addressing)
                stage.repo.pull(stage.addressing, allow_missing=True)
'''
assert s.count(per_stage) == 1
if mode == "alt_ds_only":
    s = s.replace(per_stage, per_stage.replace('if kwargs.get("pull") and stage.changed():',
                                               'if kwargs.get("pull") and stage.is_data_source and stage.changed():'))
elif mode == "gold_guarded":
    head = '''    if kwargs.get("pull", False):
        logger.debug("Pulling run cache")
        self.stage_cache.pull(None)
'''
    assert s.count(head) == 1
    s = s.replace(head, '''    if kwargs.get("pull", False) and not kwargs.get("dry", False):
        logger.debug("Pulling run cache")
        try:
            self.stage_cache.pull(None)
        except NoRemoteError:
            logger.debug("No remote configured, not pulling run cache")
''')
    s = s.replace(per_stage, '''            if kwargs.get("pull") and not kwargs.get("dry") and stage.changed():
                logger.debug("Pulling %s", stage.addressing)
                try:
                    stage.repo.pull(stage.addressing, allow_missing=True)
                except NoRemoteError:
                    logger.debug("No remote configured, not pulling %s", stage.addressing)
''')
    s = s.replace("from dvc.exceptions import ", "from dvc.config import NoRemoteError\nfrom dvc.exceptions import ", 1)
else:
    raise SystemExit(mode)
p.write_text(s)
