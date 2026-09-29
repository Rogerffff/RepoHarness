"""P4 public repro: scrapy e9387529 (base 2514973242e3, Scrapy 1.1.0dev1 on Python 3.9).

Written from the public prompt only (E06). Prompt: PythonItemExporter(binary=True) exports
bytes values but str keys; expected {b'name': b'John\\xc2\\xa3', b'age': b'22'}.
Inference: TestItem is the prompt's item with fields name / age (defined here).
"""
import sys
import scrapy
from scrapy.item import Field, Item


class TestItem(Item):
    name = Field()
    age = Field()


def main():
    print("SCRAPY_FILE", scrapy.__file__, getattr(scrapy, "__version__", "?"))
    try:
        from scrapy.exporters import PythonItemExporter
    except ImportError:
        from scrapy.contrib.exporter import PythonItemExporter
    try:
        exported = PythonItemExporter(binary=True).export_item(TestItem(name="John£", age="22"))
    except Exception as e:  # observe only
        print(f"EXPORT=raised {type(e).__name__}: {e}")
        print("REPRO_OBSERVED=0")
        print("REPRO_REASON=export raised; the prompt describes str keys, not an exception")
        return 0
    print("EXPORTED", exported)
    print("KEY_TYPES", sorted({type(k).__name__ for k in exported}),
          "VALUE_TYPES", sorted({type(v).__name__ for v in exported.values()}))
    observed = any(isinstance(k, str) for k in exported)
    print(f"REPRO_OBSERVED={int(observed)}")
    if not observed:
        print("REPRO_REASON=keys are already bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
