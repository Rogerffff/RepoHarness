"""P4 public repro: scrapy cfed9b66 (base 54216d7afe9d, Scrapy 1.1.0dev1 on Python 3.9).

Written from the public prompt only (E06). Prompt: passing a Python object instead of an
import path in middleware settings fails with AttributeError ("... has no attribute 'rindex'").
Inference: the prompt calls the abstract MiddlewareManager with a plain dict; that call is
recorded as-is, then the equivalent concrete paths are tried: load_object(<class / instance>)
and DownloaderMiddlewareManager.from_settings with the class as a DOWNLOADER_MIDDLEWARES key.
"""
import sys
import scrapy
from scrapy.middleware import MiddlewareManager
from scrapy.settings import Settings
from scrapy.utils.misc import load_object


class CustomMiddleware:
    pass


def attempt(label, fn):
    try:
        print(f"{label}=ok {fn()!r}")
        return ""
    except Exception as e:  # observe only
        print(f"{label}=raised {type(e).__name__}: {e}")
        return f"{type(e).__name__}: {e}"


def main():
    print("SCRAPY_FILE", scrapy.__file__, getattr(scrapy, "__version__", "?"))
    from scrapy.core.downloader.middleware import DownloaderMiddlewareManager
    s = Settings({"DOWNLOADER_MIDDLEWARES_BASE": {}, "DOWNLOADER_MIDDLEWARES": {CustomMiddleware: 100}})
    msgs = [
        attempt("LITERAL_PROMPT_EXAMPLE",
                lambda: MiddlewareManager.from_settings({"MIDDLEWARES": {"custom": CustomMiddleware()}})),
        attempt("LOAD_OBJECT_CLASS", lambda: load_object(CustomMiddleware)),
        attempt("LOAD_OBJECT_INSTANCE", lambda: load_object(CustomMiddleware())),
        attempt("DOWNLOADER_MW_CLASS_KEY", lambda: DownloaderMiddlewareManager.from_settings(s).middlewares),
    ]
    observed = any(m.startswith("AttributeError") and ("rindex" in m or "startswith" in m) for m in msgs)
    print(f"REPRO_OBSERVED={int(observed)}")
    if not observed:
        print("REPRO_REASON=no call treated the object as a string import path")
    return 0


if __name__ == "__main__":
    sys.exit(main())
