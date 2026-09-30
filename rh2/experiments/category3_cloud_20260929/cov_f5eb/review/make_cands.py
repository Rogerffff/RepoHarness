# 复核者候选生成：以 base 的 coverage/jsonreport.py、results.py 为底稿做文本替换（每处替换都断言恰好命中一次）
import pathlib, sys
BASE = pathlib.Path(sys.argv[1])            # base 源码目录（含 coverage/）
OUT = pathlib.Path(sys.argv[2])             # review/cands
jr = (BASE / "coverage/jsonreport.py").read_text()
rs = (BASE / "coverage/results.py").read_text()

def rep(s, old, new):
    assert s.count(old) == 1, (old[:60], s.count(old))
    return s.replace(old, new)

def mk(name, files):
    for rel, text in files.items():
        p = OUT / name / "files" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

TOT_OLD = """                'num_partial_branches': self.total.n_partial_branches,
            })
"""
FILE_OLD = """                'num_partial_branches': nums.n_partial_branches,
            })
"""
INIT_OLD = """        self.report_data = {}
"""
LOOP_OLD = """        measured_files = {}
        for file_reporter, analysis in get_analysis_to_report(self.coverage, morfs):
"""
def tot(cov_expr, mis_expr, s):
    return rep(s, TOT_OLD, TOT_OLD.replace("            })\n", "                'covered_branches': %s,\n                'missing_branches': %s,\n            })\n" % (cov_expr, mis_expr)))
def perfile(cov_expr, mis_expr, s):
    return rep(s, FILE_OLD, FILE_OLD.replace("            })\n", "                'covered_branches': %s,\n                'missing_branches': %s,\n            })\n" % (cov_expr, mis_expr)))

# ---------- 合理实现 ----------
# rv_accum：只改 totals；report_one_file 里用 Numbers 的现成属性按文件累加（+=）
s = rep(jr, INIT_OLD, INIT_OLD + "        self.covered_branches = 0\n        self.missing_branches = 0\n")
s = rep(s, "        if coverage_data.has_arcs():\n            reported_file['summary'].update({",
        "        if coverage_data.has_arcs():\n            self.covered_branches += nums.n_executed_branches\n            self.missing_branches += nums.n_missing_branches\n            reported_file['summary'].update({")
mk("rv_accum", {"coverage/jsonreport.py": tot("self.covered_branches", "self.missing_branches", s)})

# rv_sumlist：只改 totals；循环中收集 Analysis，结束后求和
s = rep(jr, LOOP_OLD, "        measured_files = {}\n        analyses = []\n        for file_reporter, analysis in get_analysis_to_report(self.coverage, morfs):\n            analyses.append(analysis)\n")
s = tot("sum(a.numbers.n_executed_branches for a in analyses)", "sum(a.numbers.n_missing_branches for a in analyses)", s)
mk("rv_sumlist", {"coverage/jsonreport.py": s})

# rv_results：在 results.Numbers 里新增存储字段 n_covered_branches（__init__/init_args/__add__ 都改对），totals 读它
r = rep(rs, "                    n_branches=0, n_partial_branches=0, n_missing_branches=0\n                    ):",
        "                    n_branches=0, n_partial_branches=0, n_missing_branches=0,\n                    n_covered_branches=0,\n                    ):")
r = rep(r, "        self.n_missing_branches = n_missing_branches\n\n    def init_args",
        "        self.n_missing_branches = n_missing_branches\n        self.n_covered_branches = n_covered_branches\n\n    def init_args")
r = rep(r, "            self.n_branches, self.n_partial_branches, self.n_missing_branches,\n        ]",
        "            self.n_branches, self.n_partial_branches, self.n_missing_branches,\n            self.n_covered_branches,\n        ]")
r = rep(r, "        nums.n_missing_branches = (\n            self.n_missing_branches + other.n_missing_branches\n            )\n        return nums",
        "        nums.n_missing_branches = (\n            self.n_missing_branches + other.n_missing_branches\n            )\n        nums.n_covered_branches = (\n            self.n_covered_branches + other.n_covered_branches\n            )\n        return nums")
r = rep(r, "            n_missing_branches=n_missing_branches,\n        )",
        "            n_missing_branches=n_missing_branches,\n            n_covered_branches=n_branches - n_missing_branches,\n        )")
mk("rv_results", {"coverage/results.py": r, "coverage/jsonreport.py": tot("self.total.n_covered_branches", "self.total.n_missing_branches", jr)})

# rv_sym_xml：对称（每文件＋totals），按 XML 报告的 branch_stats() 口径逐文件计算，totals 用累加器
s = rep(jr, INIT_OLD, INIT_OLD + "        self.covered_branches = 0\n        self.missing_branches = 0\n")
s = rep(s, "        if coverage_data.has_arcs():\n            reported_file['summary'].update({",
        "        if coverage_data.has_arcs():\n            stats = analysis.branch_stats().values()\n            file_covered = sum(taken for _, taken in stats)\n            file_missing = sum(total - taken for total, taken in stats)\n            self.covered_branches += file_covered\n            self.missing_branches += file_missing\n            reported_file['summary'].update({")
s = perfile("file_covered", "file_missing", s)
mk("rv_sym_xml", {"coverage/jsonreport.py": tot("self.covered_branches", "self.missing_branches", s)})

# ---------- 错误候选 ----------
# wr_loopvar：totals 用循环结束后残留的 analysis（最后一个文件）——只处理单文件
s = rep(jr, LOOP_OLD, "        measured_files = {}\n        analysis = None\n        for file_reporter, analysis in get_analysis_to_report(self.coverage, morfs):\n")
mk("wr_loopvar", {"coverage/jsonreport.py": tot("analysis.numbers.n_executed_branches", "analysis.numbers.n_missing_branches", s)})

# wr_first：计数器为 0 时才赋值（本意“初始化”），实际只记住第一个有分支的文件——依赖文件顺序
s = rep(jr, INIT_OLD, INIT_OLD + "        self.covered_branches = 0\n        self.missing_branches = 0\n")
s = rep(s, "        if coverage_data.has_arcs():\n            reported_file['summary'].update({",
        "        if coverage_data.has_arcs():\n            if not self.covered_branches and not self.missing_branches:\n                self.covered_branches = nums.n_executed_branches\n                self.missing_branches = nums.n_missing_branches\n            reported_file['summary'].update({")
mk("wr_first", {"coverage/jsonreport.py": tot("self.covered_branches", "self.missing_branches", s)})

# wr_split：missing 取最后一个文件，covered = num_branches - missing（保住“和等于 num_branches”，但拆分错）
s = rep(jr, LOOP_OLD, "        measured_files = {}\n        analysis = None\n        for file_reporter, analysis in get_analysis_to_report(self.coverage, morfs):\n")
mk("wr_split", {"coverage/jsonreport.py": tot("self.total.n_branches - analysis.numbers.n_missing_branches", "analysis.numbers.n_missing_branches", s)})

# wr_inproc：只有本对象亲自测量（_collector 存在）才输出两键——只在 API 进程内路径正确，CLI/读回路径缺键
s = rep(jr, TOT_OLD + "\n", TOT_OLD + "            if self.coverage._collector is not None:\n                self.report_data[\"totals\"].update({\n                    'covered_branches': self.total.n_executed_branches,\n                    'missing_branches': self.total.n_missing_branches,\n                })\n\n")
mk("wr_inproc", {"coverage/jsonreport.py": s})

# wr_brlines：按“分支行”而不是“分支去向”计数（全走到的行算 covered，有去向没走到的行算 missing）
s = rep(jr, INIT_OLD, INIT_OLD + "        self.covered_branches = 0\n        self.missing_branches = 0\n")
s = rep(s, "        if coverage_data.has_arcs():\n            reported_file['summary'].update({",
        "        if coverage_data.has_arcs():\n            for total, taken in analysis.branch_stats().values():\n                if taken == total:\n                    self.covered_branches += 1\n                else:\n                    self.missing_branches += 1\n            reported_file['summary'].update({")
mk("wr_brlines", {"coverage/jsonreport.py": tot("self.covered_branches", "self.missing_branches", s)})

# wr_sym_c2file（选 A 时相关）：totals 正确；每文件两键用“部分分支”口径（covered = n_branches - partial，missing = partial）
s = tot("self.total.n_executed_branches", "self.total.n_missing_branches", jr)
mk("wr_sym_c2file", {"coverage/jsonreport.py": perfile("nums.n_branches - nums.n_partial_branches", "nums.n_partial_branches", s)})

# wr_sym_last（选 A 时相关）：每文件两键正确；totals 取最后一个文件
s = rep(jr, LOOP_OLD, "        measured_files = {}\n        analysis = None\n        for file_reporter, analysis in get_analysis_to_report(self.coverage, morfs):\n")
s = tot("analysis.numbers.n_executed_branches", "analysis.numbers.n_missing_branches", s)
mk("wr_sym_last", {"coverage/jsonreport.py": perfile("nums.n_executed_branches", "nums.n_missing_branches", s)})
print("ok")

# wr_alldata：totals 的两个计数按数据里“全部被测文件”计算，而不是按本次报告的文件（忽略 morfs / --include / --omit）
s = rep(jr, TOT_OLD, """                'num_partial_branches': self.total.n_partial_branches,
                'covered_branches': sum(self.coverage._analyze(f).numbers.n_executed_branches
                                        for f in coverage_data.measured_files()),
                'missing_branches': sum(self.coverage._analyze(f).numbers.n_missing_branches
                                        for f in coverage_data.measured_files()),
            })
""")
mk("wr_alldata", {"coverage/jsonreport.py": s})
print("ok2")

# wr_alldata_proj：同 wr_alldata，但先滤掉 site-packages 下的文件（模拟“只算项目文件”）；仍忽略本次报告选了哪些文件
s = rep(jr, TOT_OLD, """                'num_partial_branches': self.total.n_partial_branches,
                'covered_branches': sum(self.coverage._analyze(f).numbers.n_executed_branches
                                        for f in coverage_data.measured_files()
                                        if 'site-packages' not in f),
                'missing_branches': sum(self.coverage._analyze(f).numbers.n_missing_branches
                                        for f in coverage_data.measured_files()
                                        if 'site-packages' not in f),
            })
""")
mk("wr_alldata_proj", {"coverage/jsonreport.py": s})
print("ok3")
