# MONAI reserve6：root 执行前审查

仅允许按冻结脚本做有界CPU实验，尚无两题新运行结果。

已核4583实际box/label与2D/3D矩阵、6975返回像素及lazy策略，后者不把resample次数作为唯一正确答案；公开actor、私有gold/退化分离。每变体独立检查准备、整文件SHA、结果与清理，正式原测试/参考不变，含manager容器账目。镜像导入、prelaunch和资源仍须实际结果复核。

脚本和范围见[结构记录](reserve6_monai_root_prelaunch_review.json)。不据静态审查授予探针或训练资格。
