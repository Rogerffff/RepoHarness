# 原镜像与安装复用依据（材料阶段）

建议只恢复本题原不可变镜像。不是相邻Moto题的install_wave1/E10候选，也不需要增加安装配方注册。

- OCI：xingyaoww/sweb.eval.x86_64.getmoto_s_moto-5406@sha256:727caa5dba157d41b1e839a5044106f0ad7ea1fe824c9a5f562e2f74113339d6。
- 历史实测config ID：sha256:808c60d962cb94330e499404720a0813fa400a2e86464aabdb47fcaa05aad5f6。旧original_image.json与actor image事实可追溯，但新机必须实际restore/inspect；不可代填本次image_id_actual。
- base：87683a786f0d3a0280c92ea01fecce8a3dd4b0fd，tree895c012fc15bb2256dcc71e570bcdc9796acb153。公开base导出逐blob/mode/path核过，唯一未materialize gitlink为Terraform provider，不在本片节点依赖。
- vendor：swegym_constants_242429c1 / getmoto/moto / 4.0，source要求python_version=3.12；冻结RH2真实derive_install_cmd返回精确 `make init`，无eval_commands。
- 原make init执行python setup.py develop、pip install -r requirements-dev.txt；后者含-e .[all,server]和requirements-tests（pytest/sure等）。CPU29三方实际安装日志均make init成功、候选源码开发安装完成、无failed_commands/skip，原import为/testbed/moto。不是静态recipe说明代替真实安装。

历史CC公开actor观察Python3.12.4、boto3/botocore1.35.9、pytest8.3.2；旧公开East1节点实际执行base/gold通过，constant_east2因ARN断言失败。该节点同原27项共享moto/mock_dynamodb、SDK、sure、pytest和同目录conftest，没有独有额外安装依赖。tests包helpers只注册sure辅助断言，非fixture；table fixture非autouse并未被节点请求。

| 固定材料 | 原始SHA256 |
| --- | --- |
| 新选择的原公开test_dynamodb_create_table.py | a0543ad19335b4d87b717263e797055ab9876481d469808554be9ec1d6ca6292 |
| 原正式test_dynamodb_table_without_range_key.py | b2e2e5f7bbc1c25a401771e37470d93b5c27bb15398b7e0764043c0f5ce00cf9 |
| 原tests/test_dynamodb/conftest.py | 8cfb47240cdf8f63d5dada316b5921ff610b4947fba5aefa0382952ab006cfcd |
| 原test.patch，提案effective相同 | 8ebca50a732adf095b78e805dabf13bb64efd7037639c3280b08425705c4db8f |
| base moto/dynamodb/models/__init__.py | 87a558769bc0786464aeaca26fc29217c718971f447d6ddfc4ced9a3977d4f23 |
| gold应用后源码 | 2fd7febd19be90e561f79b324508cc934b05922fc32c8daab7f5097d25234b5c |
| constant_east2应用后源码 | 4bd4d6450546ba4a497c938023bea94b7bd81c774e089c0a0db690c461c66253 |

上述源码SHA也由本轮隔离static apply实际复算；没导入/运行Moto。material manifest列原文件/安装文件和原CPU27项完整logs/ledger/artifacts。冻结parser重放验证81个原参考状态，以及三份独立公开East1原日志状态，历史原正式reward为0/1/1，预期新28节点为0/1/0尚待实跑。

资源沿历史2CPU/4GiB/PID512/shm64MiB、setup/reset900、apply120/test1800/whole1800/cleanup120提案；root最后CPU计划定额，不能因历史约293/278/280秒setup而声称旧300预算已验收。原ledger资源facts=null，约15秒资源样本不是全生命周期证明。新命令添加1个已在该镜像执行过的节点，仍须新机安装/源码/实际collection/footer/两层清理原件核对；如失败保留事实后另诊断，不先扩大配方或预算。

本片环境材料仅说明供应与历史适用性，不构成新CPU验收、训练资格或对所有DynamoDB/其它Moto题的通用认证。
