# DVC5839 Coder 首臂：模型文件计数更正

2026-10-03。原作者审计与首轮验收保持原 SHA，本页更正其中一项计数表述，不改变业务修复、23/23 评分、请求核收或服务身份的证据范围。

`coder_a1_semantic_audit_v1.md` 第 6 维称“28 文件下载清单及 25 个权重文件数／大小已核”。实际 `download_manifest_actual.json` 的 `files_count` 字段为 28，但 `files` 数组仅 25 项；`model_file_sizes_actual.json` 也仅 25 项且逐项名称／大小与数组一致，其中 safetensors **16 个分片**，其余为配置、tokenizer、模板、索引及 parser。原报告把 declared count 和实际列表混为一谈，并误称 25 项全是权重，现予更正。

原件位于 `runs/ordinary_gpu_probe_20261002/remote/diagnostics/QUEUE_V20_gpu1003-dvc5839-coder-a1_before/`：下载清单 SHA `5783533eae085661e3b3cde2e46ee46c9dbce0c05154d6028f6e46aa7260de39`，实际大小列表 SHA `a10a5d6fe23597016d4e6f40482c768416149c7a1a8e58758dc945a944a9f001`，capture 的清单指针匹配该原件。此次只读比对，没有下载、SSH、模型／候选／评分执行或重新逐权重哈希。

更正后的范围为：**实时 operational capture 绑定同一 engine／adapter、只读 model mount 和 HTTP 配置；实际列出的 25 个模型文件大小核对，其中 16 个权重分片；声明计数 28 与列表 25 不一致。** 这既不是全 GPU 内存权重证明，也不将三个未列出项推断成缺失权重或运行故障。原首轮的限制保持，当前阅读入口和 results 应同时指向本更正。
