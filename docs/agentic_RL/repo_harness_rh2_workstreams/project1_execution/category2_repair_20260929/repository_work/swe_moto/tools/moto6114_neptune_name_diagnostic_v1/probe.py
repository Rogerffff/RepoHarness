"""仅两条既有 Neptune name 委托；输出实际行为，不改原奖励。"""
import hashlib
import json
import os
import sys
from pathlib import Path

import moto
import moto.neptune.models
import moto.rds.models


def observe(operation, name):
    backend = moto.rds.models.rds_backends['123456789012']['us-east-1']
    neptune = backend.neptune
    cluster = neptune.create_db_cluster(db_cluster_identifier=name, storage_encrypted='false')
    record = {'operation': operation, 'input': name, 'before_status': cluster.status,
              'present_before': name in neptune.clusters}
    try:
        result = getattr(backend, operation)(name)
        record.update(outcome='returned', returned_identifier=result.db_cluster_identifier,
                      returned_status=result.status, exception_type=None)
    except Exception as error:  # noqa: BLE001 — 诊断须保存实际异常类型，不能预筛模型输出。
        record.update(outcome='exception', exception_type=type(error).__name__,
                      exception_message=str(error))
    record['present_after'] = name in neptune.clusters
    record['stored_status_after'] = neptune.clusters[name].status if record['present_after'] else None
    return record


rds = Path(moto.rds.models.__file__).resolve()
neptune = Path(moto.neptune.models.__file__).resolve()
print(json.dumps({'uid': os.getuid(), 'gid': os.getgid(), 'cwd': os.getcwd(),
    'home': os.environ.get('HOME'), 'python': sys.executable, 'moto_file': moto.__file__,
    'rds_file': str(rds), 'rds_sha256': hashlib.sha256(rds.read_bytes()).hexdigest(),
    'neptune_file': str(neptune), 'neptune_sha256': hashlib.sha256(neptune.read_bytes()).hexdigest(),
    'cases': [observe('start_db_cluster', 'moto6114-neptune-start'),
              observe('delete_db_cluster', 'moto6114-neptune-delete')]}, sort_keys=True))
