"""P4 public repro: scrapy a95a338e (base 9077d0f9b490). Written from the public prompt only (E06).

Prompt: is_generator_with_return_value(functools.partial(generator_func, arg1=42)) raises
TypeError ("... was expected, got partial"); expected result False. Example used verbatim.
"""
import sys
from functools import partial
import scrapy
from scrapy.utils.misc import is_generator_with_return_value


def generator_func(arg1, arg2):
    yield {}


def main():
    print("SCRAPY_FILE", scrapy.__file__, getattr(scrapy, "__version__", "?"))
    try:
        print("PLAIN_FUNCTION_RESULT", is_generator_with_return_value(generator_func))
    except Exception as e:  # observe only
        print(f"PLAIN_FUNCTION=raised {type(e).__name__}: {e}")
    partial_gen = partial(generator_func, arg1=42)
    try:
        result = is_generator_with_return_value(partial_gen)
    except Exception as e:  # observe only
        print(f"PARTIAL=raised {type(e).__name__}: {e}")
        observed = isinstance(e, TypeError)
        print(f"REPRO_OBSERVED={int(observed)}")
        if not observed:
            print("REPRO_REASON=partial failed, but not with TypeError")
        return 0
    print("PARTIAL=ok", result)
    print("REPRO_OBSERVED=0")
    print("REPRO_REASON=partial accepted without error")
    return 0


if __name__ == "__main__":
    sys.exit(main())
