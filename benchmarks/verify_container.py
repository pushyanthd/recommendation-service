"""Verify the built CPU image offline, non-root/read-only, without GPU access."""

import argparse
import json
import subprocess
import time
from pathlib import Path

from reco.benchmark import execution_identity
from reco.storage import atomic_json, json_hash, sha256_file


def docker(*arguments):
    return subprocess.run(
        ["docker", *arguments], check=True, capture_output=True, text=True
    ).stdout.strip()


def verify(image, output):
    image_info = json.loads(docker("image", "inspect", image))[0]
    container = docker(
        "run",
        "--detach",
        "--network",
        "none",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=16m",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--health-interval",
        "1s",
        "--health-start-period",
        "0s",
        image,
    )
    try:
        command = """
import hashlib, json, os, pathlib, urllib.request
from reco.data import load_fixture, chronological_split
from reco.ranking import Ranker
import implicit.gpu
url='http://127.0.0.1:8000'
def get(path):
    return json.load(urllib.request.urlopen(url+path, timeout=2))
model=get('/v1/model')
assert model['data_mode']=='fictional_fixture'
assert os.getuid()==10001
request=urllib.request.Request(url+'/v1/recommendations',
    data=b'{"user_id":1,"k":20}', headers={'Content-Type':'application/json'})
result=json.load(urllib.request.urlopen(request,timeout=2))
assert not {1,2,3,4,5} & {row['movie_id'] for row in result['items']}
assert result['model_id']==model['model_id']
dataset=load_fixture()
split=chronological_split(dataset.ratings)
als=Ranker(dataset,split.train,'als_cpu')
assert type(als.als).__module__=='implicit.cpu.als'
assert not implicit.gpu.HAS_CUDA
assert not list(pathlib.Path(implicit.gpu.__file__).parent.glob('_cuda*.so'))
inventory=json.loads(pathlib.Path('/usr/share/reco-runtime/inventory.json').read_text())
for library in inventory['external_libraries']:
    assert hashlib.sha256(pathlib.Path(library['path']).read_bytes()).hexdigest()==library['sha256']
assert not inventory['package_managers_and_shells_included']
for name in ('/bin/sh','/bin/bash','/usr/bin/apt','/usr/bin/dpkg','/usr/bin/perl',
             '/usr/bin/mount','/usr/bin/nsenter','/opt/venv/bin/pip'):
    assert not pathlib.Path(name).exists(), name
assert not {'util-linux','perl-base','libsystemd0','libncursesw6'} & {
    package['name'] for package in inventory['debian_packages']}
print(json.dumps({'model_id':model['model_id'],'data_mode':model['data_mode'],
    'uid':os.getuid(),'cpu_backend':type(als.als).__module__,
    'runtime_identity_sha256':model['runtime_identity_sha256'],
    'source_identity_sha256':model['runtime_source_identity_sha256'],
    'api_peak_process_rss_bytes':model['peak_process_rss_bytes'],
    'runtime_inventory':inventory,
    'ready':get('/readyz')['status']=='ready'}))
"""
        deadline = time.monotonic() + 30
        while True:
            try:
                result = json.loads(docker("exec", container, "python", "-c", command))
                break
            except subprocess.CalledProcessError as exc:
                if time.monotonic() >= deadline:
                    print(exc.stderr)
                    raise
                time.sleep(0.3)
        expected_source = json_hash(execution_identity(Path("uv.lock"))["source_files"])
        assert result["source_identity_sha256"] == expected_source
        info = json.loads(docker("inspect", container))[0]
        while info["State"]["Health"]["Status"] != "healthy":
            if time.monotonic() >= deadline:
                raise RuntimeError("Docker healthcheck failed: " + str(info["State"]["Health"]))
            time.sleep(0.3)
            info = json.loads(docker("inspect", container))[0]
        assert image_info["Config"]["Healthcheck"]["Test"][0] == "CMD"
        assert result["runtime_inventory"]["staging_helper_sha256"] == sha256_file(
            Path("benchmarks/stage_runtime.py")
        )
        assert info["HostConfig"]["ReadonlyRootfs"]
        assert info["HostConfig"]["NetworkMode"] == "none"
        assert not info["HostConfig"].get("DeviceRequests")
        evidence = {
            "schema_version": 1,
            "passed": True,
            "image_id": image_info["Id"],
            "image_user": image_info["Config"]["User"],
            "architecture": image_info["Architecture"],
            "os": image_info["Os"],
            "image_size_bytes": image_info["Size"],
            "dockerfile_sha256": sha256_file(Path("Dockerfile")),
            "source_identity_sha256": json_hash(
                execution_identity(Path("uv.lock"))["source_files"]
            ),
            "read_only": True,
            "healthcheck_passed": True,
            "network": "none",
            "gpu_device_requests": [],
            "checks": result,
        }
        atomic_json(output, evidence)
        print(json.dumps(evidence, indent=2))
    finally:
        docker("rm", "--force", container)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default="cpu-reco:local")
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/container/verification.json")
    )
    args = parser.parse_args()
    verify(args.image, args.output)
