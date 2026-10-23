# linux-runner

A manually dispatched GitHub Actions job that runs commands on a GitHub-hosted Linux machine (`ubuntu-24.04`, free for public repositories). It checks out any public repository at a branch, tag or commit, optionally prepares it with a preset and starts a PostgreSQL 16 server, runs the given commands, and keeps the logs as an artifact for 7 days.

It is used to run heavy test suites, linters and Postgres-backed tests in the cloud instead of on a local machine.

## Use

```bash
python -I run.py --repo AliceMessi/openminion --ref fix/my-branch --preset openminion --postgres \
    --label my-check -- "make lint && make test-critical"
```

`run.py` dispatches the workflow, waits for it, downloads the logs into `linux-runner-logs/<label>-<timestamp>/` (`head.txt`, `setup.log`, `run.log`, `result.txt`) and exits with the run's status. Runs can also be started from the Actions tab.

Presets:
- `none`: nothing is installed.
- `python`: `pip install -e .[dev]`, falling back to `pip install -e .`, then `requirements.txt`.
- `openminion`: clones `openminion-eval` into `.deps` (branch `dev` by default) and runs `make dev-install`, as OpenMinion's CI does.

`--postgres` starts `postgres:16` on `localhost:5432` (user `postgres`, password `test`) and exports `OPENMINION_TEST_POSTGRES_URL`.

## Safety

- The workflow has `contents: read` permission only and uses no secrets.
- The target checkout does not keep credentials.
- Actions are pinned to commit SHAs.
- Logs are public, so never pass keys or personal data in commands.
- Only the repository owner can dispatch runs.
