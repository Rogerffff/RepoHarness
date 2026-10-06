# Conan Ninja 补充脚本窄审

2026-09-29。审查`rh2/experiments/swegym_cpu_preprobe_20260929/conan_ninja_followup_v1.py`，SHA256 `dadb387b4b06dcee3b7447fda65a70f3beacf1737fefda25d7a0200f65e3f3b0`。**未发现阻断首次受控CPU执行的可达接口、材料或镜像传递错误。仅静态审查通过，不代表下载、构建、Ninja版本或Conan目标已运行成功。** 未运行远端、Docker或项目，也未改脚本/输入。

- **实际接口相容。** 导入的`mixed_followups.py` SHA为`605f4326beb120c00cbbb6a6bbc36f04a03ce6a64f834cd557edc9fba4d799c6`，与脚本硬检查相符。Campaign的构造参数、state/out/plan/recovery/public等字段以及run/inspect/actor/private_behavior/grade签名均吻合。ninja-v1输出以exist_ok=False新建，不回写mixed-v1或inputs_v1；重复执行同名目录会停止。源码及DOWNLOAD/PROBE字符串仅做AST解析，语法有效。
- **源镜像与范围受约束。** 先核现有输入/冻结入口哈希、源manifest/public tag、linux/amd64及此前实际image ID。已读旧actor原件，原运行为ran且容器/网络/relay/stub全部清理正常；其未到达目标不是本次行为已验证。新脚本不使用旧recovery里可选的CMake3.23.3 pin，安装前后要求CMake3.22.1且整份path/realpath/sha/mode/版本返回一致。基础层前缀必须原样保留。
- **单wheel来源及校验链可追溯。** 固定ninja发行版1.10.2.4，源解释器的pip vendored packaging选择兼容非yanked wheel；限定HTTPS files.pythonhosted.org、文件名/URL尾部一致、元数据SHA256及size。pip直接URL下载附hash、no-index/no-deps/no-cache，仅允许一个wheel；容器内和宿主再次核大小/hash，原始PyPI JSON与选择/验证receipt保存。具体wheel及其hash是运行时从固定版本元数据取得，尚非本稿预验的历史固定字节；之后recipe冻结它，不能提前宣称已下载成功或冷重建已验。
- **PATH与实际二进制有探针。** 专用容器显式将testbed/bin放在PATH前，源image Config.User为空，root可写cache mount；其余rootfs只读、tmp有界。PROBE以shutil.which选实际入口、记录文件hash/模式并调用--version；安装前要求Ninja不存在，安装后要求1.10.2系列并保存完整版本字符串。Docker层用同一解释器离线安装该单wheel。分发包1.10.2.4不被误当二进制必须输出1.10.2.4。真正actor的toolchain命令再次调用cmake/ninja，并在真实Ninja Multi-Config目标中验证是否可用。
- **派生镜像实传。** 仅内存plan切至rebuild_dependency_image；`built['Id']`传给actor和私有helper。继承grade在该模式添加`--derived-image`，并核账本image_id_actual相等；因此不会出现仅actor补Ninja、grader仍用缺依赖原镜像的断链。
- **原参考与预算保持。** Conan仍读取原private/reference_bindings.json并验证manifest；正式candidate/gold来源、冻结投影源码核对和参考缺失检查保持。准备900、测试原值、whole grading1800、candidate阶段900、cleanup120及2CPU/4GiB由原Campaign/CPU wrapper沿用。未改公开命令、CMake或生产评分。
- **失败和取消路径会停。** 下载/探针受run超时及进程组TERM/KILL控制，finally按确定容器名rm并查询实际残留；Docker --rm导致rm报“已不存在”时，查询成功且为空才继续，不能机械要求rm0。build离线且force-rm，失败/取消记录build_cleanup=unconfirmed并抛出，不能继续actor；遗留BuildKit/daemon作业须由root核后再恢复，脚本不冒称已自动清净。外层仍按脚本文档用有界systemd管理整个进程组。actor/private/grader继承停止和收尾检查；正式完整行为/清理最终仍须读原件。

运行后最小验收：PyPI原元数据与单wheel receipt；CMake前后不变及Ninja实际路径/version；actor真实RUN_TESTS未知target复现而非缺工具；gold私有目标真正执行Release marker；三行正式实际image/候选导出、完整安装测试、逐参考及清理。仅补依赖并不预判后续行为成功、退化误奖或训练资格。无需为静态审查重写框架或添加实现镜像式单测。
