# reserve20 静态材料准备记录

范围严格为冻结 manifest.reserve20_task_ids 的20题。根任务已授权继续该冻结名单；manifest中的原历史阶段字段保持不变。本记录仅描述机械材料导出与身份核验，不是质量审查或当前运行资格判断。

20题的三源行、公开题面、AST对拍重建prompt、精确base、私有gold/test原始补丁、逐题历史hash引用均已导出。40条运行引用（20 noop、20 gold）均已定位，原日志hash已核对；同题同attempt的所有候选目录均已复核，task_id、candidate.kind、raw patch SHA（noop为null且无patch）、baseline task/base/head、stage apply_method/head及projection摘要/物理attempt/rollout绑定均唯一匹配。未通过worker目录glob猜测归属。原件未缺失，绑定无歧义。

## 校验结果

- 20/20题静态材料导出完成；14,881个Git blob，共202,895,074字节，50个可执行blob。
- 精确Git对象字节、磁盘字节、权限mode、完整路径集合逐题核验通过；4个符号链接原样保留，0个gitlink，0个LFS指针。
- 公开目录仅base/、base_identity.json、environment_brief.md、public_bundle.json、user_prompt.txt；私有gold/test和历史引用未混入公开顶层。base含当时已跟踪测试，不含未来Git历史。
- 20份环境引用JSON的所有字符串对manifest其余任务ID进行机械扫描，无跨题ID引用。
- 历史仅枚举ref与hash，未解析、复制或展示历史质量内容。
- 实际image ID与expected source digest分字段保留；20/40条历史运行的实际image ID原值为null，不以expected digest替代。

## 保留的具体缺口

以下10题在catalog指定的 `runs/env_recipe_repair_20260919/inventory/records/<task_id>.json` 未定位本地repair image inventory文件，且对应noop/gold两条历史运行的实际image ID为unknown；baseline生成shell脚本未单独定位，已有host grading view和历史代码身份引用。这不是镜像内资产缺失的证据：

- Project-MONAI__MONAI-4583
- Project-MONAI__MONAI-5932
- Project-MONAI__MONAI-6975
- conan-io__conan-11560
- conan-io__conan-12397
- conan-io__conan-13403
- conan-io__conan-13610
- conan-io__conan-13788
- dask__dask-7305
- dask__dask-7894

所有20题的实际actor初始工作树、初始修改、忽略资产、消息交付、用户/权限、PATH/解释器/导入状态仍未核验。历史代码tar仅检查成员元数据，未解包、执行或逐成员校验内容。公开prompt是当前模板AST对拍的计划输入，不等于实际发送消息。

## 写入边界与未触碰项

仅新建prepare_reserve20_materials.py、新reserve20汇总/本说明和RUN下本20题public/private/history/material_checks。新脚本已删除原correct_references入口；默认只处理reserve20，--resume也仅限reserve20。运行时Python审计hook将写入限制在这20题和新汇总，阻止读取首12材料目录及results。首12现有材料、汇总、检查记录、原脚本与提交快照未写入；未重扫首12 base blobs。未创建results，未修改assignments/root_dispatch。未执行或导入项目、测试、容器、SSH、GPU/模型工作；未联网、安装、下载、commit或push。

## 文件SHA256

- `manifest.json`: `52649a38cadccdeacc2317f8d4fb7beee798247e2c9adbc00a198dea88261c7e`
- `prepare_materials.py`: `4c8790d705d7d621ef34d780be2482cfe6c915f0fefbddb820de29ca2a805bf5`
- `prepare_reserve20_materials.py`: `d9f9320d1a27290c440eecabf59534c71e3e42a844059212cc39f636135ccf09`
- `reserve20_material_check.json`: `a3578490f2a87a45d5133b685c39a45afcf4ecc1a0e4bd4ffec30773a6200928`
- `reserve20_environment_replay_inventory.json`: `5fd6a217422109a941c9c4b57dea29d55157fc86fe966d0187fb7be42c1d40b4`

## 逐题检查SHA256

- `runs/swegym_quality_expansion_20260925/material_checks/Project-MONAI__MONAI-1121.json`: `3e550961099a0ad4632529940e37ca9d5bd1cff622cdb9cfe0a9cad5a70a5051`
- `runs/swegym_quality_expansion_20260925/material_checks/Project-MONAI__MONAI-3566.json`: `96792e6ee81ed111fe8a92319f10a11e889dfdca03fb04cdabad5bd287070150`
- `runs/swegym_quality_expansion_20260925/material_checks/Project-MONAI__MONAI-4583.json`: `770450425a49ca3de858a33fd5845d5657dde143a2d6c969d05fc2a194df9e00`
- `runs/swegym_quality_expansion_20260925/material_checks/Project-MONAI__MONAI-5932.json`: `a9c3dd27ebb3a7dbdfc22ca3a80193b6f9de090d6f44a1e715ab5474679a7558`
- `runs/swegym_quality_expansion_20260925/material_checks/Project-MONAI__MONAI-6975.json`: `28766acec07dd5eef25b755aa08ce9164254706ee15de43c66130035f964e70d`
- `runs/swegym_quality_expansion_20260925/material_checks/conan-io__conan-11560.json`: `6738d8f81ce86eba4f2be40fa4879bebfa4205904786d6b3711697826b3fac9d`
- `runs/swegym_quality_expansion_20260925/material_checks/conan-io__conan-12397.json`: `7787f7e1415b8616671ce297e7de9290508c8d7c07d8cd2e00f0d9bab687bc73`
- `runs/swegym_quality_expansion_20260925/material_checks/conan-io__conan-13403.json`: `16291d69f29f2d85f2177f7507c1982e79d0bf2aff283378f24c1f45d6c0f5c7`
- `runs/swegym_quality_expansion_20260925/material_checks/conan-io__conan-13610.json`: `0f150f187de8c1e932efaa8a2dc766e3802d528b8ad03b5a873cc506f300f2e0`
- `runs/swegym_quality_expansion_20260925/material_checks/conan-io__conan-13788.json`: `3c349ce63c6ccdde1f75e8ec30d59a4387dc3f4b58455471ae6fe0184265bc2a`
- `runs/swegym_quality_expansion_20260925/material_checks/dask__dask-6801.json`: `6e2b149c1bc8e60e5019f273a61eaae6dd82f861a819a48918ba1646f07a6c5b`
- `runs/swegym_quality_expansion_20260925/material_checks/dask__dask-7138.json`: `f831d674f7d74c87768df1f9d5f4446f357505224da451f52726e4a034353f95`
- `runs/swegym_quality_expansion_20260925/material_checks/dask__dask-7305.json`: `8ffca044f74de494f78d7768462e9ea30b697d05731c4a89213590f34cdf2d11`
- `runs/swegym_quality_expansion_20260925/material_checks/dask__dask-7894.json`: `cb9067638b656249a6e9534ba0e752ad4ca15040afe34b3e843cd2155021fbda`
- `runs/swegym_quality_expansion_20260925/material_checks/dask__dask-9212.json`: `cb54b2fcdf69b42c2118a900c7bce5e64e0cd149fb7af4165110ca62bc0ef6f6`
- `runs/swegym_quality_expansion_20260925/material_checks/pydantic__pydantic-5662.json`: `9bed3da04f01d277c80c12502c347657b1788a5203e8fe58cd9ebfeb0a0425e6`
- `runs/swegym_quality_expansion_20260925/material_checks/pydantic__pydantic-6043.json`: `7030b8d2c70088e172f65612a0f672f48c49c221bc5ce90af745fc25046e0331`
- `runs/swegym_quality_expansion_20260925/material_checks/pydantic__pydantic-8316.json`: `4c719ea2da894d488aace418b5c745d02d1eb2f5e0848597a26d773aa77ef8a2`
- `runs/swegym_quality_expansion_20260925/material_checks/pydantic__pydantic-8793.json`: `24a380cf3d0523e9781188a403228710154fa5260614f0fb268fce7d011b55ab`
- `runs/swegym_quality_expansion_20260925/material_checks/pydantic__pydantic-9066.json`: `6aa7344faaa84ecc1fb85bfd742ec1f60c6e861d28266aaa6225ad328228bd07`
