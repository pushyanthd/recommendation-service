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
        image,
    )
    try:
        command = """
import json, os, urllib.request
from reco.data import load_fixture, chronological_split
from reco.ranking import Ranker
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
print(json.dumps({'model_id':model['model_id'],'data_mode':model['data_mode'],
    'uid':os.getuid(),'cpu_backend':type(als.als).__module__,
    'runtime_identity_sha256':model['runtime_identity_sha256'],
    'source_identity_sha256':model['runtime_source_identity_sha256'],
    'api_peak_process_rss_bytes':model['peak_process_rss_bytes'],
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
