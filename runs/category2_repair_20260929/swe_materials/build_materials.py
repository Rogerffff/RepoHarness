from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path.cwd()
D=Path('docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/swe_materials')
R=Path('runs/category2_repair_20260929/swe_materials')
EXEC=D.parent.parent
START=D.parent/'starting_inventory.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rec(p):
 p=Path(p);return {'path':p.as_posix(),'sha256':sha(p),'bytes':p.stat().st_size}
def out(p,x):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def jsonread(p):return json.loads(Path(p).read_text())
x=jsonread(START);tasks={t['instance_id']:t for t in x['tasks'] if t['source']=='SWE'}
# 这些是逐题工程计划；不改变起始分类，也不以旧准入许可免除修复。
packs=[
 ('01','现成 mypy 旧测试引用','python__mypy-10424 python__mypy-17071'),
 ('02','已有对照的原五题余项','pydantic__pydantic-8511 conan-io__conan-15422'),
 ('03','地区、对象身份及默认值','getmoto__moto-5406 getmoto__moto-6114 pydantic__pydantic-8793'),
 ('04','内外行为及返回参数类型','Project-MONAI__MONAI-2446 Project-MONAI__MONAI-5932 dask__dask-7656'),
 ('05','图像标签及真实返回像素','Project-MONAI__MONAI-4583 Project-MONAI__MONAI-6975'),
 ('06','真实构建与双 profile','conan-io__conan-11594 conan-io__conan-13230'),
 ('07','非示例相等行为','pydantic__pydantic-5662 pydantic__pydantic-6283'),
 ('08','已有公开行为的核心缺口','iterative__dvc-5839 iterative__dvc-6954 python__mypy-10174'),
 ('09','完整投影与标签归属','getmoto__moto-5960 getmoto__moto-6408'),
 ('10','训练模式与完整配置键','Project-MONAI__MONAI-3715 conan-io__conan-12397'),
 ('11','节点身份及文件目录成对控制','iterative__dvc-4166 pandas-dev__pandas-48106'),
 ('12','公开复现与合理解接受性','python__mypy-15184 pandas-dev__pandas-50319 dask__dask-7138'),
]
# 每项：已知对照状态；具体准备；候选矩阵；该题附加阻塞。
plans={
'python__mypy-10424':('已实证 C1 原 reward=1 且四项旧收窄失败；gold 保护旧行为。','复用两个现成 TypeEquals case，追加 P2P 和实际 selector；保留原 F2P 与题面；重新绑定可离线 editable 安装的派生 grader。','noop→0（F2P失败）；gold→1；C1_disable_narrowing→0（新P2P失败）。','D6消费者、固定离线安装及逐步rc未验；不能将09-25失败安装当已完成。'),
'python__mypy-17071':('已实证 C1 原 reward=1；真正unbound被放过，testUnboundTypeVar失败；四份历史成功模型补丁已有负例复核。','复用 check-typevar-unbound.test::testUnboundTypeVar；保留TypeGuard/TypeIs两F2P及两P2P；核collector文件层和安装。','noop→0；gold→1；C1_disable_check→0；可选q36_a1旧成功工件→1（只在接受性需要时加一行）。','D6与离线安装未在当前链验；旧summary rc0是echo/tail外层值，必须读诊断正文。'),
'pydantic__pydantic-8511':('R4：gold与窄修原分均1；gold引入三类继承TypeError，窄修原例/继承均过。','复用R4三类无本地注解继承控制与只读本地annotations窄修；固定Python3.8及pydantic-install配方，先处理pdm/make失败。','noop原例失败；窄修→1；原gold→0（继承保护）；保留正常repr/default/factory。','正确对照存在；安装pdm rc127、make rc2须收口，不能为保gold删护栏。'),
'conan-io__conan-15422':('已有12个正式1；3份真实候选漏默认jobs或多配置；DS a4纯生成器差异按既定范围不判错。','复用CMake3.23.5、真实conan入口及G1修复；默认CPU helper结果、显式2/7、多配置追加纳入断言，并核生成schema能被所用CMake读取。','noop→0；gold及已核正确候选→1；Coder a1/a3与DS a1→0；Q36 a2单核schema兼容原因。','须保留既定生成器范围；工具已修勿重列缺失，schema4兼容风险不能自动算已失败。'),
'getmoto__moto-5406':('CPU18：noop0/gold1/恒East2错解1；East1公开行为失败。','优先复用公开test_create_table_standard的East1 ARN断言，与East2 F2P同版选入；复用原actor/27项证据。','noop→0；gold→1；constant_east2→0（East1 ARN）。','D6新引用实际执行；不扩成全流/备份/CloudFormation回归。'),
'getmoto__moto-6114':('CPU18：noop0/gold1/按B ARN返回A错解1；正式35项只核长度。','把已有双集群请求B/返回Identifier和ARN断言并入版本；复用离线构建资产层。','noop→0；gold→1；返回首对象→0；原名称查询和旧列表行为保留。','不把creating/available状态差异整包判错；跨账号/服务ARN未定范围不混入。'),
'pydantic__pydantic-8793':('CPU18：noop0/gold1/forced_required1；默认5和两项公开旧测试被破坏。','复用create_model+Annotated真实默认值/工厂控制；优先用现成default测试能否直接入P2P，否则将已跑最小断言独立版本化。','noop→0；gold→1；forced_required→0（M().x或is_required）。','保持内外Field默认优先级争议在范围外；不要求内部字典形状。'),
'Project-MONAI__MONAI-2446':('CPU18：noop0/gold1/只保护外部数组列表错解1；内部shuffle/cache顺序错误。','复用NiBabel修复和同输入内外顺序/缓存矩阵；使用确定随机种子或受控排列核实际行为。','noop→0；gold→1；不打乱数组列表候选→0（内部shuffle/cache）。','4GiB出现回收压力须保留；不把私有root行为等同actor权限。'),
'Project-MONAI__MONAI-5932':('CPU18：noop0/gold1/反转引用顺序错解1；长名在前原本正常路径退化。','复用short_first/long_first同一表达式双顺序，核真实解析值；原解析18旧测已验。','noop→0；gold→1；reverse_order→0（long_first）。','别用只无异常替代真实数值；保留requirements初态。'),
'dask__dask-7656':('CPU18：noop0/gold1；opaque错解0，另一候选1但传给delayed函数的dataclass类型改变。','复用现成类型和字段值诊断；加入被调用函数实际收到的参数类型及值，而非只验最终字符串。','noop→0；gold→1；类型退化→0；已被拒opaque不必无变化重跑。','准备曾300秒超时，采用已验setup900；题面修法提示如实披露。'),
'Project-MONAI__MONAI-4583':('CPU18：noop0/gold1/2D-only1；稀疏3D标签被误算背景。','复用2D/3D、numpy/torch、真实标签及dtype矩阵，固定CPU身份；把3D护栏入正式引用。','noop→0；gold→1；2D-only→0（稀疏3D标签）。','CPU校准不声称CUDA已验；尊重dtype/device已有条件。'),
'Project-MONAI__MONAI-6975':('CPU18新正式0/1/1；退化日志正确但丢弃返回图像；旧setup900超时另列。','复用direct/Dataset×True/False/None六行矩阵，核实际像素和有效lazy语义，不约束唯一resample调用次数。','noop→0；gold→1；丢弃返回值候选→0。','沿用已验setup1800版本，测试预算不混改；4GiB压力与并发变化记录。'),
'conan-io__conan-11594':('CPU18：补Ninja后actor可真实配置；noop0/gold1/丢配置1，实际Debug而非Release。','复用Ninja1.10.2.4离线wheel、未改CMake3.22.1及真实CTest marker；核构建配置与marker内容。','noop→0；gold→1；drop_configuration→0（Release未执行）。','需要真实构建资产与双Ninja节点绑定；只命令字符串不够。'),
'conan-io__conan-13230':('CPU18：noop0/gold1/Android-only1，公开Linux host仍生错误Apple flags。','复用Macos build/Linux host双profile的真实conan CLI输出；核精确flags并保留有意raise终止。','noop→0；gold→1；Android-only→0（Linux flags）；原Android参考保留。','无需无关SDK/交叉编译；CLI退出1按目标raise解释，不当环境失败。'),
'pydantic__pydantic-5662':('CPU18：noop0/gold1/all_nonmodels_equal0/any_only1，普通matcher未收到委托。','复用普通true/false/NotImplemented matcher行为，保留dict/object及7项旧比较护栏。','noop→0；gold→1；any_only→0；all_nonmodels_equal→0。','不以精确内部调用次数定义正确性；setup900版本已验。'),
'pydantic__pydantic-6283':('CPU18：noop0/gold1/validate_construct0；非42 TextRoot补充base失败、gold与退化相等。','把已验TextRoot另一合法值的相等断言入版本，保留原test_construct/test_construct_nested无验证护栏。','noop→0；gold→1；validate_construct仍0；可用示例特判候选校准新增断言（尚未执行）。','不能因旧退化已拒绝就免补核心非示例；不要求内部__dict__精确结构。'),
'iterative__dvc-5839':('默认/4/8真实CLI已有行为证据及10个成功候选；硬编码8未评分。','复用pathspec0.8.1和固定YAML，直接核输出小数位数/数值，维持默认5；准备硬编码8窄候选。','noop→0；gold/真实成功候选→1；硬编码8→0预期未实测。','标量float旧不舍入不当新缺陷；不改为有效数字。'),
'iterative__dvc-6954':('公开负int/float/nested、lock更新已验；int-only退化未评分。','复用pygit2 1.14.1，负float及容器负值用parse→run/repro→lock实际输出验证，新增引用避免旧参数空白合键。','noop→0；gold/成功候选→1；int-only→0预期未实测。','非法调用/算术表达式不扩题；旧坏行gold shell引号错误不能当DVC缺陷。'),
'python__mypy-10174':('正式actor原例复现/32旧测通过；公开同开关负例缺正式保护，错解得分未实测。','从已有公开strict-equality用例选同no-strict-optional条件的不重叠成员检查，或复用已提1 in tuple[str]行为；固定派生安装与dirty初态。','noop→0；gold→1且真不重叠报警；关闭全部比较候选→0预期。','不要把未执行错解写误奖；切换strict-optional须清除相反inline flags。'),
'getmoto__moto-5960':('GSI INCLUDE/KEYS_ONLY公开行为已有base/gold；KEYS_ONLY评分缺失，错解未评分；158执行/157解析有合键。','加入两种GSI scan全部项目字段集合/数量和索引投影后原表保持；同时核引用全节点身份。','noop→0；gold→1；漏KEYS_ONLY→0预期；只复用一份目的明确错解。','LSI保持原参考；额外范围争议不扩大；先修已确认节点身份。'),
'getmoto__moto-6408':('原actor题面失败，29旧测过；gold修两已有镜像迁移；首项断言不保护完整tag归属。','用两已有manifest核全部标签集合、唯一归属和来源其它tag；准备只排序、误删其它tag候选。','noop→0；gold→1；只排序/全删来源→0预期。','新manifest目的邻接旧缺陷另列范围，不能静默扩入本包。'),
'Project-MONAI__MONAI-3715':('公开train核心目标缺验收；旧两参考只保护eval/空构造；gold静态合理。','先备CPU合成数据和Ignite，定义forward时training/梯度及with退出恢复断言，保留eval/枚举。','noop→0；gold须先验正对照；eval-only或强制eval→0预期。','actor与可信train运行正对照仍待；未通过不转第1类，不要求完整GPU训练。'),
'conan-io__conan-12397':('cpp_link_args子串可匹配objcpp_link_args；Linux native缺测，只有静态候选。','原Apple与公开Linux clang/libc++配置按完整键读取；复用公开生成helper，不安装无关完整编译器。','noop→0；gold先验证→1；objcpp-only及Apple-only→0预期。','实际actor配置生成待验；顺序接受性只在相关差异发生时调查。'),
'iterative__dvc-4166':('pathspec/networkx actor已修；两参数节点合键，文件/目录成对判据仍不足。','固定pathspec0.8.1/networkx2.3兼容配方及setup.py初态；绑定完整节点，构造混合状态和同名普通文件/目录。','旧gold→1；noop→0；只裁尾/候选应被文件目录护栏拒；混合PASS/FAIL不可覆盖。','公共parser/绑定消费者由D6负责人核；不回溯修改旧分数。'),
'pandas-dev__pandas-48106':('pandas_meta_v3及3组Period绑定已验，剩两tz别名仍各合并2/4节点，六节点均PASS。','复用现行安装/参考版本；列全六tz节点，补完整身份绑定及混合状态/缺席回放，保留3组Period。','noop0/gold1原事实保留；新绑定gold1；混合失败/缺席必须如实拒绝，正常六PASS接受。','尚无候选错分实测；合成摘要控制不冒作真实候选；重编译源码生效检查。'),
'python__mypy-15184':('原SupportsIndex题面例base成功；公开a.C/b.C同名类复现已验且gold修。','中性改公开复现，保留限定名目标；准备新的公开读者，不给其gold/隐藏测试；核assert_type正例及失败文案。','新公开例base失败/gold通过；无歧义短名不退化；旧错误候选按新复现核。','公开材料变更需新版本/干净尝试；旧模型行为不能直接当新题面成绩。'),
'pandas-dev__pandas-50319':('公开允许None或格式，唯一F2P只接受格式；None合理路线未运行；两参数别名合键。','构造局部ValueError→None候选并核原有格式及调用者回退；修oracle接受公开两路线，并补全节点绑定。','noop→0；gold→1；保留其它行为的None解→1；恒None/吞掉其它错误→0预期。','Cython重建/当前actor待验；None路线未证前不声称已解除误拒。'),
'dask__dask-7138':('gold重命名形参使旧array=调用失效，静态确定；旧pytest兼容配方已验。','保留array形参而添加转换主体的兼容候选；加入array=调用和原标量/list/ndarray行为，固定pytest7.4.4配方。','noop原目标失败；兼容候选→1；原gold→0（array=护栏）。','先验兼容正对照/actor；题面自带修法提示保留说明；不要求未承诺零拷贝。'),
}
assert set(plans)==set(tasks)
entries=[]
for order,label,ids in packs:
 for tid in ids.split():
  t=tasks[tid];ev,prep,matrix,block=plans[tid]
  refs=list(t['evidence_refs'])
  for p in list(refs):
   if p.endswith('/result.md') and Path(p[:-3]+'.json').exists():refs.append(p[:-3]+'.json')
  entries.append({'instance_id':tid,'source':'SWE','starting_category':2,'current_category':2,'state':'materials_planned_not_formally_repaired','pack':order,'pack_label':label,'owner':'root（执行与持续题主）；cat2_swe_first_materials（本材料）','known_gap':t['current_situation'],'existing_control_status':ev,'repair_preparation':prep,'recommended_matrix':matrix,'blockers':['D6正式材料版本/选择器/参考消费者由共用机制负责人核验；本目录不实现。',block],'source_next_action':t['next_action'],'material_entries':[rec(p) for p in dict.fromkeys(refs)],'new_owner_decision_required':False,'ordinary_probe_release':'修订版本的相关开发操作、正确解通过、已知漏修被拒/误拒解除、逐节点/安装/源码/清理和独立复核齐全后逐题交接；当前仍第2类。'})
inventory={'schema':'swe_category2_material_plan.v1','as_of':'2026-09-29','status':'preparation_only','starting_inventory':rec(START),'scope':{'tasks':28,'category':2,'excludes_category3':True,'remote_executor':'root','local_execution':'仅文件读取、SHA、JSON与材料一致性核验；未运行项目测试/模型/容器/SSH'},'decision_scan':{'confirmed_new_user_decisions':[],'ordinary_public_requirement_repairs':'已有授权；不新增用户审批','shared_d6':'本材料只登记需求，能力状态由另一agent核定'},'packs':[{'order':a,'name':b,'instance_ids':c.split()} for a,b,c in packs],'tasks':entries}
out(D/'swe_inventory.json',inventory)
md=['# SWE 第2类28题：分批材料与验收顺序','', '整理：2026-09-29。**当前28题均保持第2类；本页是材料计划，不是正式评分修复完成。** 首包为两道mypy，直接复用公开旧测试。常规公开依据修订已在本轮授权内，当前未发现新的必须用户选择事项。D6正式版本入口由共用机制负责人核，本目录不实现公共机制。','', '只按固定起始SWE28题推进，不领取第3类。每个小包完成新版本验收与独立复核即可逐题交接，不等全28题。旧“受限比较＋事后审计”不是普通探针豁免。','', '材料入口：[首包说明](first_mypy_bundle/README.md)、[首包验收计划](first_mypy_bundle/acceptance_plan.md)、[完整机器清单](swe_inventory.json)。','', '## 顺序小包','', '| 顺序 | 范围 | 准备重点 |','| --- | --- | --- |']
for order,label,ids in packs:md.append(f'| {order} | {label}：'+ '、'.join(ids.split())+' | '+('复用现成节点、安装有效性、D6选择器和引用联动。' if order=='01' else '沿用已有环境与对照，按下列逐题缺口作窄修订。')+' |')
md+=['','顺序反映材料成熟度与准备成本；同包不是可盲目并发的授权。root维护唯一远端队列。共用入口未验收时可以继续准备后包材料，不能用私有后检代替正式评分。','', '## 逐题处理','']
for t in entries:
 md += [f'### {t["pack"]} · {t["instance_id"]}', '',f'**缺口：** {t["known_gap"]}',f'**已有依据：** {t["existing_control_status"]}',f'**所需准备：** {t["repair_preparation"]}',f'**建议矩阵：** {t["recommended_matrix"]}',f'**附加阻塞：** {t["blockers"][1]}','**材料：** '+'；'.join(f'[{Path(v["path"]).name}]({"../"*6}{v["path"]})' for v in t['material_entries'] if v['path'].endswith(('/card.md','/result.md'))) +'。完整SHA与所有独立复核/任务二入口见JSON。','']
md+=['## 共用验收与停止条件','','冻结代码、base、镜像/离线资产、原材料与修订材料SHA、命令/预算、实际选择节点和参考绑定。公开面改动、评分改动、环境改动分开记。相关旧证据仅在适用版本复用；没有变化的整套矩阵不机械重跑。','','每行核完整安装子命令、实际源码与模块来源、全部新增及旧引用状态、终止事实和双层清理。正确对照不成立或安装仍不明时保留第2类，并列出具体辨别动作；原分数保留，不能改写为新版本分数。只有验收后才能提出转第1类，训练/留出资格仍另议。','','所有材料已见私有测试与gold，只能用于准备/校准，不能提供给solver或冒作独立公开初判。']
(D/'swe_inventory.md').write_text('\n'.join(md)+'\n')
# 首包：只复制候选、原始评分/补丁与诊断脚本来源，不生成重复.test。
bundle={'schema':'swe_first_mypy_materials.v1','version':'mypy-p2p-reuse-v1-prepared','as_of':'2026-09-29','status':'prepared_not_executed_not_runtime_schema','public_revision':'none','test_patch_revision':'none','production_score_modified':False,'requires_runtime_adapter':'D6必须同时消费追加引用、完整节点选择及可信恢复；本manifest不是已接线配置','tasks':[]}
receipts=[]
history=[]
for num,batch,kind,c1,casefile,casenames in [
 ('10424','01','semantic','C1_disable_narrowing','check-isinstance.test',['testTypeEqualsCheckUsingIs','testTypeEqualsNarrowingUnionWithElse']),
 ('17071','02','behavior','C1_disable_check','check-typevar-unbound.test',['testUnboundTypeVar'])]:
 tid='python__mypy-'+num; qroot=Path(f'runs/swegym_quality_batch{batch}_20260921_v2');pub=qroot/'public'/tid;pri=qroot/'private'/tid
 old=Path('runs/task2_swegym_dev_20260925/runs')/kind/('mypy'+num); instal=Path('runs/env_recipe_repair_20260919/install_wave1/tasks')/tid
 dest=R/'first_mypy_bundle'/tid;dest.mkdir(parents=True,exist_ok=True)
 grading=jsonread(pri/'grading.json');identity=jsonread(pub/'base_identity.json'); image=jsonread(instal/'image.json')
 copies={}
 for src,name in [(pri/'gold.patch','gold.patch'),(old/c1/'candidate.diff',c1+'.patch'),(pri/'test.patch','original_test.patch'),(pri/'grading.json','original_grading.json'),(pub/'user_prompt.txt','original_user_prompt.txt')]:
  target=dest/name;shutil.copyfile(src,target);copies[name]={'source':rec(src),'frozen':rec(target)};receipts.append(rec(src))
 if num=='17071':
  src=old/'q36_a1/candidate.diff';target=dest/'q36_a1.patch';shutil.copyfile(src,target);copies['q36_a1.patch']={'source':rec(src),'frozen':rec(target)}
 casepath=pub/'base/test-data/unit'/casefile;lines=casepath.read_text().splitlines(keepends=True);cases=[]
 for name in casenames:
  starts=[i for i,l in enumerate(lines) if l.strip()==f'[case {name}]'];assert len(starts)==1
  i=starts[0];j=next((j for j in range(i+1,len(lines)) if lines[j].startswith('[case ')),len(lines));body=''.join(lines[i:j])
  node='mypy/test/testcheck.py::TypeCheckSuite::'+(casefile+'::' if num=='17071' else '')+name
  cases.append({'case':name,'node_id':node,'source':rec(casepath),'start_line':i+1,'end_line':j,'case_bytes_sha256':hashlib.sha256(body.encode()).hexdigest(),'source_is_existing_public_test':True,'new_test_body':False,'assertions':('Any→int；完整诊断输出比较' if name.endswith('UsingIs') else 'Union[int,str]正分支→int；else保持Union；完整诊断输出比较' if 'Union' in name else '仅返回T、带bound U、带约束V的真实未绑定变量均须诊断；并核U的upper-bound说明')})
 p2p=grading['pass_to_pass']+[c['node_id'] for c in cases];allnodes=grading['fail_to_pass']+p2p
 selector=' or '.join(n.split('::')[-1] for n in allnodes)
 for path in [pub/'base_identity.json',pub/'public_bundle.json',pri/'source_refs.json',casepath,pub/'base/mypy/test/testcheck.py',pub/'base/mypy/test/data.py',instal/'image.json',instal/'build.log',Path('rh2/experiments/task2_swegym_dev_20260925/specs')/('sem_mypy10424.json' if num=='10424' else 'spec_mypy17071.json')]:receipts.append(rec(path))
 # 原件逐文件绑定，历史结果读正文+账本，不由summary.json外层RC推断。
 for variant in ['base','gold',c1]+(['q36_a1'] if num=='17071' else []):
  for p in sorted((old/variant).rglob('*')):
   if p.is_file():receipts.append(rec(p))
 for variant in ['noop','gold']:
  for p in sorted((instal/variant).rglob('*')):
   if p.is_file():receipts.append(rec(p))
 histrows=[]
 for origin,variant in [(instal,'noop'),(instal,'gold')]+([(old,'gold')] if num=='10424' else [])+[(old,c1)]:
  lp=origin/variant/('ledger.jsonl' if origin==instal else 'grade/ledger.jsonl');j=json.loads(lp.read_text().splitlines()[0]);logp=next(lp.parent.glob('eval_logs/*.eval.log')); text=logp.read_text();summary=[]
  in_seg=False
  for line in text.splitlines():
   if line==">>>>> Start Test Output":in_seg=True
   if line.startswith(('PASSED ','FAILED ','SKIPPED ','XFAIL ','XPASS ')):
    summary.append(line)
  histrows.append({'variant':variant,'source_family':'install_wave1' if origin==instal else 'task2_0925','ledger':rec(lp),'log':rec(logp),'report':j['report'],'install':j['install'],'complete_summary_status_lines':summary,'actual_import':j.get('observations',{}).get('RH2_OBS_IMPORT_PATH'),'historical_scripts_digest':j.get('scripts_digest'),'image_identity':j.get('image_identity'),'candidate_patch_sha256':j.get('candidate',{}).get('patch_sha256'),'reference_diagnostics':j.get('verdict_diagnostics'),'cleanup':j.get('cleanup'),'install_interpretation':('完整旧日志有build/install success，仍须核当前镜像和资产可用' if origin==instal else 'editable build隔离环境缺离线setuptools，子命令rc1；后续测试真实执行但非完整安装通过')})
 history.append({'instance_id':tid,'formal_history':histrows,'behavior_summary':{'base':'10424原例<nothing>/普通int；17071合法guard/is仍报unbound，真实unbound正确报警','gold':'10424原例Type[C]/普通int/旧6测通过；17071合法guard/is通过、真实unbound报警、旧135P/1XFAIL','C1':'10424原例通过但普通int变Union、旧4F2P；17071真正unbound诊断消失且testUnboundTypeVar失败（1F134P1XFAIL）'},'behavior_summary_scope':'逐题字段的行为以本目录README和源.out为准，未新增运行'})
 matrix=[{'candidate':'noop','expected_reward':0,'expected_f2p_pass':0,'expected_p2p_fail':0},{'candidate':'gold','expected_reward':1,'expected_f2p_pass':len(grading['fail_to_pass']),'expected_p2p_fail':0},{'candidate':c1,'expected_reward':0,'expected_f2p_pass':len(grading['fail_to_pass']),'expected_p2p_fail':len(cases),'expected_fail_nodes':[c['node_id'] for c in cases]}]
 bundle['tasks'].append({'instance_id':tid,'base_commit':identity['base_commit'],'base_tree':identity['base_tree'],'mypy_version':grading['version'],'python_version':grading['python_version'],'original_public':rec(pub/'public_bundle.json'),'original_grading':rec(pri/'grading.json'),'source_bindings':jsonread(pri/'source_refs.json'),'unchanged_test_patch':rec(pri/'test.patch'),'public_revision':None,'test_patch_revision':None,'frozen_assets':copies,'additional_p2p':cases,'revised_fail_to_pass':grading['fail_to_pass'],'revised_pass_to_pass':p2p,'expected_reference_count':len(allnodes),'required_collected_node_ids':allnodes,'suggested_eval_argv':['python','-m','pytest','-n0','-rA','-p','no:cacheprovider',*allnodes],'fallback_existing_k_selector':selector,'selection_note':'显式node优先；若D6沿用-k，必须核collected全集准确对应上述完整node集合。只改reference不会让原test.patch选择器执行新增P2P。','restore_requirement':{'unchanged_official_patch_targets':'按original_test.patch恢复','additional_trusted_public_file':str(Path('test-data/unit')/casefile),'required_source_sha256':sha(casepath),'reason':'候选投影后恢复此公开测试的固定base字节再选择节点，避免新增P2P文件被候选改写；由D6机制提供。'},'install_proposal':{'status':'reuse_historical_recipe_pending_current_verification','historical_image_record':rec(instal/'image.json'),'base_image_id':image['base_id'],'base_digest':image['base_digest'],'historical_derived_image_id':image['image_id'],'recipe':image['recipe'],'wheel_pins':image['pins'],'asset_bytes_available_here':False,'notes':['wheel pins不是完整依赖锁；必须保持原base镜像初态并核wheel实际SHA。','保留隔离构建、网络deny_all；不以关闭build isolation或放网掩盖缺件。','先在固定派生grader核requirements和editable每步成功，再跑三候选。','本材料未验证远端镜像当前存在/已拉取，不新建或修改镜像。']},'matrix':matrix,'optional_acceptance_control':({'candidate':'q36_a1','expected_reward':1,'when':'同D6版本需要一份历史真实成功补丁接受性控制时，非必做全4份重跑'} if num=='17071' else None),'release_status':'category2_pending_install_d6_formal_matrix_independent_review'})
out(D/'first_mypy_bundle/materials_manifest.json',bundle)
out(R/'first_mypy_bundle/historical_evidence_readback.json',history)
receipts=list({v['path']:v for v in receipts}.values());out(R/'first_mypy_bundle/source_receipts.json',{'schema':'source_receipts.v1','as_of':'2026-09-29','files':receipts,'count':len(receipts),'note':'本地源原件SHA；不冒称本轮远端对账。'})
# 把现成诊断命令的原始文本复制成审阅JSON，正式参考不依赖其echo/tail包装。
for name in ['sem_mypy10424.json','spec_mypy17071.json']:
 src=Path('rh2/experiments/task2_swegym_dev_20260925/specs')/name;shutil.copyfile(src,R/'first_mypy_bundle'/('historical_'+name))
print(json.dumps({'tasks':len(entries),'packs':len(packs),'first_bundle_tasks':len(bundle['tasks']),'source_receipts':len(receipts)},ensure_ascii=False))
# 收口既有安装修复：按历史清单匹配每个pin的wheel SHA，不重新设计安装。
asset_path=Path('runs/env_recipe_repair_20260919/install_wave1/assets_manifest.json')
plan_path=asset_path.parent/'plan.json'
catalog_path=EXEC/'env_recipe_repair_20260919/repair_catalog.json'
assets=jsonread(asset_path);install_plans=jsonread(plan_path);catalog=jsonread(catalog_path)
install_doc=[]
for t in bundle['tasks']:
 tid=t['instance_id'];ip=t['install_proposal'];wheels=[]
 for pkg,version in ip['wheel_pins'].items():
  match=[a for a in assets if a['path'].split('/')[2]==pkg+'=='+version];assert len(match)==1
  a=dict(match[0]);a['distribution']=pkg;a['version']=version;a['original_manifest']=rec(asset_path);a['local_payload_exists']=(asset_path.parent/a['path']).is_file();wheels.append(a)
 ip.update({'status':'historically_verified_install_wave1_reuse_required','recipe_id':'install-wave1:'+tid,'historical_plan_entry':next(v for v in install_plans if v['instance_id']==tid),'asset_manifest':rec(asset_path),'required_wheels':wheels,'repair_catalog':{'source':rec(catalog_path),'entry':{k:v for k,v in next(v for v in catalog['tasks'] if v['instance_id']==tid).items() if k in ['instance_id','issues','status','selected_batch','checks']}},'reuse_entry':rec(Path('rh2/experiments/env_recipe_repair_20260919/run_install_wave1.py')),'new_cpu_scope':'优先恢复/绑定既有派生grader和相同base初态，补C1及新增公开case的诊断证据；不把已有gold/noop无变化矩阵当待重新发明的环境修复。新D6评分版本启用后再做版本矩阵。'})
 bad='C1_disable_narrowing' if tid.endswith('10424') else 'C1_disable_check';kind='semantic' if tid.endswith('10424') else 'behavior';old=Path('runs/task2_swegym_dev_20260925/runs')/kind/('mypy'+tid.split('-')[-1])
 logs=[]
 for var in (['gold',bad] if tid.endswith('10424') else [bad]):
  lp=old/var/'grade/ledger.jsonl';j=jsonread(lp);logp=next(lp.parent.glob('eval_logs/*.eval.log'));lines=logp.read_text().splitlines();i=next(i for i,l in enumerate(lines) if l=='+ python -m pip install -e .');end=next(k for k in range(i+1,len(lines)) if lines[k].startswith('RH2_INSTALL_CMD_FAILED='))+1
  logs.append({'variant':var,'ledger':rec(lp),'log':rec(logp),'line_start':i+1,'line_end':end,'install_failure_excerpt':'\n'.join(lines[i:end]),'image_ref':j['image_ref'],'image_local_build':j['image_local_build'],'derived_image_recipe':j['derived_image_recipe'],'install_failed_commands':j['install']['install_failed_commands'],'last_rc':j['install']['install_rc_last_command'],'diagnosis':'PEP517 editable隔离构建尝试公网查setuptools，deny_all下DNS失败，最终找不到setuptools>=40.6.2；后续hash -r/其他pip命令把段末置0。09-19离线资产修复未消费。'})
 t['installation_failure_evidence']=logs
 for c in t['additional_p2p']:
  proof=old/bad/('public_typeequals_tests.out' if tid.endswith('10424') else 'public_tests.out');assert 'FAILED '+c['node_id'] in proof.read_text();c['node_id_observed_in_historical_real_pytest']=rec(proof);c['fresh_collect_status']='not_run_pending_root'
 install_doc.append({'instance_id':tid,'recipe':ip,'failure_evidence':logs})
 # selector与可信保护的版本要求写在同一个拟用物料对象中。
 t['source_protection_status']='required_not_implemented_here'
out(D/'first_mypy_bundle/materials_manifest.json',bundle)
out(D/'first_mypy_bundle/installation_reuse.json',install_doc)
rr=jsonread(R/'first_mypy_bundle/source_receipts.json')
for p in [asset_path,plan_path,catalog_path,Path('rh2/experiments/env_recipe_repair_20260919/run_install_wave1.py')]:rr['files'].append(rec(p))
rr['files']=list({v['path']:v for v in rr['files']}.values());rr['count']=len(rr['files']);out(R/'first_mypy_bundle/source_receipts.json',rr)
# 摘要只用各题自己的行为，不混同不同mypy版本。
history[0]['behavior_summary']={'base':'原例<nothing>；普通int分支收窄正确；6个TypeEquals旧测通过。','gold':'原例Type[C]；普通int分支收窄正确；6个TypeEquals旧测通过。','C1':'原例Type[C]但普通int变Union；TypeEquals旧测4失败/2通过。'}
history[1]['behavior_summary']={'base':'合法TypeGuard/TypeIs仍报unbound；真实unbound报警；135P/1XFAIL。','gold':'合法TypeGuard/TypeIs无错误并保留str推断；真实unbound报警；135P/1XFAIL。','C1':'合法原例表面通过；TypeGuard[U]→T错误被接受；testUnboundTypeVar失败，134P/1XFAIL。'}
out(R/'first_mypy_bundle/historical_evidence_readback.json',history)
