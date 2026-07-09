from __future__ import annotations

import subprocess


def terminate_child_process(
    child: subprocess.Popen,
    *,
    graceful_timeout_seconds: float,
    kill_timeout_seconds: float = 2,
) -> None:
    child.terminate()
    try:
        child.wait(timeout=graceful_timeout_seconds)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=kill_timeout_seconds)
