| 行 | base | ctx | ctx_list | depth2 | gold | list_as_names | null_only | parity | rootkey | shape | siblings | skip_s_subtree | swallow | top_only |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L.control_lower_s | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok |
| L.control_A | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok |
| L.top_S_null | SerEx | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok |
| L.nested_S_null | SerEx | ok | ok | ok | ok | ok | ok | ok | ok | ok | SerEx | ok | ok | SerEx |
| L.top_S_str | SerEx | ok | ok | ok | ok | ok | SerEx | ok | ok | ok | ok | ok | ok | ok |
| L.nested_S_str | SerEx | ok | ok | ok | ok | ok | SerEx | ok | ok | ok | SerEx | ok | ok | SerEx |
| L.deep_S | SerEx | ok | ok | SerEx | ok | ok | ok | ok | ok | ok | SerEx | ok | ok | SerEx |
| L.deep2_S_str | SerEx | ok | ok | SerEx | ok | ok | SerEx | ok | ok | ok | SerEx | ok | ok | SerEx |
| L.nested_S_sibling | SerEx | ok | ok | ok | ok | ok | SerEx | ok | ok | ok | ok | ok | ok | SerEx |
| L.S_in_S_in_S | SerEx | ok | ok | SerEx | ok | ok | SerEx | ok | ok | ok | SerEx | ok | ok | SerEx |
| L.nested_S_map_value | SerEx | ok | ok | ok | ok | ok | SerEx | ok | ok | ok | SerEx | ok | ok | SerEx |
| L.list_map_S | ok | ok | ok | ok | ok | SerEx | ok | ok | ok | ok | ok | ok | ok | ok |
| L.other_tag_names | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok |
| L.S_first_then_other | SerEx | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok |
| L.batch_nested_S_null | SerEx | ok | ok | ok | ok | ok | ok | ok | ok | ok | SerEx | ok | ok | SerEx |
| L.transact_nested_S_null | TxCancel | ok | ok | ok | ok | ok | ok | ok | ok | ok | TxCancel | ok | ok | TxCancel |
| L.update_set_nested_S_null | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok |
| K.hashM_nested_S_null | SerEx | ok | ok | ok | SerEx | ok | ok | ok | ok | ok | SerEx | ok | ok | SerEx |
| K.hashM_top_S_null | SerEx | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok |
| K.hashM_deep_S_str | SerEx | ok | ok | SerEx | SerEx | ok | SerEx | ok | ok | ok | SerEx | ok | ok | SerEx |
| K.hashM_plain | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok |
| K.rangeM_nested_S_null | SerEx | ok | ok | ok | SerEx | ok | ok | ok | ok | ok | SerEx | ok | ok | SerEx |
| K.hashS_plain | SerEx | ok | ok | ok | ok | ok | SerEx | ok | ok | ok | SerEx | ok | SerEx | ok |
| K.hashS_nested_S_null | SerEx | ok | ok | ok | ok | ok | SerEx | ok | ok | ok | SerEx | ok | SerEx | SerEx |
| K.hashA_nested_S_null | SerEx | ok | ok | ok | ok | ok | ok | ok | ok | ok | SerEx | ok | ok | SerEx |
| N.pk_S_int | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx |
| N.pk_S_dict | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | AttrErr | SerEx | SerEx | SerEx | SerEx |
| N.nonkey_S_dict | SerEx | SerEx | SerEx | SerEx | AttrErr | SerEx | SerEx | SerEx | AttrErr | AttrErr | SerEx | SerEx | AttrErr | SerEx |
| N.nonkey_S_int | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | AttrErr | SerEx |
| N.nested_nonkey_S_dict | SerEx | SerEx | SerEx | SerEx | AttrErr | SerEx | SerEx | SerEx | AttrErr | AttrErr | SerEx | SerEx | AttrErr | SerEx |
| N.nested_nonkey_N_int | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx |
| N.nonkey_N_int | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx |
| N.attrS_S_dict | SerEx | SerEx | SerEx | SerEx | AttrErr | SerEx | SerEx | SerEx | AttrErr | AttrErr | SerEx | AttrErr | AttrErr | SerEx |
| N.attrS_S_int | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | AttrErr | AttrErr | SerEx |
| N.attrS_first_then_N_int | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | ok | SerEx |
| N.lowlevel_top_S_str | SerEx | ok | ok | ok | ok | ok | SerEx | ok | ok | ok | ok | ok | ok | ok |
| N.lowlevel_nested_S_null | SerEx | ok | ok | ok | ok | ok | ok | ok | ok | ok | SerEx | ok | ok | SerEx |
| N.lowlevel_deep_S_str | SerEx | ok | ok | SerEx | ok | ok | SerEx | ok | ok | ok | SerEx | ok | ok | SerEx |
| N.lowlevel_list_map_S | ok | ok | ok | ok | ok | SerEx | ok | ok | ok | ok | ok | ok | ok | ok |
| X.attrS_contains_N_int | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | ok | SerEx | SerEx |
| X.attrS_then_nested_N_int | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | ok | SerEx |
| X.nested_N_int_then_attrS | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx |
| X.nested_attrS_contains_N_int | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | ok | SerEx | SerEx |
| X.attrS_then_nonkey_S_int | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | SerEx | AttrErr | SerEx |
| 私有模拟 orig | 0@L945 | 1 | 1 | 1 | 1 | 1 | 0@L945 | 1 | 1 | 0@L938 | 1 | 1 | 1 | 1 |
| 私有模拟 v2 | 0@L945 | 1 | 1 | 0@L961 | 1 | 0@L961 | 0@L945 | 1 | 1 | 0@L938 | 0@L961 | 0@L971 | 0@L971 | 0@L961 |
| 私有模拟 v2s | 0@L944 | 1 | 1 | 0@L960 | 0@L986 | 0@L960 | 0@L944 | 1 | 0@L993 | 0@L938 | 0@L960 | 0@L970 | 0@L970 | 0@L960 |
| dynamodb 全套 | 434 passed, 2815 warnings in 28.01s | 434 passed, 2815 warnings in 26.78s | 434 passed, 2815 warnings in 28.76s | 434 passed, 2815 warnings in 26.92s | 434 passed, 2815 warnings in 26.38s | 434 passed, 2815 warnings in 29.88s | 434 passed, 2815 warnings in 31.09s | 434 passed, 2815 warnings in 28.82s | 434 passed, 2815 warnings in 26.70s | 1 failed, 433 passed, 2815 warnings in 2 | 434 passed, 2815 warnings in 28.46s | 434 passed, 2815 warnings in 29.81s | 434 passed, 2815 warnings in 29.44s | 434 passed, 2815 warnings in 29.80s |
