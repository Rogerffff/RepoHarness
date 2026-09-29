# Batch02 方法与例外记录

实际派发以dispatch.json和总协调者明确消息为准，不改材料manifest的预备状态。沿用首批已核方法，所有角色新上下文；同仓reviewer先封存全包初判，再开放任一主审结论。37项首批封存及已验收产物不触碰。

材料v2显式登记Moto5752/5134的Terraform gitlink缺口；按相关性判断，不能据导出缺失推出运行环境不存在。CPU建议选择性，不给每题强制构造反例。

只读材料核验已完成并存入assignments.material_verification：36源行、19188个导出blob及mode、24日志/账本匹配；2个未导出gitlink与材料身份一致。关键代码和manifest摘要匹配，无失配。

环境原件定位：mypy17071/11236为install_wave1离线wheel增层；10308指定运行另经materials_v2的--materials流程，补两处明确的私有fixture并保留原断言，原/修订grading digest均在逐运行materials.json。不能把10308称为单靠派生镜像的原始材料运行；主审/reviewer在初判前获得本题这些原件，区别已修环境/材料与质量判断，不重新把既有已登记修订报作新执行。

未来重放命令静态核验：wrapper的 --code-root 指向 rh2 目录；10308 的 --materials 应传 materials_v2/materials.json（version+tasks 映射），逐运行 materials/materials.json 是审计输出，不能直接作为输入。输入和输出均保存身份，不能仅看同名文件。验证仅阅读代码，尚未执行。

Pandas48106 的指定历史运行还使用 reference-bindings-v1，不仅是 pandas_meta_v3 安装修订。主审/reviewer 初判阶段须读取本题 bindings 输入、解析代码及两个逐运行审计输出；未来重放需明确 --bindings。它把3个来源别名对应到7个完整 pytest node，任一成员缺席不能沿用旧碰撞末值。原始 reference 分组保留；其正确性与实际命中由逐题复核说明，不能把命令遗漏绑定后的分差归因于候选。

历史原件检索再确认：mypy10308的旧L1未写出完整stage1路径，但协调者按 instance_id 在已知stage1日志根定位到了 gold/empty 原件，raw来源第193行也匹配1898字符hints。主审将修正report-only措辞；封存初稿保持不变。旧摘要缺路径不等于工件缺失，应补任务ID限定的原件索引检索。

- DVC最终复核：保留是否允许沉默的合理解释，不能由gold未发消息直接定错；参数0的可见结果不等于先排除再重包含。只更新短卡/JSON，不回写封存稿。固定grader的oracle实验可先做；actor开发验证是单独用途条件。1681核心三路比较，自然一律dot候选为可选扩展，不机械叠加门槛。

- pandas56849主审在本题历史开放后误用head -3查看历史collide_detail.json结构，看到48106题键与scoring_keys_with_collision=2，随即报告并停止。56849封存稿不改，后历史产物记录暴露；48106/53958未开始主审，撤回原派发并改由新鲜上下文接手。不给新主审该历史数字，不重做已完成任务。

- mypy最终复核：10308候选明确绑定既存materials-v2而非原prepared；10308目标是无internal error，不能偷换为零普通诊断。17071的TypeIs有公开仓库依据，规范分歧与实测误拒分开。11236已有六条负断言，zip-only等假说不机械变准入必测。三题固定grader语义实验与正式actor资格解耦，封存初稿不回写。
- pandas独立reviewer报告完整显示授权environment_record，包含环境summary和history路径索引；协调者确认history字段本身仅为版本/路径/roles。初判披露实际环境摘要暴露，按原日志核实，不打开质量历史路径；不将其称完全未见环境结论，也不要求重新审全题。

- Moto最终复核：7584原版因公开流程/gold和精确报文冲突，仅保留已知争议诊断；5752原hints除拼写还缺命中continue，初稿中的独立窄实现可保留，历史差异稿不回写；5134没有强造反例。5752/7584后期公开base包含先前两题修法，版本包含关系与重复题/实际泄漏分开。固定grader诊断不前置要求actor合格。

- Pandas最终复核：56849的warning为re.search且freq没有直接断言，优先规范名M警告对照；48106剩余2组tz合并不推翻原全PASS，混合/缺席诊断必须按真实摘要顺序、区分合成控制与真实候选；53958保留命名空间分歧，协调者采纳reviewer的singleton误导出优先实验，因其直接检验无争议的类型目标，不把两个候选都设必测。后期base含48106/53958修法，版本关系不等同重复或实际泄漏。三份封存稿不回写。
