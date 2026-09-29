import coverage

# Run coverage while executing code whose filename cannot be encoded in UTF-8
cov = coverage.Coverage()
cov.start()
exec(compile("pass", "\udcff.py", "exec"))
cov.stop()
cov.save()  
print('REVISED_EXAMPLE_SAVE_OK')
