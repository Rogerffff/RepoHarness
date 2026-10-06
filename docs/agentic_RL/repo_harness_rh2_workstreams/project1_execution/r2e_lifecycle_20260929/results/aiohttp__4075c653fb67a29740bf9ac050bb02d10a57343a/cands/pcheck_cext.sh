#!/bin/bash
cd /testbed && ls -la vendor/llhttp 2>&1 | head -8; ls aiohttp/*.so aiohttp/_http_parser* 2>&1 | head; which gcc cc 2>&1; python -c "import aiohttp.http_parser as h; print(\"C parser:\", getattr(h, \"HttpRequestParserC\", None))" 2>&1
echo RH2_CMD_RC=$?
