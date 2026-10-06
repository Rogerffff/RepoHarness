# Orange4014／9b公开开发说明非作者窄核

整理日期：2026-10-03。**当前两份说明的事实、公开依据和可见边界核查完成；9b原有一处测试范围误述已由作者修正，现无未解决必改项。** 本轮不称CPU最终验收、实际CC交付完成或GPU准入。

只读核新brief，复用既有静态／公开阅读及9b版本校准，没有重审题目、派新fresh reader、运行CPU／Docker／构建／pytest或轮询矩阵。已封存Orange50报告保持原样；仅新增本报告和同名JSON。

| 被审文件 | 当前SHA-256 | 当前结论 |
| --- | --- | --- |
| [4014公开说明](../tasks/4014f248/public_development_brief.md) | `a7f74bbe44d82bca2ab0bdfe8b36ac9eabc31bc96a991e1f48c5f69e48c025ab` | 入口真实、范围准确，未发现必改项。 |
| [9b公开说明](../tasks/9b5494e2/public_development_brief.md) | `33d7e34f091c820c6b1456133fd53578e9b0bc7bad87b38814f358c19d5e3c06` | 已核作者修正，无待改项。 |

## 4014：构建提醒与公开测试入口有依据

公开[setup.py](../../../../../../../../runs/r2e_static_prep_20260924/v3/public/orange3__4014f2483e3bab0621c9ae0f994947c008183253/worktree/setup.py)第428—433行声明自动Cython构建`Orange/*/*.pyx`，第471—473行在NumPy／Cython可用时注册`build_ext`；因此`python setup.py build_ext --inplace`是实际开发入口。固定R9 census确实含`Orange/preprocess/_discretize.cpython-37m-x86_64-linux-gnu.so`，其SHA为`9ee458d0…`。提醒源码修改后重编、检查退出状态、用新Python进程核加载路径，解决的是现有源码／二进制状态差异，没有给切点处理答案。

公开[TestEqualFreq](../../../../../../../../runs/r2e_static_prep_20260924/v3/public/orange3__4014f2483e3bab0621c9ae0f994947c008183253/worktree/Orange/tests/test_discretize.py)第19—44行真实包含三个方法，覆盖distinct值少于n、100个值分4箱及4实例分4箱；brief的selector和覆盖描述准确。[EqualFreq公开定义](../../../../../../../../runs/r2e_static_prep_20260924/v3/public/orange3__4014f2483e3bab0621c9ae0f994947c008183253/worktree/Orange/preprocess/discretize.py)也明确实际箱数可因distinct值少而降低。题面原有近邻值小复现存在；要求检查真实返回points和interval行为有公开问题依据，不规定实现位置、容差、gold常量或隐藏测试。

固定镜像为`33071677…`、完整配方`9cd596e8…`，base commit为`9403704f…`；agent可执行现有`/testbed/.venv/bin/python`，sysconfig读回`LIBDIR`和`INCLUDEPY`已指向搬迁后的Python路径。[R9 facts](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_build_readback_v1/derived/orange3__4014f2483e3bab0621c9ae0f994947c008183253/facts.json)支持环境身份；它**不证明未来修改源码后构建成功或实际新进程已加载新产物**。构建和测试命令在本轮均未执行。

## 9b：修正默认测试与L1概率测试的区别

初稿SHA为`17133f26e2acd3efdcbddec98a5d4182050428f08b4c50b3772d656f1edde735`，第22—23行称两selector检查“existing default learner and its probability output”。这处事实不准确：公开[test_logistic_regression.py](../../../../../../../../runs/r2e_static_prep_20260924/v3/public/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040/worktree/Orange/tests/test_logistic_regression.py)第21—27行的`test_LogisticRegression`检查默认learner的heart_disease交叉验证准确率，但第60—64行的`test_probability`明确构造`penalty='l1'`，拟合`iris[:100]`，再对`iris[100:]`取概率。后者是L1两类拟合与概率返回检查，不是默认learner概率行为检查。

已向题主指出，作者将当前文本改为分别覆盖default learner和`penalty="l1"` learner的probability output，并明确该L1测试可能在原实现暴露同一问题；修正后SHA见上表，已逐字复核。两个selector本身始终真实，无需改测试命令。**既有场景step ID即使仍叫`public_default_regression`也不能预设RC0**；后续必须按实际selector与完整工具结果读取base可能的1失败1通过。

brief的iris复现以公开题面、`Table('iris')`公开fixture和[learner公开API](../../../../../../../../runs/r2e_static_prep_20260924/v3/public/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040/worktree/Orange/classification/logistic_regression.py)为依据，确实调用拟合而非只构造对象。文字要求查安装库支持的选项及保留已有有效配置，没有指定solver答案、参数重写算法、默认多分类私有断言或概率容差。

版本Python3.7.9／NumPy1.17.5／SciPy1.5.4／scikit-learn0.22.2.post1与[既有9b实际版本记录](../tasks/9b5494e2/probability_precheck_v2.json)及原轨迹、pip freeze一致。固定R9镜像`08470256…`、完整配方`050316e4…`、base commit`43f086f0…`的[R9 facts](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_build_readback_v1/derived/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040/facts.json)记录同来源完整性、SciPy1.5.4 pin和agent解释器可用，支持当前prepared环境描述。这里仅借既有校准的版本身份；不把其私有控制成绩当新版R9的公开开发、真实模型或正式矩阵结果。

## 身份、可见边界与限制

本次定点读取的4014 setup／discretize／pyx／公开测试，以及9b learner／公开测试，SHA全部与各自固定R9`integrity_derived.txt`对应路径一致；公开测试类／方法用AST核名，无导入或执行。每份依据的完整SHA及路径保存在同名JSON。

两份brief均只给现有环境、公开复现和构建／测试位置，要求保留原测试；未发现gold、隐藏评分条目、固定候选或实现算法。外网禁用指agent直连外网，平台受限模型relay例外仍存在。`python`命令要求使用现有venv；未来实际CC的PATH／activation、module identity、重编／加载、完整返回码及清理仍须由新原件核对。

派发时4014矩阵运行中、实际CC未启动，9b新版矩阵与R9公开CC未启动；本轮未收取或评价其完成结果。**表中的命令是待运行建议，不是已跑测试；两个selector或一类测试通过也不能代替整题验收。** 这份说明本身是否实际交付、未来solver是否理解，均没有本轮动态证据。

停止条件：当前两份brief的窄核完成，唯一发现B1已修正并复核；无须为本轮重跑或扩大审查。矩阵／CC原件回收后再单独接续实际结果核查，CPU最终验收、GPU准入、训练资格及模型表现保持未评价。
