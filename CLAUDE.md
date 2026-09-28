# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Hard rules (set by the repository owner)

- **Never run commands outside the workspace** `/mnt/Dati4/Workspace/PythonExamples`: no reading, writing or executing anything in other paths (the only exception is the session scratchpad provided by Claude Code for temporary files).
- **Cloud commands only after explicit confirmation**: before running `aws`, `az`, `cdk`, `sam`, `serverless` (and any other tool that acts on a cloud account, e.g. `gcloud`), show the exact command, say what it does (and whether it costs money or changes resources) and wait for the user's confirmation. Each command needs its own confirmation: a previous "yes" does not cover the next one. The same applies to running scripts or apps from this repo that call real cloud APIs through an SDK (boto3, Azure SDK), e.g. starting a Manager that queries AWS.
- **Never run git commands**, read-only ones included (`git status`, `git diff`, `git log`, ...). To know what changed, read the files; commits are made by the user.

## What this repository is

A collection of independent Python examples by AlNao ("Python Examples"), documented in Italian. There is no global build, lint or test setup: every folder is a self-contained project with its own `README.md` and usually its own `requirements.txt`.

- The root `README.md` has a table that indexes every example by section (AI, AWS, Azure, DataScientist, Django, Docker, FromOthersSites, ManageFile, RobotFramework, Simple); `ROADMAP.md` tracks planned and completed work.
- Code comments, READMEs and UI text are in Italian; every README ends with the same "`# < AlNao />`" block and the GPL license section (copy it from an existing README when creating a new project).
- `FromOthersSites/` holds code adapted from tutorials: the README of each example cites the original source.

## Environment and commands

- Shared virtualenv at the repository root: `.venv` (Python 3.13). Some projects have their own venv (e.g. `AI/AlNaoAIRunners/venv`).
  ```bash
  .venv/bin/pip install -r <project>/requirements.txt
  cd <project> && ../../.venv/bin/python app.py      # adjust the relative path to .venv
  ```
- Tests exist only in a few places:
  - AWS CDK projects (`AWS/CDK/cdkNN*/tests/unit/`): `cd AWS/CDK/<project> && pytest tests/unit`, single test with `pytest tests/unit/test_<file>.py::<test_name>` (the unit tests only synthesize the stack locally).
  - Robot Framework suites: `robot <file>.robot` inside `RobotFramework/Es0*` and `Docker/10RobotFramework` (they need the services under test running, see each README).
- Docker examples are run with `docker compose up` from their folder (see each README).

## AWS/Managers (Flask web apps)

Same structure for every manager: a class wrapping boto3 (`tag_manager.py`, `cost_explorer.py`, `cloudwatch_manager.py`), `app.py` with Flask pages and a JSON REST API, `templates/` with Bootstrap 5 and `static/` with vanilla JS (libraries only from cdnjs). Settings live in `config.json`, overridable with environment variables. Ports: TagManager 5002, CostExplorer 5003.

- **TagManager**: lists and edits resource tags by merging two sources (Resource Groups Tagging API + Resource Explorer). Its `config.json` (`suggested_tags`, `regions`, `compliant_tags`, `resources_skipped`) is also read by CostExplorer; for `Project` a value that extends a suggested one (`Paths.games.aws.serverless` under `Paths.games`) is shown as its child (`static/tag_match.js`, same rule in CostExplorer).
- **CostExplorer**: cost reports by service and by tag. Every Cost Explorer API request costs 0.01 $, and the design depends on that:
  - the page never calls AWS on its own: it asks the server with `cache_only=1` and, when data is missing, shows "Carica i dati dal cloud" with a confirmation modal that lists the requests and their cost. Do not add automatic Cost Explorer calls.
  - `cost_cache.py`: disk cache that never expires, one file per month (`cache/costs/<filters>/YYYY-MM.json`); a request loads only missing months, one call per run of consecutive months. Months read before month end are marked incomplete and are refreshed only on explicit user request. Never delete or overwrite cached months (the data has been paid for); old-format files were migrated to `cache/legacy/`.
  - `cur_source.py`: free source from AWS Data Exports (CUR 2.0 Parquet on S3, configured in `.env`, template `.env.example`). For each month the order is Data Export → API cache → paid API with confirmation. The Parquet files are reduced to a daily table in `cache/cur/` and queried to produce the same series as the API, with service names mapped to the Cost Explorer ones (`SERVICE_NAMES`, `cur_service_names` in `config.json`).
  - the browser computes charts, cross filters, zoom (month/week/day) and tables from rows `{period, month, service, group, amount}`; `static/charts.js` holds the fixed 8-color palette, colors follow the entity, not its rank.
