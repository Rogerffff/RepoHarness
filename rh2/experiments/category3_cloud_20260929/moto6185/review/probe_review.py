"""复核者私有行为探针（moto-6185，不交给求解者）。在原镜像的一次性断网容器里运行。

每行输出一个 JSON：{"row": 名称, "put": "ok" | "SerEx:<文案前 40 字>" | "<Code>" | "EXC:<异常类型>",
                   "stored": 之后能否读到, "equal": 合法行的读回是否与写入相等, "stored_value": 错误行被存入时的值}
- L：题面同款表（HASH index，N），资源层 API、正常 SDK 校验；合法值，put 后 get 比较；
- K：主键名本身为 M 或 S 的表；
- N：关闭 botocore 参数校验的低层 client（与 F2P 同一入口）；前缀 bad_ 的行是真正的类型错误，其余是合法值。
"""
import json
import os
from decimal import Decimal

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ["TEST_SERVER_MODE"] = "false"
import boto3  # noqa: E402
import botocore.client  # noqa: E402
import botocore.session  # noqa: E402
from boto3.dynamodb.types import TypeSerializer  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402
from moto import mock_dynamodb  # noqa: E402

PROV = {"ReadCapacityUnits": 1, "WriteCapacityUnits": 1}


def attempt(fn):
    try:
        fn()
        return "ok"
    except ClientError as e:
        err = e.response["Error"]
        if err["Code"] == "SerializationException":
            return "SerEx:" + err["Message"][:40]
        return err["Code"]
    except Exception as e:  # noqa: BLE001 - moto 内部异常直接穿出 client
        return "EXC:" + type(e).__name__


def emit(**kw):
    print(json.dumps(kw, ensure_ascii=False, default=str, sort_keys=True))


def resource_table(ddb, name, hash_name, hash_type):
    ddb.create_table(TableName=name, KeySchema=[{"AttributeName": hash_name, "KeyType": "HASH"}],
                     AttributeDefinitions=[{"AttributeName": hash_name, "AttributeType": hash_type}],
                     ProvisionedThroughput=PROV)
    return ddb.Table(name)


def resource_roundtrip(row, table, item, key):
    put = attempt(lambda: table.put_item(Item=item))
    got = table.get_item(Key=key).get("Item")
    emit(row=row, put=put, stored=got is not None, equal=(got == item) if got is not None else None)


LEGAL = [
    ("L.ex1_top_S_null", {"S": None}),
    ("L.ex2_nested_S_null", {"A": {"S": None}}),
    ("L.deep2_S", {"A": {"B": {"S": "x"}}}),
    ("L.deep3_S", {"A": {"B": {"C": {"S": None}}}}),
    ("L.deep4_S", {"A": {"B": {"C": {"D": {"S": "x"}}}}}),
    ("L.S_holding_map", {"S": {"x": "y"}}),
    ("L.S_holding_map_with_S", {"S": {"S": "y"}}),
    ("L.nested_S_holding_map", {"A": {"S": {"B": Decimal(1)}}}),
    ("L.S_holding_list", {"S": ["a", Decimal(1)]}),
    ("L.S_holding_bool", {"S": True}),
    ("L.S_holding_set", {"S": {"a", "b"}}),
    ("L.S_first_then_other", {"S": None, "x": Decimal(1)}),
    ("L.map_S_then_sibling", {"A": {"S": None, "T": "x"}}),
    ("L.list_map_S", {"A": [{"S": None}]}),
    ("L.list_in_map_S", {"A": {"B": [{"S": None}]}}),
]

with mock_dynamodb():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    t = resource_table(ddb, "test", "index", "N")
    for i, (row, extra) in enumerate(LEGAL):
        resource_roundtrip(row, t, {"index": i, **extra}, {"index": i})
    # 共用 Table.put_item 的另外两个入口
    item = {"index": 100, "A": {"S": None}}

    def _batch():
        with t.batch_writer() as bw:
            bw.put_item(Item=item)
    put = attempt(_batch)
    got = t.get_item(Key={"index": 100}).get("Item")
    emit(row="L.batch_nested_S", put=put, stored=got is not None, equal=(got == item) if got else None)
    client = boto3.client("dynamodb", region_name="us-east-1")
    ser = TypeSerializer()
    item = {"index": 101, "A": {"S": None}}
    put = attempt(lambda: client.transact_write_items(TransactItems=[
        {"Put": {"TableName": "test", "Item": {k: ser.serialize(v) for k, v in item.items()}}}]))
    got = t.get_item(Key={"index": 101}).get("Item")
    emit(row="L.transact_nested_S", put=put, stored=got is not None, equal=(got == item) if got else None)

    tm = resource_table(ddb, "hashM", "M", "S")
    resource_roundtrip("K.hashM_nested_S", tm, {"M": "id", "A": {"S": None}}, {"M": "id"})
    ts = resource_table(ddb, "hashS", "S", "S")
    resource_roundtrip("K.hashS_nested_S", ts, {"S": "id", "A": {"S": None}}, {"S": "id"})

LOW = [
    # 公开旧断言（F2P 原有部分）
    ("N.bad_pk_S_int", {"pk": {"S": 123}}),
    ("N.bad_pk_S_dict", {"pk": {"S": {"S": "asdf"}}}),
    # gold 缺口 2（v2s 第二项）及同类
    ("N.bad_nonkey_S_dict", {"attr": {"S": {"S": "asdf"}}}),
    ("N.bad_nonkey_S_int", {"attr": {"S": 123}}),
    ("N.bad_nonkey_S_bool", {"attr": {"S": True}}),
    # 公开 P2P test_put_item_wrong_datatype 同形
    ("N.bad_nested_N_int", {"nested": {"M": {"sth": {"N": 5}}}}),
    # v2 第二组两例
    ("N.bad_attrS_contains_N_int", {"S": {"M": {"sth": {"N": 5}}}}),
    ("N.bad_attrS_then_nested_N_int", {"S": {"S": "asdf"}, "nested": {"M": {"sth": {"N": 5}}}}),
    # 同一个嵌套 map 内的顺序（v3 草案新增）及反序
    ("N.bad_mapS_then_N_int", {"nested": {"M": {"S": {"S": "asdf"}, "sth": {"N": 5}}}}),
    ("N.bad_map_N_int_then_S", {"nested": {"M": {"sth": {"N": 5}, "S": {"S": "asdf"}}}}),
    ("N.bad_mapS_then_S_int", {"nested": {"M": {"S": {"NULL": True}, "x": {"S": 5}}}}),
    # 畸形的“裸值”（不是 AttributeValue），ctx／parity 与 base 在此不同
    ("N.bad_raw_S_int", {"S": 5}),
    ("N.bad_raw_N_int", {"N": 5}),
    # list 内的畸形值（base 不校验 list）
    ("N.bad_list_S_dict", {"A": {"L": [{"S": {"S": "x"}}]}}),
    ("N.bad_list_N_int", {"A": {"L": [{"N": 5}]}}),
    # 合法值（与 F2P 同一入口）
    ("N.ok_top_S_str", {"S": {"S": "asdf"}}),
    ("N.ok_S_holding_map", {"S": {"M": {"S": {"S": "asdf"}}}}),
    ("N.ok_deep3", {"A": {"M": {"B": {"M": {"C": {"M": {"S": {"S": "x"}}}}}}}}),
    ("N.ok_list_map_S", {"A": {"L": [{"M": {"S": {"N": "1"}}}]}}),
    ("N.ok_S_before_pk", "S_FIRST"),
]

with mock_dynamodb():
    c = botocore.session.Session().create_client(
        "dynamodb", region_name="us-east-1", config=botocore.client.Config(parameter_validation=False))
    c.create_table(TableName="without_sk", KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
                   AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
                   ProvisionedThroughput=PROV)
    for i, (row, attrs) in enumerate(LOW):
        pk = f"k{i}"
        if attrs == "S_FIRST":
            item = {"S": {"S": "asdf"}, "pk": {"S": pk}}
        elif "pk" in attrs:
            item, pk = attrs, None
        else:
            item = {"pk": {"S": pk}, **attrs}
        put = attempt(lambda: c.put_item(TableName="without_sk", Item=item))
        if pk is None:
            emit(row=row, put=put)
            continue
        try:
            got = c.get_item(TableName="without_sk", Key={"pk": {"S": pk}}).get("Item")
        except Exception as e:  # noqa: BLE001
            got = "get-" + type(e).__name__
        rec = dict(row=row, put=put, stored=got is not None)
        if row.startswith("N.ok_"):
            rec["equal"] = got == item
        elif got is not None:
            rec["stored_value"] = got
        emit(**rec)
