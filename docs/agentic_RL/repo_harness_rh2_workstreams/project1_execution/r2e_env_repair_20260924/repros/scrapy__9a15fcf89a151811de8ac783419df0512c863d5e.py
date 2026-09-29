"""P4 public repro: scrapy 9a15fcf8 (base 3fc4e0b319fc, Scrapy 1.1.0dev1 on Python 3.9).

Written from the public prompt only (E06). Prompt: responsetypes.from_content_type(
'application/x-json; encoding=UTF8;charset=UTF-8') returns Response, not TextResponse.
Inference: the prompt passes a str; bytes is tried too (header values are bytes on py3).
"""
import sys
import scrapy
from scrapy.http import TextResponse
from scrapy.responsetypes import responsetypes

CT = "application/x-json; encoding=UTF8;charset=UTF-8"


def main():
    print("SCRAPY_FILE", scrapy.__file__, getattr(scrapy, "__version__", "?"))
    got = {}
    for label, arg in (("STR", CT), ("BYTES", CT.encode())):
        try:
            got[label] = cls = responsetypes.from_content_type(arg)
            print(f"FROM_CONTENT_TYPE_{label}={cls.__module__}.{cls.__name__}")
        except Exception as e:  # observe only
            print(f"FROM_CONTENT_TYPE_{label}=raised {type(e).__name__}: {e}")
    observed = any(not issubclass(c, TextResponse) for c in got.values())
    print(f"REPRO_OBSERVED={int(observed)}")
    if not observed:
        print("REPRO_REASON=no call returned a non-TextResponse class")
    return 0


if __name__ == "__main__":
    sys.exit(main())
