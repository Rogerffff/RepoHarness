# pack11 Dask 静态审查

7894、9212均归quality_first，ready_for_probe=false。两题核心修复有静态和历史grader正证据，但各有一个具体参考补丁风险，优先安排选择性私有对照建议；本轮未执行或派发。26/27均保持unknown，实际actor与正式训练/评测资格仍未核。

| 题目 | 决定性发现 | 唯一优先下一步 |
| --- | --- | --- |
| 7894 | 删除原轴0再在输出0插入新轴时，原轴1仍位于输出1；gold只按kept_axes压缩depth为{0:1}，会把裁剪移到新轴。具体映射/切片差异已静态确认，实际结果未验。 | 私有base/gold的drop_axis=0/new_axis=0小数组对照，同时记录lazy shape/chunks与compute结果或异常。 |
| 9212 | 不同module但同短类名Color、RED=1的Enum得到相同('Color','RED',1)表示；pure delayed据token建键，可能把可观察不同的输入合并。 | 同一个pure delayed函数返回type(e).__module__，base/gold比较token/key及一次成对compute结果。 |

7894的全部七个新参数都使用非none边界，trim只区分none，因此只重排depth的半修复不能被这些新断言区分。实际完整expected是否接收该候选未运行。新测试先compute也不直接核lazy元数据。主审优先验证boundary漏接收；独立review给出更具体的drop+new_axis潜在新增回归。协调者按已读map_blocks删/插轴、trim及gold映射链采用后者为唯一优先项，保留前者而不加第二项当前CPU要求。不以“未请求任意new_axis扩展”自动豁免可能被破坏的旧输入，也不凭静态推断宣称已证回归。

9212四参数分别构造一种Color，普通Enum/Flag走新注册，IntEnum/IntFlag由MRO先命中int；两个P2P只是局部关系保护。碰撞源于丢失类型身份，非随机MD5碰撞。公开题面已有与gold核心相同的Possible Implementation，属于带修法提示的材料，actual actor是否收到仍unknown，不能称私有泄露或批准训练。Enum hook可能被注册分派绕过，但旧文档/测试已有注册父类优先的契约，不据此单独认定gold违规。任意复杂值的确定性未证，也不强加所有对象必须可hash。

| 历史原件 | no-op | gold | 身份边界 |
| --- | --- | --- | --- |
| 7894：pytest -n0 -rA --color=no dask/array/tests/test_overlap.py | 5failed/75passed，RC1 | 80passed，RC0 | basebf4bc7dd8dc9，Python3.9.19，actual image ID=null |
| 9212：pytest -n0 -rA --color=no dask/tests/test_base.py | 2failed/124passed/3skipped，RC1 | 126passed/3skipped，RC0 | baseaa801de0f427，Python3.10.14，derived ID 5b69493366c23ca4871f1011097747345c49cb6c4f8408cac7fc6a8125fff122 |

两题历史安装RC均0；7894全部80 expected执行，9212全部105 expected执行且无expected skip/xfail。9212的129 collected与parser125并非同一集合，非expected解析未全面审计，不能由总数证明具体塌缩细节或当前参考ID错分。compat_v2b仅改变离线安装pins等环境入口；协调者核过原before/after脚本、recipe/image/build身份，测试补丁和选择命令未变。历史grader与实际actor仍分开。

旧记录的kwargs.pop修改外部字典、depth-only必失败、UUID混称pickle、以注册文本先后推分派、以P2P数量或建议列表推完整性均已纠正。旧跨题8792关系只作为未重验历史报告，未扩读其原件或决定分组；不以无seed直接认定奖励抖动。主审初稿“不同成员数值相等”由delta/review勘误为各参数与各自均值参考比较，封存稿不改。

六份初稿封存后才释放历史/交叉材料，四角色均显式请求Astra/high/fork_turns=none，后端/OS隔离未独立认证。协调者读全部新增patch、关键源码链、角色技术正文、两份完整review和决定性record字段；P2P语义由角色风险抽查，协调者不冒认全读，历史仅选定字段。四份main原card/record归档。见[后续](pack11_followups.md)、[修订来源](coordinator_revisions/pack11_dask/revision_log.json)、[阅读边界](reserve20_coordinator_read_notes.md)。结构和来源校验不认证语义完整性。
