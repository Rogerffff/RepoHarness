"""原测试的数据生成与 DataLoader 短复现；不训练 UNet，不产出 SWE 分数。"""
import ast
import hashlib
import inspect
import json
import os
import sys
import time
sys.path.insert(0, "/testbed")
import tests.test_integration_segmentation_3d as task

source = inspect.getsource(task.run_training_test)
tree = ast.parse(source)
fn = tree.body[0]
fn.name = "make_original_loader"
cut = next(i for i, n in enumerate(fn.body) if isinstance(n, ast.Assign)
           and any(isinstance(t, ast.Name) and t.id == "dice_metric" for t in n.targets))
fn.body = fn.body[:cut] + [ast.Return(value=ast.Name(id="train_loader", ctx=ast.Load()))]
ast.fix_missing_locations(tree)
scope = dict(task.__dict__)
exec(compile(tree, "original_loader_prefix", "exec"), scope)
record = {"source_sha256": hashlib.sha256(source.encode()).hexdigest(),
          "requested_batches": 3, "loaded_batches": 0, "status": "started"}
started = time.monotonic()
case = task.IntegrationSegmentation3D(methodName="test_training")
try:
    case.setUp()
    task.torch.manual_seed(0)
    loader = scope["make_original_loader"](case.data_dir, device=case.device, cachedataset=False)
    iterator = iter(loader)
    for _ in range(3):
        batch = next(iterator)
        record["loaded_batches"] += 1
        record["batch_tensor_bytes"] = sum(v.numel() * v.element_size() for v in batch.values() if task.torch.is_tensor(v))
        stat = os.statvfs("/dev/shm")
        record.setdefault("shm_used_bytes", []).append((stat.f_blocks - stat.f_bfree) * stat.f_frsize)
    record["status"] = "loaded_three_batches"
except Exception as exc:
    record["status"] = "error"
    record["exception_type"] = type(exc).__name__
    record["error"] = str(exc)
finally:
    record["elapsed_s"] = round(time.monotonic() - started, 3)
    print("CODEX_LOADER_RESULT " + json.dumps(record, ensure_ascii=False), flush=True)
