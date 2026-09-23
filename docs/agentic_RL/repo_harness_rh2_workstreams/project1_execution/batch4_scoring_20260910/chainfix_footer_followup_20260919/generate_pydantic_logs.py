"""沿 pydantic 固定配方的 verbose 输出再跑同一组有界日志对照。"""
from pathlib import Path
import generate_pretty_logs as generator

generator.HERE = Path(__file__).resolve().parent / "pydantic_runtime"
generator.HERE.mkdir()
original_run = generator.run

def run(repo, *, pretty=True, flags=()):
    if pretty:
        flags = ("--tb=short", "-vv", "-o", "console_output_style=classic", "--no-header", *flags)
    return original_run(repo, pretty=pretty, flags=flags)

generator.run = run
generator.main()
