def value() -> int:
    from pathlib import Path

    counter = Path(".baseline_invocation_count")
    count = int(counter.read_text(encoding="utf-8")) if counter.exists() else 0
    counter.write_text(str(count + 1), encoding="utf-8")
    if count >= 2:
        return 0
    return 1
