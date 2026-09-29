"""pydantic-8316 私有行为矩阵（在一次性、断网、root 容器内运行，不交给求解者）。
输出一行 JSON（BEHAVIOR_JSON=...）：
  to_snake：各输入的直接输出（题面原例、F2P、17 个旧参数、缩写位置/长度/个数、数字边界、歧义与非 ASCII 输入）；
  to_camel / to_pascal：确认未受影响；
  alias：alias_generator=to_snake 的模型上，生成的 alias、按新 key 与 base 旧 key 填充、populate_by_name、按别名导出、JSON schema 键；
         以及 AliasGenerator(validation_alias=..., serialization_alias=...) 路径；
  note_to_camel：题面附注的 to_camel + populate_by_name 示例。
"""
import json
import re
import warnings

from pydantic import BaseModel, ConfigDict, ValidationError, create_model
from pydantic.alias_generators import to_camel, to_pascal, to_snake

try:
    from pydantic import AliasGenerator
except ImportError:  # pragma: no cover
    AliasGenerator = None

warnings.simplefilter('ignore')


def base_snake(s: str) -> str:
    """base（20c0c6d9）的 to_snake 算法，用来构造“旧 key”。"""
    s = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', s)
    s = re.sub(r'([a-z0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', s)
    return s.lower()


OLD_P2P = [
    'camel_to_snake', 'camelToSnake', 'camel2Snake', '_camelToSnake', 'camelToSnake_', '__camelToSnake__',
    'CamelToSnake', 'Camel2Snake', '_CamelToSnake', 'CamelToSnake_', '__CamelToSnake__',
    'Camel2', 'Camel2_', '_Camel2', 'camel2', 'camel2_', '_camel2',
]
GROUPS = {
    'example': ['HTTPResponse', 'CAMELToSnake'],
    'old_p2p': OLD_P2P,
    'acronym_position': ['HTTPResponseCode', 'getHTTPResponse', 'myHTTPResponse', '_HTTPResponse', '__HTTPResponse__',
                         'HTTPResponse_', 'parseURL', 'innerHTML', 'getHTTPResponseCode'],
    'acronym_length': ['IPAddress', 'IOError', 'userIDToken', 'DBConnection', 'XAxis', 'ATest', 'ABTest'],
    'acronym_count': ['XMLToJSONConverter', 'HTTPResponseXMLParser', 'getIDFromHTTPResponse', 'userIDToJSONString'],
    'digit_boundary': ['A1', 'API2', 'HTTP2', 'snakeV2', 'fieldV2', 'S3Bucket', 'ipV4Address', 'HTTP2Response',
                       'Base64Encoder', 'sha256Hash', 'OAuth2Token', 'EC2Instance', 'version2Name', 'A1B2'],
    'ambiguous_or_other': ['XMLHTTPRequest', 'HTTPS', 'ALLCAPS', 'A', '', 'a', 'already_snake', 'kebab-case',
                           'Mixed_CaseName', 'ÜberHTTPClient', 'getÄnderung'],
}
res = {'to_snake': {g: {s: to_snake(s) for s in xs} for g, xs in GROUPS.items()}}
res['to_snake_base_algo'] = {g: {s: base_snake(s) for s in xs} for g, xs in GROUPS.items()}
res['to_camel'] = {s: to_camel(s) for s in ['http_response_code', 'snake_2_camel', 'snake2camel', '__snake_to_camel__']}
res['to_pascal'] = {s: to_pascal(s) for s in ['http_response_code', 'snake_2_camel', 'snake2camel', '__snake_to_camel__']}


def try_validate(model, data):
    try:
        return {'ok': True, 'dump_by_alias': model.model_validate(data).model_dump(by_alias=True)}
    except ValidationError as e:
        return {'ok': False, 'err': [x['type'] for x in e.errors()]}


alias = {}
for field in ['HTTPResponse', 'myHTTPResponse', 'userIDToken', 'XMLToJSONConverter', 'A1', 'API2', 'fieldV2',
              'S3Bucket', 'ipV4Address', 'Camel2Snake', 'camelToSnake']:
    rec = {}
    M = create_model('M', __config__=ConfigDict(alias_generator=to_snake), **{field: (int, ...)})
    fi = M.model_fields[field]
    rec['alias'] = fi.alias
    rec['validation_alias'] = fi.validation_alias
    rec['serialization_alias'] = fi.serialization_alias
    rec['old_key'] = base_snake(field)
    rec['validate_new_key'] = try_validate(M, {fi.alias: 1})
    rec['validate_old_key'] = try_validate(M, {rec['old_key']: 1})
    rec['validate_field_name_no_populate'] = try_validate(M, {field: 1})
    rec['schema_props'] = sorted(M.model_json_schema(by_alias=True)['properties'])
    P = create_model('P', __config__=ConfigDict(alias_generator=to_snake, populate_by_name=True), **{field: (int, ...)})
    rec['populate_by_name_field'] = try_validate(P, {field: 1})
    if AliasGenerator is not None:
        G = create_model('G', __config__=ConfigDict(alias_generator=AliasGenerator(validation_alias=to_snake,
                                                                                    serialization_alias=to_snake)),
                         **{field: (int, ...)})
        gi = G.model_fields[field]
        rec['aliasgen'] = {'validation_alias': gi.validation_alias, 'serialization_alias': gi.serialization_alias,
                           'validate_new_key': try_validate(G, {gi.validation_alias: 1})['ok'],
                           'validate_old_key': try_validate(G, {rec['old_key']: 1})['ok']}
    alias[field] = rec
res['alias'] = alias


class CamelAliasModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Foo(CamelAliasModel):
    http_response_code: int


res['note_to_camel'] = {
    'alias': Foo.model_fields['http_response_code'].alias,
    'HTTPResponseCode': try_validate(Foo, {'HTTPResponseCode': '200'}),
    'httpResponseCode': try_validate(Foo, {'httpResponseCode': '200'}),
    'http_response_code': try_validate(Foo, {'http_response_code': '200'}),
}
print('BEHAVIOR_JSON=' + json.dumps(res, ensure_ascii=False, sort_keys=True))
