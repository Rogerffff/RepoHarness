# getmoto__moto-5752

`needs_review / static_review`；限 `development_diagnostic`，尚非 ready_for_probe。

公开问题是 SSM 多标签过滤应取全部条件、与顺序无关。base 标签分支提前 return True，gold 令各条件继续受检，修复路径明确。唯一新增 F2P 有4个数量断言：两种 Equals 顺序直接对应题面；两条单标签 BeginsWith 又覆盖独立旧缺陷。公开校验器允许 BeginsWith，故“题面未明说”尚不足以定性误拒；仍需裁定本题验收范围。

精确 baseline 记录为 gold 安装0/测试0、80 passed、reward1；noop 安装0/测试1、79 passed+目标反序失败、reward0。冻结引用1 F2P+79 P2P；已读33个P2P引用对应正文，其余46只核日志/列表。gold 无内部布局强制，标签分支独立实现亦可满足断言。未查出具体新回归，不把普通计数覆盖缺口自动判坏。

历史核对推翻“tag Contains 可达 gold 缺陷”：接口校验只为 Name 放行 Contains。Description 删除实为7处，旧断言不变。原 hints 不仅有 parameter.tag 笔误，还缺命中后的 continue；只改字段仍会落入通用比较，不能当作有效窄候选；只有 w/world 前缀断言能区分窄 Equals 修复，a/a不能。截断ID与固定parser仍一一对应；独立复核确认后期base包含先前修法的版本关系，不据此自动分组。

当前 grader 使用 public digest 的baseline、rh2grader/54322；apply_user54321不等于正式actor。实际actor的导入/写权限、公开消息、离线开发验证及答案可见性未验。Terraform gitlink `tests/terraformtests/terraform-provider-aws@f9a6db6e3c3f3299701747972fd6c37ba4af36f4` 未物化，与最小SSM mock路径无关，不能推断容器缺资产。官方只恢复 `tests/test_ssm/test_ssm_boto3.py`，`test_globs=()`，额外排除空。

唯一优先实验：base/gold加一个自然的“只修AND顺序”候选，核公开MWE的Name集合与原冻结评分，确认是否仅在w/world前缀处被拒；独立reviewer保留范围争议；诊断分数不能独自裁决规范，也不把诊断补丁当独立求解。详细证据见封存初稿与历史差异；未执行新项目命令，成本未知。

协调裁定：保留为范围待定的受限静态候选。唯一窄候选明确采用等值未命中返回False、命中continue外层；不直接使用raw hints。本题base已含5134修法，7584后期base含本题匹配路线，实际求解暴露未知。独立复核已完成，见[review.md](review.md)。
