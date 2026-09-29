#!/usr/bin/env python3
"""MONAI-1121 诊断：在 fresh 容器测试前预置已校验的 ResNet 权重，评分逻辑沿原 runner。"""
import argparse
import hashlib
from pathlib import Path
import shlex
import sys
import swegym_probe as probe


def main():
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--resnet-file',required=True)
    args,rest=parser.parse_known_args()
    asset=Path(args.resnet_file)
    digest=hashlib.sha256(asset.read_bytes()).hexdigest()
    expected='0676ba61b6795bbe1773cffd859882e5e297624d384b6993f7c9e683e722fb8a'
    if digest != expected:
        raise ValueError('预置文件与已保存的 ResNet 资产摘要不一致')
    details={'url':'https://download.pytorch.org/models/resnet50-0676ba61.pth','sha256':digest,'bytes':asset.stat().st_size,'container_path':'/root/.cache/torch/hub/checkpoints/resnet50-0676ba61.pth','purpose':'实验性预置测试依赖；未改变参考测试或评分定义'}
    original_start=probe.Container.start
    original_job=probe.run_job

    def start(container):
        original_start(container)
        folder='/root/.cache/torch/hub/checkpoints'
        result=container.exec('mkdir -p '+shlex.quote(folder),timeout=30)
        if result.returncode:
            raise RuntimeError('无法建立测试资产缓存目录')
        result=probe.sh(['docker','cp',str(asset),container.name+':'+details['container_path']],timeout=120)
        if result.returncode:
            raise RuntimeError('预置测试资产失败：'+result.stderr.decode(errors='replace')[-300:])
        verified=container.exec('sha256sum '+shlex.quote(details['container_path']),timeout=30)
        if verified.returncode or verified.stdout.decode().split()[0] != digest:
            raise RuntimeError('容器内测试资产校验失败')

    def job(*args,**kwargs):
        rec=original_job(*args,**kwargs)
        rec['test_asset_preload']=details
        return rec

    probe.Container.start=start
    probe.run_job=job
    sys.argv=[sys.argv[0],*rest]
    return probe.main()

if __name__=='__main__':
    sys.exit(main())
