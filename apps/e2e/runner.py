"""双端目标管理：spawn / 就绪等待 / fixture 预置 / teardown。

zimeiti(:8110)：显式环境变量注入 mock LLM（override .env，因 load_dotenv
override=False）；Easel(:7860)：保持其自身配置。
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from mock_llm import MOCK_PORT

APPS = Path(__file__).resolve().parent.parent
API_DIR = APPS / "api"
EASEL_DIR = Path("e:/Projects/Easel")

PORT_Z = 8110
BASE_Z = f"http://127.0.0.1:{PORT_Z}"
BASE_E = "http://127.0.0.1:7860"

FIXTURE_DIRNAME = "e2e-fixture"
FIXTURE_FILE = "note.md"
FIXTURE_BODY = "# E2E 固定装置\n\n这是 browser-e2e 预置的预览内容，断言用它。"


def _wait_ready(base: str, proc: subprocess.Popen, timeout: float = 90,
                errlog: Path | None = None) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            # 单次探测超时必须宽于 Easel /api/status 的最坏耗时：
            # check_gateway() 对已死网关端口吃满 3s + 技能扫描——负载下单请求 3-8s。
            # （曾用 2s：服务活着也永远"未就绪"。）
            urllib.request.urlopen(f"{base}/api/status", timeout=15)
            return
        except Exception:
            if proc.poll() is not None:
                tail = ""
                if errlog is not None and errlog.exists():
                    tail = errlog.read_text(encoding="utf-8", errors="replace")[-300:]
                raise RuntimeError(f"{base} 进程提前退出（code={proc.returncode}）{tail}")
            time.sleep(1)
    proc.kill()
    tail = errlog.read_text(encoding="utf-8", errors="replace")[-300:] if errlog and errlog.exists() else ""
    raise RuntimeError(f"{base} {timeout}s 未就绪 {tail}")


def _write_fixture(root: Path) -> Path:
    d = root / "outputs" / FIXTURE_DIRNAME
    d.mkdir(parents=True, exist_ok=True)
    f = d / FIXTURE_FILE
    f.write_text(FIXTURE_BODY, encoding="utf-8")
    return d


def _rm_fixture(root: Path) -> None:
    import shutil

    shutil.rmtree(root / "outputs" / FIXTURE_DIRNAME, ignore_errors=True)


class Target:
    """一端的一次完整生命周期。"""

    def __init__(self, name: str) -> None:
        self.name = name
        self.base = BASE_Z if name == "zimeiti" else BASE_E
        self.proc: subprocess.Popen | None = None

    def start(self) -> str:
        # 系统瞬时高负载下冷启动可能远超常速（实测 Docker 重启期 >90s）——
        # 120s 窗口 + 失败一次重试（杀净等端口释放再拉起）
        last_err: Exception | None = None
        for _attempt in (1, 2):
            try:
                self._spawn()
                return self.base
            except RuntimeError as e:
                last_err = e
                self.stop()
                time.sleep(5)
        raise last_err from None  # type: ignore[misc]

    def _spawn(self) -> None:
        if self.name == "zimeiti":
            venv_py = API_DIR / ".venv" / "Scripts" / "python.exe"
            if not venv_py.exists():
                venv_py = API_DIR / ".venv" / "bin" / "python"
            env = dict(os.environ)
            # mock LLM 注入：显式环境变量 > .env（load_dotenv override=False）
            env["OPENAI_API_KEY"] = "sk-e2e-mock"
            env["OPENAI_BASE_URL"] = f"http://127.0.0.1:{MOCK_PORT}/v1"
            env["ZIMEITI_MODEL"] = "mock-model"
            env["EASEL_PORT"] = str(PORT_Z)
            err = Path(os.environ.get("TEMP", "/tmp")) / "e2e_zimeiti_stderr.log"
            self.proc = subprocess.Popen(
                [str(venv_py), "-m", "zimeiti_api", "--host", "127.0.0.1", "--port", str(PORT_Z)],
                cwd=API_DIR, env=env, stdout=subprocess.DEVNULL,
                stderr=open(err, "w", encoding="utf-8"),
            )
            _write_fixture(APPS)
        else:
            venv_py = EASEL_DIR / ".venv" / "Scripts" / "python.exe"
            # Windows 控制台 GBK 编不下 Easel 启动横幅的 ✦ ——强制 UTF-8 模式
            env = dict(os.environ, PYTHONUTF8="1")
            err = Path(os.environ.get("TEMP", "/tmp")) / "e2e_easel_stderr.log"
            self.proc = subprocess.Popen(
                [str(venv_py), "web/app.py"],
                cwd=EASEL_DIR, env=env, stdout=subprocess.DEVNULL,
                stderr=open(err, "w", encoding="utf-8"),
            )
            _write_fixture(EASEL_DIR)
        _wait_ready(self.base, self.proc, timeout=120, errlog=err)
        return self.base

    def stop(self) -> None:
        _rm_fixture(APPS)
        _rm_fixture(EASEL_DIR)
        if self.proc is not None:
            # 杀整棵进程树（terminate 只杀直接子进程，孙进程会成孤儿占资源）
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(self.proc.pid)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            try:
                self.proc.wait(timeout=5)
            except Exception:
                pass
            self.proc = None

    def port_busy(self) -> bool:
        return _port_open(self.base)


def _port_open(base: str) -> bool:
    try:
        urllib.request.urlopen(f"{base}/api/status", timeout=1)
        return True
    except Exception:
        return False


def python_exec() -> str:
    return sys.executable
