#!/bin/bash
echo '=== public_http_parser_tests'
( cd /testbed && if PYTHONDONTWRITEBYTECODE=1 python -c "import aiohttp._http_parser" 2>/dev/null; then echo 'C parser importable: py-parser and c-parser params both run'; else echo 'C parser not importable: exporting AIOHTTP_NO_EXTENSIONS=1 so the three C-only tests are skipped'; export AIOHTTP_NO_EXTENSIONS=1; fi; PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider -o addopts="" -m "not dev_mode" -q -rfEs tests/test_http_parser.py ) 2>&1 | tail -25
echo "RC_public_http_parser_tests=${PIPESTATUS[0]}"
echo '=== public_related_tests'
( cd /testbed && PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider -o addopts="" -m "not dev_mode" -q -rfE tests/test_http_exceptions.py tests/test_multipart.py tests/test_client_proto.py ) 2>&1 | tail -25
echo "RC_public_related_tests=${PIPESTATUS[0]}"
