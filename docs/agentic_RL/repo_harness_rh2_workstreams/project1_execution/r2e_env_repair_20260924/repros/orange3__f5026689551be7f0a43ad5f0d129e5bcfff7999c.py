"""公开复现：orange3 f5026689 —— OWDataSets.migrate_settings 不把 selected_id 里的反斜杠换成正斜杠。

依据：公开题面示例（settings = {"selected_id": "dir1\\bar"}; OWDataSets.migrate_settings(settings, 0)），原样改写。
只调用类方法，不创建 widget、不访问网络，不写工作区。
"""
import sys
import traceback


def main():
    from Orange.widgets.data.owdatasets import OWDataSets

    settings = {"selected_id": "dir1\\bar"}
    OWDataSets.migrate_settings(settings, 0)
    sel = settings.get("selected_id")
    print(f"SELECTED_ID_AFTER={sel!r} EXPECTED='dir1/bar'")
    if sel != "dir1/bar":
        return 1, "backslash not converted by migrate_settings"
    return 0, "selected_id migrated to forward slashes"


if __name__ == "__main__":
    try:
        observed, why = main()
    except Exception:  # 脚本自身或环境出错
        traceback.print_exc()
        print("REPRO_OBSERVED=0")
        print("REPRO_REASON=unexpected_exception")
        sys.exit(3)
    print(f"REPRO_OBSERVED={observed}")
    print(f"REPRO_REASON={why}")
    sys.exit(0)
