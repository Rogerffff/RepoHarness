# probe_extra.py 结果（私有对照；关闭参数校验的低层 client；非法输入只登记差异，不作判分依据）

| 行 | `base` | `gold` | `ctx` | `parity` | `ctx_list` | `rv_dynamotype` | `rv_tagparent` | `rootkey` | `rv_shape_key` |
|---|---|---|---|---|---|---|---|---|---|
| attr_S_dict | SerEx:Start… | AttrErr | SerEx:Start… | SerEx:Start… | SerEx:Start… | SerEx:Start… | SerEx:Start… | AttrErr | AttrErr |
| attrS_S_dict | SerEx:Start… | AttrErr | SerEx:Start… | SerEx:Start… | SerEx:Start… | SerEx:Start… | AttrErr | AttrErr | AttrErr |
| raw_member_named_S_int | AttrErr | AttrErr | AttrErr | AttrErr | AttrErr | AttrErr | AttrErr | AttrErr | AttrErr |
| raw_member_named_N_int | AttrErr | AttrErr | AttrErr | AttrErr | AttrErr | AttrErr | AttrErr | AttrErr | AttrErr |
| raw_member_named_x_int | AttrErr | AttrErr | AttrErr | AttrErr | AttrErr | AttrErr | AttrErr | AttrErr | AttrErr |
| nonkey_S_bool | 存入 | 存入 | 存入 | 存入 | 存入 | SerEx:Start… | 存入 | 存入 | 存入 |
| nonkey_S_list | AttrErr | AttrErr | AttrErr | AttrErr | AttrErr | SerEx:Start… | AttrErr | AttrErr | AttrErr |
| list_N_int | 存入 | 存入 | 存入 | 存入 | SerEx:NUMBER… | SerEx:NUMBER… | 存入 | 存入 | 存入 |
| list_map_member_N_int | 存入 | 存入 | 存入 | 存入 | SerEx:NUMBER… | SerEx:NUMBER… | 存入 | 存入 | 存入 |
| two_tags_N_int | SerEx:NUMBER… | SerEx:NUMBER… | SerEx:NUMBER… | SerEx:NUMBER… | SerEx:NUMBER… | 存入 | SerEx:NUMBER… | SerEx:NUMBER… | SerEx:NUMBER… |

裸值行（raw_member_*）在所有版本上都是 botocore 客户端序列化时抛出的 AttributeError，请求没有到达 moto。
