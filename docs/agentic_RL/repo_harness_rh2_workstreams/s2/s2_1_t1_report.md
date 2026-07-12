# S2-1 T1 报告：raw 重抓归档 + 键控镜像清单

日期：2026-07-12。执行：S2-1 线程（本机）。依据：执行计划 §4 T1。判定：**全 PASS，T2 可开工**。产物 digest 账：`s2_1_manifest_v0.json`（回链 freeze_manifest v0.1，冻结账本未动）。

## T1a raw 重抓归档（`rh2/experiments/s2_1_ingestion/fetch_raw_lite.py`，可重跑）

```text
1. revision 核对：HF 当前 sha == 冻结 pin（f70b1a29…）——数据集自冻结未动；
   下载走 hf_hub_download 按 pin 取 parquet（不走 datasets-server，
   它只服务最新 revision 无法按 pin 取数）。
2. 230 行 × 11 列，与 strip_spec swe_bench_family 键集合双向相等
   （多列拒绝/少列拒绝的 fail-closed 两个方向都在脚本里）。
3. survivor 级 D5 断言（codex 轮次 5 指出旧互斥脚本的 train_pool∩heldout
   是同义反复后新增的真实检查）：216/216 按 instance_id join 成功、
   唯一、repo ∩ {tornado,pyramid,hydra,bokeh} = ∅。此断言就此成为
   正式机器检查，T2 起并入 ingestion 库。
4. 一致性回验：230 行的 8 个裁剪字段逐字节等于冻结 meta/swe_gym_lite.jsonl
   ——raw archive 与冻结元数据同源同版的直接证明。
5. 落盘：s2/raw/swe_gym_lite_full_f70b1a29.jsonl（3.5MB 明文，按
   instance_id 排序 + 键排序，可 diff 可复算）+ .sha256 旁证。
```

## T1b 键控镜像清单（`rh2/experiments/s2_1_ingestion/resolve_image_digests.py`，可重跑/断点续跑）

```text
216/216 解析成功 → s2/image_manifest_keyed.json
方法：逐镜像匿名 token + registry HEAD 读 Docker-Content-Digest
  （HEAD 不计 Docker Hub pull 限额；0.4s 间隔 + 指数退避，实跑零 429）。
映射校验：`_s_` 规则推导 ref 均存在于冻结清单——但首跑抓到一个真实坑：
  Docker 仓库名强制小写，规则必须是 replace('__','_s_') + lower()
  （Project-MONAI__MONAI-* → project-monai_s_monai-*）。data_freeze 的
  image_manifest.md 只写了 `_s_` 替换未写小写化；fail-closed 校验按设计
  拦截，规则已修正并记 implementation-notes（勘误回写清单 +1）。
内容类型：216 个全部是单架构 v2 manifest（非 manifest list）——
  platform 字段按命名约定记 x86_64，抽样 GET 证实"单 manifest"形态
  （架构在 config blob，未展开；诚实留痕，不冒充逐镜像实证）。
```

## 发现：214 唯一 digest / 216 条——两对同镜像任务

```text
getmoto__moto-6469 / getmoto__moto-6470    同 repo+base_commit（3e11578a…）
python__mypy-11824 / python__mypy-11857    同 repo+base_commit（f96446ce…）
```

两对都是**同一仓库快照上的不同 issue**（题面、F2P 各不相同）——是真正不同的任务，共享环境镜像合理。**语义结论（T2 落实）**：`(repo, base_commit)` 是**环境身份**（镜像缓存/物化可去重），不是**任务身份**（任务身份 = instance_id / 题面 + F2P）；data_freeze 的跨源去重规则意图是"同一真实 commit 的**同一任务**从两源重复进池"，T2 实现应比对 `(repo, base_commit, F2P 集合)` 或标记人工复核，**不得按 (repo, base_commit) 盲目去重**（否则这两对里各有一题被错杀）。

## T0 补注（codex 轮次 5）

旧互斥脚本的 `train_pool ∩ heldout` 检查在数学上必空（`train_pool` 定义时已减去 heldout），T0 报告的该行不构成 survivor 级证明；真实证明由本报告 T1a 第 3 项 + codex 独立复跑（216/216 join、命中 0）补齐。T0 的其余结论（digest 零漂移、与 Verified 互斥）不受影响。
