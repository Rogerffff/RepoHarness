# 题面示例逐字（只补 import coverage，并用临时数据文件），在 /tmp 下运行
import os
import coverage
os.chdir("/tmp")
# Create a file with a non-UTF8 encodable filename
exec(compile("pass", "\udcff.py", "exec"))

# Run coverage and attempt to save data
cov = coverage.Coverage(data_file="/tmp/literal_example.coverage")
cov.start()
exec("pass")
cov.stop()
cov.save()  # This line raises UnicodeEncodeError
print("LITERAL_EXAMPLE_SAVE_OK measured_files=%s" % ascii(sorted(cov.get_data().measured_files())))
