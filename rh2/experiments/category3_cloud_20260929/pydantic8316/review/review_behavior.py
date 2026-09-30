"""复核者的私有行为探针（断网一次性 root 容器内运行，不交给求解者）。输出一行 REVIEW_BEHAVIOR_JSON=...：
  to_snake：v2 与复核草案 v3 的断言输入、各类阈值／位置／编码输入、数字边界与歧义输入；
  alias：alias_generator=to_snake 的模型上字段 alias 与按 base 旧 key 验证的结果（核对作者“alias 的实际影响”）；
  lossless：去掉下划线并小写后是否与输入一致（候选有没有丢字符或改字符）。
"""
import json
import re
import warnings

from pydantic import ValidationError, create_model, ConfigDict
from pydantic.alias_generators import to_snake

warnings.simplefilter('ignore')

INPUTS = [
    # 题面原例、原 F2P、v2 的 7 条
    'HTTPResponse', 'CAMELToSnake', 'getHTTPResponseCode', 'userIDToken', 'XMLToJSONConverter', '__HTTPResponse__',
    'base64URLEncode', 'parseURL',
    # 复核草案 v3 追加的 4 条
    'loadCONFIGURATIONFile', 'convertXMLToJSONViaHTTPRequest', 'get_HTTPResponse', 'ÜberHTTPClient',
    # 阈值：长度、个数、位置、串长
    'NASDAQTicker', 'CONFIGURATIONError', 'getWYSIWYGEditor', 'parseXMLToJSONToCSVToYAMLFile', 'aVeryLongPrefixBeforeTheHTTPResponse',
    # 与下划线／数字相邻
    '_HTTPResponse', 'HTTPResponse_', 'my_XMLParser', 'Camel2HTTPResponse', 'sha256HMACKey', 'HTTPResponse2',
    # 非 ASCII
    'naïveHTTPResponse', 'getÄnderung', 'ÜBERSize', 'parseÜBERDoc',
    # 未规定：大写字母→数字、单字母、相连缩写、复数缩写、kebab
    'A1', 'snakeV2', 'S3Bucket', 'HTTP2Response', 'getAValue', 'XAxis', 'OAuth2Token', 'XMLHTTPRequest', 'getURLs', 'kebab-case',
]


def try_validate(model, data):
    try:
        return {'ok': True, 'dump_by_alias': model.model_validate(data).model_dump(by_alias=True)}
    except ValidationError as e:
        return {'ok': False, 'err': [x['type'] for x in e.errors()]}


def base_snake(s):
    s = re.sub(r'([a-zA-Z])([0-9])', lambda m: f'{m.group(1)}_{m.group(2)}', s)
    s = re.sub(r'([a-z0-9])([A-Z])', lambda m: f'{m.group(1)}_{m.group(2)}', s)
    return s.lower()


res = {'to_snake': {}, 'lossless': {}}
for s in INPUTS:
    try:
        out = to_snake(s)
    except Exception as e:  # noqa: BLE001
        out = f'<{type(e).__name__}: {e}>'
    res['to_snake'][s] = out
    res['lossless'][s] = isinstance(out, str) and out.replace('_', '') == s.replace('_', '').lower()

alias = {}
for field in ['HTTPResponse', 'userIDToken', 'fieldV2', 'S3Bucket', 'loadCONFIGURATIONFile', 'my_XMLParser', 'ÜberHTTPClient']:
    M = create_model('M', __config__=ConfigDict(alias_generator=to_snake), **{field: (int, ...)})
    fi = M.model_fields[field]
    alias[field] = {
        'alias': fi.alias,
        'old_key': base_snake(field),
        'validate_new_key': try_validate(M, {fi.alias: 1})['ok'],
        'validate_old_key': try_validate(M, {base_snake(field): 1})['ok'],
        'schema_props': sorted(M.model_json_schema(by_alias=True)['properties']),
    }
res['alias'] = alias
print('REVIEW_BEHAVIOR_JSON=' + json.dumps(res, ensure_ascii=False, sort_keys=True))
