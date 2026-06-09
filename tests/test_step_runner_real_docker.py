"""L11:对真实 docker 守护进程跑容器,验证 mock 单测覆盖不到的执行器机制——
work_dir bind-mount 到 /job、env 注入(PYTHONPATH/STEP_EXEC_ID)、离线池 network=none、
退出码捕获。无 docker.sock 或本地无 python:3.11-slim 镜像时跳过(不联网拉取),
故标准容器内单测套件会跳过,有 docker 的环境才真跑。"""

from __future__ import annotations

import os

import pytest

_SOCK = "/var/run/docker.sock"


def _docker_or_skip():
    if not os.path.exists(_SOCK):
        pytest.skip("无 /var/run/docker.sock")
    try:
        import docker
    except ImportError:
        pytest.skip("无 docker SDK")
    try:
        client = docker.from_env()
        client.ping()
    except Exception:
        pytest.skip("docker 守护进程不可达")
    try:
        client.images.get("python:3.11-slim")  # 不联网拉取,本地无则跳过
    except Exception:
        pytest.skip("本地无 python:3.11-slim 镜像")
    return client


class TestRealDockerMechanics:
    def test_bind_mount_env_and_network_none(self, tmp_path):
        client = _docker_or_skip()
        # 模拟执行器:把 work_dir 以宿主路径 bind 到 /job,注入 env,断网,跑一段真命令。
        # 用容器把 STEP_EXEC_ID 写进 /job,再从宿主读回,验证 bind-mount 双向可见。
        (tmp_path / "in.txt").write_text("hi", encoding="utf-8")
        script = (
            "import os;"
            "open('/job/out.txt','w').write("
            "os.environ.get('STEP_EXEC_ID','')+':'+os.environ.get('PYTHONPATH','')"
            "+':'+open('/job/in.txt').read())"
        )
        container = client.containers.run(
            "python:3.11-slim",
            command=["python3", "-c", script],
            volumes={str(tmp_path): {"bind": "/job", "mode": "rw"}},
            working_dir="/job",
            environment={"STEP_EXEC_ID": "exec-real-1", "PYTHONPATH": "/app"},
            network_mode="none",  # 离线计算池断网
            detach=True,
        )
        try:
            result = container.wait(timeout=60)
            assert result["StatusCode"] == 0, container.logs().decode()
        finally:
            container.remove(force=True)

        out = (tmp_path / "out.txt").read_text(encoding="utf-8")
        assert out == "exec-real-1:/app:hi"  # env 注入 + bind-mount 双向均生效
