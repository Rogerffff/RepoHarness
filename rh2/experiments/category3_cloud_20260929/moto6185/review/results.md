| 版本 | 候选 sha256 | orig | v2 | v2s | v3 | P2P（四版） |
|---|---|---|---|---|---|---|
| `base` | — | 0@945 | 0@945 | 0@944 | 0@944 | 34/34 |
| `gold` | 868fd2d1 | **1** | **1** | 0@986 | 0@994 | 34/34 |
| `ctx` | 139572e8 | **1** | **1** | **1** | **1** | 34/34 |
| `parity` | d7ca0fd9 | **1** | **1** | **1** | **1** | 34/34 |
| `ctx_list` | 9169306d | **1** | **1** | **1** | **1** | 34/34 |
| `rv_dynamotype` | 2d73d9d7 | **1** | **1** | **1** | **1** | 34/34 |
| `top_only` | 1d82e10d | **1** | 0@961 | 0@960 | 0@967 | 34/34 |
| `siblings` | c39acf3b | **1** | 0@961 | 0@960 | 0@967 | 34/34 |
| `depth2` | 2bdf47a6 | **1** | 0@961 | 0@960 | 0@967 | 34/34 |
| `list_as_names` | f4a791b5 | **1** | 0@961 | 0@960 | 0@967 | 34/34 |
| `null_only` | 23b58b21 | 0@945 | 0@945 | 0@944 | 0@944 | 34/34 |
| `shape` | 36f1b5d7 | 0@938 | 0@938 | 0@938 | 0@938 | 34/34 |
| `rootkey` | 0232a04f | **1** | **1** | 0@993 | 0@1006 | 34/34 |
| `swallow` | 35a765d8 | **1** | 0@971 | 0@970 | 0@978 | 34/34 |
| `skip_s_subtree` | c273d7e3 | **1** | 0@971 | 0@970 | 0@978 | 34/34 |
| `rv_swallow_attr` | 9d37f01b | **1** | **1** | 0@993 | 0@978 | 34/34 |
| `rv_depth4` | ae21146f | **1** | **1** | **1** | 0@967 | 34/34 |
| `rv_scalar_s` | e068f41a | **1** | **1** | 0@986 | 0@967 | 34/34 |
| `rv_tagparent` | 9d4c841f | **1** | **1** | **1** | 0@1006 | 34/34 |
| `rv_shape_key` | d0c12753 | **1** | **1** | 0@993 | 0@1006 | 34/34 |
| `rv_top_or_null` | 5d441c3e | **1** | 0@961 | 0@960 | 0@967 | 34/34 |
| `rv_break_after_s` | 48702342 | **1** | 0@971 | 0@970 | 0@978 | 34/34 |

| 版本 | 例2 嵌套 | 三层 map | S 的值是 map | list 内 map | 主键名 M＋嵌套 S | 主键名 S＋嵌套 S | batch | transact | 非主键 S→dict | S 在前＋嵌套 N 整数 | 同一 map 内 S 在前＋N 整数 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `base` | SerEx | SerEx | SerEx | ok | SerEx | SerEx | SerEx | TxCancel | SerEx | SerEx | SerEx |
| `gold` | ok | ok | ok | ok | SerEx | ok | ok | ok | AttrErr | SerEx | SerEx |
| `ctx` | ok | ok | ok | ok | ok | ok | ok | ok | SerEx | SerEx | SerEx |
| `parity` | ok | ok | ok | ok | ok | ok | ok | ok | SerEx | SerEx | SerEx |
| `ctx_list` | ok | ok | ok | ok | ok | ok | ok | ok | SerEx | SerEx | SerEx |
| `rv_dynamotype` | ok | ok | ok | ok | ok | ok | ok | ok | SerEx | SerEx | SerEx |
| `top_only` | SerEx | SerEx | ok | ok | SerEx | SerEx | SerEx | TxCancel | SerEx | SerEx | SerEx |
| `siblings` | SerEx | SerEx | ok | ok | SerEx | SerEx | SerEx | TxCancel | SerEx | SerEx | SerEx |
| `depth2` | ok | SerEx | ok | ok | ok | ok | ok | ok | SerEx | SerEx | SerEx |
| `list_as_names` | ok | ok | ok | SerEx | ok | ok | ok | ok | SerEx | SerEx | SerEx |
| `null_only` | ok | ok | SerEx | ok | ok | SerEx | ok | ok | SerEx | SerEx | SerEx |
| `shape` | ok | ok | ok | ok | ok | ok | ok | ok | AttrErr | SerEx | SerEx |
| `rootkey` | ok | ok | ok | ok | ok | ok | ok | ok | AttrErr | SerEx | SerEx |
| `swallow` | ok | ok | ok | ok | ok | SerEx | ok | ok | AttrErr | **存入** | **存入** |
| `skip_s_subtree` | ok | ok | ok | ok | ok | ok | ok | ok | SerEx | SerEx | SerEx |
| `rv_swallow_attr` | ok | ok | ok | ok | ok | SerEx | ok | ok | AttrErr | SerEx | **存入** |
| `rv_depth4` | ok | SerEx | ok | ok | ok | ok | ok | ok | SerEx | SerEx | SerEx |
| `rv_scalar_s` | ok | ok | SerEx | ok | SerEx | ok | ok | ok | AttrErr | SerEx | SerEx |
| `rv_tagparent` | ok | ok | ok | ok | ok | ok | ok | ok | SerEx | SerEx | SerEx |
| `rv_shape_key` | ok | ok | ok | ok | ok | ok | ok | ok | AttrErr | SerEx | SerEx |
| `rv_top_or_null` | ok | ok | ok | ok | ok | ok | ok | ok | SerEx | SerEx | SerEx |
| `rv_break_after_s` | ok | ok | ok | ok | ok | ok | ok | ok | SerEx | **存入** | **存入** |

tests/test_dynamodb 全套：`gold` 434 passed, 2815 warnings in 29.08s；`ctx` 434 passed, 2815 warnings in 28.98s；`parity` 434 passed, 2815 warnings in 28.62s；`ctx_list` 434 passed, 2815 warnings in 28.15s；`rv_dynamotype` 434 passed, 2815 warnings in 29.19s

测试补丁 sha256：orig `506b3670e0f8`，v2 `7bbae2873ebc`，v2s `4122cced6ef0`，v3 `fc65a52722f4`；gold `868fd2d166dd`；解析命令 `pytest -n0 -rA`，P2P 34 项
