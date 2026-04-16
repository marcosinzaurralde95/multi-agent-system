"""
MAMS - Matrix Agentic Money System
Startup and health commands
"""

import argparse
import subprocess
import sys
import threading
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def _print_header(title: str):
    print("=" * 60)
    print(title)
    print("=" * 60)


def ensure_config_exists() -> None:
    config_path = Path("config.yaml")
    if not config_path.exists():
        raise FileNotFoundError("config.yaml not found in project root.")


def run_worker(mode: str = "autonomous") -> None:
    from config import validate_runtime
    from main import SystemOrchestrator

    ensure_config_exists()
    validate_runtime(require_openrouter=True)

    _print_header("MAMS Worker")
    print(f"Mode: {mode}")
    orchestrator = SystemOrchestrator()
    orchestrator.initialize()
    orchestrator.start()


def run_dashboard(port: int = 8050):
    from dashboard import run_dashboard as run_dashboard_server

    ensure_config_exists()
    _print_header("MAMS Dashboard")
    print(f"Port: {port}")
    run_dashboard_server(debug=False, port=port)


def run_system(mode: str = "autonomous", port: int = 8050):
    _print_header("MAMS Full Run (dev)")
    dashboard_thread = threading.Thread(target=run_dashboard, kwargs={"port": port}, daemon=True)
    dashboard_thread.start()
    print(f"Dashboard available at http://localhost:{port}")
    run_worker(mode=mode)


def run_agent(agent_id: str):
    from agents import (
        AnalystAgent,
        ComplianceAgent,
        CreatorAgent,
        FinanceAgent,
        MarketerAgent,
        QualityAgent,
        ResearcherAgent,
        SalesAgent,
    )

    mapping = {
        "researcher": ResearcherAgent,
        "creator": CreatorAgent,
        "marketer": MarketerAgent,
        "sales": SalesAgent,
        "analyst": AnalystAgent,
        "quality": QualityAgent,
        "compliance": ComplianceAgent,
        "finance": FinanceAgent,
    }
    agent_class = mapping.get(agent_id)
    if not agent_class:
        raise ValueError(f"Unknown agent: {agent_id}")

    agent = agent_class()
    agent.start()
    print(f"Agent started: {agent_id}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()


def run_healthcheck(strict: bool = False) -> int:
    from config import ConfigValidationError, get_config, validate_runtime
    from memory import get_memory
    from message_bus import get_message_bus

    _print_header("MAMS Healthcheck")
    status = 0

    try:
        cfg = get_config()
        print(f"Config: OK ({cfg.system.name} {cfg.system.version})")
    except Exception as exc:
        print(f"Config: FAIL ({exc})")
        return 1

    try:
        validate_runtime(require_openrouter=strict)
        print("Runtime env: OK")
    except ConfigValidationError as exc:
        print(f"Runtime env: FAIL ({exc})")
        status = 1

    try:
        memory = get_memory()
        memory.store_shared("healthcheck:last", {"timestamp": time.time()}, importance=0.5)
        _ = memory.retrieve("healthcheck:last")
        print("Memory: OK")
    except Exception as exc:
        print(f"Memory: FAIL ({exc})")
        status = 1

    try:
        bus = get_message_bus()
        stats = bus.get_stats()
        print(f"Message bus: OK (agents={stats.get('total_agents', 0)})")
    except Exception as exc:
        print(f"Message bus: FAIL ({exc})")
        status = 1

    return status


def test_system() -> int:
    _print_header("MAMS Tests")
    rc = run_healthcheck(strict=False)
    if rc != 0:
        return rc

    print("Running unit tests...")
    result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], check=False)
    return result.returncode


def install_dependencies() -> int:
    _print_header("Install Dependencies")
    cmds = [
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        [sys.executable, "-m", "pip", "install", "-r", "requirements-optional.txt"],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


def main():
    parser = argparse.ArgumentParser(description="MAMS - Matrix Agentic Money System")
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "worker", "dashboard", "agent", "test", "install", "healthcheck"],
        help="Command to run",
    )
    parser.add_argument("--agent", type=str, help="Agent ID to run")
    parser.add_argument("--port", type=int, default=8050, help="Dashboard port")
    parser.add_argument("--mode", type=str, default="autonomous", help="System mode")
    parser.add_argument("--strict", action="store_true", help="Require all production env values")
    args = parser.parse_args()

    if args.command == "run":
        run_system(mode=args.mode, port=args.port)
        return
    if args.command == "worker":
        run_worker(mode=args.mode)
        return
    if args.command == "dashboard":
        run_dashboard(port=args.port)
        return
    if args.command == "agent":
        if not args.agent:
            raise ValueError("--agent required for 'agent' command")
        run_agent(args.agent)
        return
    if args.command == "test":
        raise SystemExit(test_system())
    if args.command == "install":
        raise SystemExit(install_dependencies())
    if args.command == "healthcheck":
        raise SystemExit(run_healthcheck(strict=args.strict))


if __name__ == "__main__":
    main()
