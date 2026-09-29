# R-c 草案 v3 = v2 + 第 5 项（测试 ID 不变）。在原 test_patch 应用后的 tests/test_validators.py 上运行：
# 先执行 v2 的全部修改，再在 F2P 测试体末尾追加：
# 5) PV 左侧的元数据仍被 PV 取代（文档 validators.md:66 与验证器排序示例）：左侧 AfterValidator 不运行，serializer 仍生效。
#    触发反例：独立复核构造的 rv_pv_first（把 PV 挪到元数据最内层）在 v2 下得 1。断言文本按复核 N1 的已验证草案，改为单引号。
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("_edit_revised_test_v2.py")))

p = Path("tests/test_validators.py")
s = p.read_text()
old_tail = '''    m = WithUnsupported(u='abc')
    assert isinstance(m.u, Unsupported)
    assert isinstance(m.model_dump()['u'], Unsupported)
'''
assert s.endswith(old_tail), s[-300:]
s += '''
    # Metadata placed before the plain validator is still replaced by it (documented ordering of validators):
    # an inner validator is not called, while the serializer is still used.
    class Replaced(BaseModel):
        z: Annotated[bool, AfterValidator(lambda v: 1 / 0), serializer, validator]

    replaced = Replaced(z='1')
    assert replaced.z is True
    assert replaced.model_dump() == {'z': '1'}
'''
p.write_text(s)
print("ok revised v3")
