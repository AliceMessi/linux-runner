"""Run commands on a GitHub-hosted Linux machine through AliceMessi/linux-runner.

    python -I run.py --repo AliceMessi/openminion --ref fix/my-branch --preset openminion \
        [--postgres] [--label name] [--out DIR] -- "make lint && make test-critical"

Dispatches the `run` workflow, waits for it, downloads the logs artifact into
--out (default: ./linux-runner-logs/<label>) and exits with the run's status.
Nothing secret is sent: the workflow has no secrets and its logs are public.
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RUNNER_REPO = "AliceMessi/linux-runner"
WORKFLOW = "run.yml"


def gh(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", check=check)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--preset", default="none", choices=["none", "python", "openminion"])
    parser.add_argument("--postgres", action="store_true")
    parser.add_argument("--python", default="3.11")
    parser.add_argument("--eval-branch", default="dev")
    parser.add_argument("--label", default="")
    parser.add_argument("--out", default="")
    parser.add_argument("command", nargs="+")
    args = parser.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    label = f"{args.label or args.ref.replace('/', '-')}-{stamp}"
    gh(
        "workflow", "run", WORKFLOW, "-R", RUNNER_REPO,
        "-f", f"repo={args.repo}", "-f", f"ref={args.ref}", "-f", f"preset={args.preset}",
        "-f", f"postgres={'true' if args.postgres else 'false'}", "-f", f"python={args.python}",
        "-f", f"eval_branch={args.eval_branch}", "-f", f"label={label}",
        "-f", f"command={' '.join(args.command)}",
    )
    run_id = None
    for _ in range(30):
        time.sleep(4)
        runs = json.loads(gh("run", "list", "-R", RUNNER_REPO, "--workflow", WORKFLOW, "--limit", "20",
                             "--json", "databaseId,displayTitle").stdout)
        match = [r for r in runs if r["displayTitle"] == label]
        if match:
            run_id = match[0]["databaseId"]
            break
    if run_id is None:
        print("run not found for label", label)
        return 2
    print(f"run {run_id}: https://github.com/{RUNNER_REPO}/actions/runs/{run_id}", flush=True)
    gh("run", "watch", str(run_id), "-R", RUNNER_REPO, "--interval", "30", check=False)
    view = json.loads(gh("run", "view", str(run_id), "-R", RUNNER_REPO, "--json", "conclusion,status").stdout)
    out = Path(args.out or Path("linux-runner-logs") / label)
    out.mkdir(parents=True, exist_ok=True)
    gh("run", "download", str(run_id), "-R", RUNNER_REPO, "-n", "logs", "-D", str(out), check=False)
    result = out / "result.txt"
    print("conclusion:", view.get("conclusion"), "|", result.read_text(encoding="utf-8").strip() if result.exists() else "no result.txt")
    run_log = out / "run.log"
    if run_log.exists():
        tail = run_log.read_text(encoding="utf-8", errors="replace").splitlines()[-25:]
        print("\n".join(tail))
    print("logs:", out.resolve())
    return 0 if view.get("conclusion") == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
