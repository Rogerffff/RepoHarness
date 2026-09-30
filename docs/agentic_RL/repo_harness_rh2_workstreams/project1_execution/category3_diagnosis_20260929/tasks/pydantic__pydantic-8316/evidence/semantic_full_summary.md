| 变体 | 相关公开测试 | 私有模拟 原测试 | v1 | v2 | v1/v2 首条失败断言 |
| --- | --- | --- | --- | --- | --- |
| acr3 | 274 passed、17 skipped | 1（F2P 1/1，P2P 143/143） | 0（F2P 0/1，P2P 143/143） | 0（F2P 0/1，P2P 143/143） | E   AssertionError: assert 'user_idtoken' == 'user_id_token' |
| acr_max4 | 274 passed、17 skipped | 0（F2P 0/1，P2P 143/143） | 0（F2P 0/1，P2P 143/143） | 0（F2P 0/1，P2P 143/143） | E   AssertionError: assert 'camelto_snake' == 'camel_to_snake' |
| acr_max5 | 274 passed、17 skipped | 1（F2P 1/1，P2P 143/143） | 1（F2P 1/1，P2P 143/143） | 1（F2P 1/1，P2P 143/143） |  |
| base | 274 passed、17 skipped | 0（F2P 0/1，P2P 143/143） | 0（F2P 0/1，P2P 143/143） | 0（F2P 0/1，P2P 143/143） | E   AssertionError: assert 'camelto_snake' == 'camel_to_snake' |
| first_only | 274 passed、17 skipped | 1（F2P 1/1，P2P 143/143） | 0（F2P 0/1，P2P 143/143） | 0（F2P 0/1，P2P 143/143） | E   AssertionError: assert 'xml_to_jsonconverter' == 'xml_to_json_converter' |
| gold | 274 passed、17 skipped | 1（F2P 1/1，P2P 143/143） | 1（F2P 1/1，P2P 143/143） | 1（F2P 1/1，P2P 143/143） |  |
| keep_digit | 274 passed、17 skipped | 1（F2P 1/1，P2P 143/143） | 1（F2P 1/1，P2P 143/143） | 1（F2P 1/1，P2P 143/143） |  |
| lead_only | 274 passed、17 skipped | 1（F2P 1/1，P2P 143/143） | 0（F2P 0/1，P2P 143/143） | 0（F2P 0/1，P2P 143/143） | E   AssertionError: assert 'get_httpresponse_code' == 'get_http_response_code' |
| literal | 274 passed、17 skipped | 0（F2P 0/1，P2P 143/143） | 0（F2P 0/1，P2P 143/143） | 0（F2P 0/1，P2P 143/143） | E   AssertionError: assert 'camelto_snake' == 'camel_to_snake' |
| lookaround | 274 passed、17 skipped | 1（F2P 1/1，P2P 143/143） | 1（F2P 1/1，P2P 143/143） | 1（F2P 1/1，P2P 143/143） |  |
| lower_or_start | 274 passed、17 skipped | 1（F2P 1/1，P2P 143/143） | 0（F2P 0/1，P2P 143/143） | 0（F2P 0/1，P2P 143/143） | E   AssertionError: assert 'xml_to_jsonconverter' == 'xml_to_json_converter' |
| lower_or_start_la | 274 passed、17 skipped | 1（F2P 1/1，P2P 143/143） | 1（F2P 1/1，P2P 143/143） | 0（F2P 0/1，P2P 143/143） | E   AssertionError: assert '__httpresponse__' == '__http_response__' |
| no_digit_split | 8 failed、266 passed、17 skipped | 0（F2P 1/1，P2P 135/143） | 0（F2P 1/1，P2P 135/143） | 0（F2P 0/1，P2P 135/143） | E   AssertionError: assert 'camel2_snake' == 'camel_2_snake' |
| no_digit_upper | 2 failed、272 passed、17 skipped | 0（F2P 1/1，P2P 141/143） | 0（F2P 1/1，P2P 141/143） | 0（F2P 0/1，P2P 141/143） | E   AssertionError: assert 'camel_2snake' == 'camel_2_snake' |
| no_lower_upper | 274 passed、17 skipped | 1（F2P 1/1，P2P 143/143） | 0（F2P 0/1，P2P 143/143） | 0（F2P 0/1，P2P 143/143） | E   AssertionError: assert 'gethttp_response_code' == 'get_http_response_code' |
| no_trailing_upper | 274 passed、17 skipped | 1（F2P 1/1，P2P 143/143） | 1（F2P 1/1，P2P 143/143） | 0（F2P 0/1，P2P 143/143） | E   AssertionError: assert 'parseurl' == 'parse_url' |
| normalize | 274 passed、17 skipped | 1（F2P 1/1，P2P 143/143） | 1（F2P 1/1，P2P 143/143） | 1（F2P 1/1，P2P 143/143） |  |
| only_if_no_us | 274 passed、17 skipped | 0（F2P 0/1，P2P 143/143） | 0（F2P 0/1，P2P 143/143） | 0（F2P 0/1，P2P 143/143） | E   AssertionError: assert 'camelto_snake' == 'camel_to_snake' |
| scan | 274 passed、17 skipped | 1（F2P 1/1，P2P 143/143） | 1（F2P 1/1，P2P 143/143） | 1（F2P 1/1，P2P 143/143） |  |
| skip_if_digit | 274 passed、17 skipped | 1（F2P 1/1，P2P 143/143） | 1（F2P 1/1，P2P 143/143） | 0（F2P 0/1，P2P 143/143） | E   AssertionError: assert 'base_64_urlencode' == 'base_64_url_encode' |
| skip_if_underscore | 274 passed、17 skipped | 1（F2P 1/1，P2P 143/143） | 1（F2P 1/1，P2P 143/143） | 0（F2P 0/1，P2P 143/143） | E   AssertionError: assert '__httpresponse__' == '__http_response__' |
| upstream_main | 274 passed、17 skipped | 1（F2P 1/1，P2P 143/143） | 1（F2P 1/1，P2P 143/143） | 1（F2P 1/1，P2P 143/143） |  |
