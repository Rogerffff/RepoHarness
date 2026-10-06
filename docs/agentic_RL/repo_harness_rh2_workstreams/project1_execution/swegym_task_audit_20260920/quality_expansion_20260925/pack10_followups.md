# pack10 后续建议（未执行、未派发）

任务二由Claude B负责；本文件只提供选择性建议。含gold/隐藏测试的对照留在私有审查环境，不进入独立solver上下文。实际actor入口、初态、导入、权限、依赖和资产证据另行取得，历史grader不能替代。

13610唯一优先项：明确公开无参数、裸-v、显式verbose和帮助的契约，再决定是否修订题面、验收及参考帮助。现有日志矩阵重复执行不能决定产品语义。quiet/help缺口按明确后的契约处理，不机械补全仓测试。

13788唯一优先项：同条件base/gold的本地三节点root→build工具T→普通依赖D，使用host/build两profile。空Python recipes即可，无需编译器、网络或全仓。优先用lock create生成待构建锁，再install --build触发锁重放；保存锁中T→D的实际context、Requirement.build_require_context、RC及准确错误位置，确认目标源文件生效。若另选install生成已含prev的完整锁，后续不要无条件强制重建而混入已锁prev的限制；具体入口由任务二记录。

base成功且gold在D上下文查找处失败，才将26升级为已证功能回归；若gold成功，记录实际图/调用路径解释静态疑点为何不触发。保留公开目标正例作控制，但不再新增多个猜测反例或模型实验。当前没有执行结果。
