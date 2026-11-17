# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Hard rules (set by the repository owner)

- **Never run commands outside the workspace** `/mnt/Dati4/Workspace/PythonExamples`: no reading, writing or executing anything in other paths (the only exception is the session scratchpad provided by Claude Code for temporary files).
- **Cloud commands only after explicit confirmation**: before running `aws`, `az`, `cdk`, `sam`, `serverless` (and any other tool that acts on a cloud account, e.g. `gcloud`), show the exact command, say what it does (and whether it costs money or changes resources) and wait for the user's confirmation. Each command needs its own confirmation: a previous "yes" does not cover the next one. The same applies to running scripts or apps from this repo that call real cloud APIs through an SDK (boto3, Azure SDK), e.g. starting a Manager that queries AWS.
- **Never run git commands**, read-only ones included (`git status`, `git diff`, `git log`, ...). To know what changed, read the files; commits are made by the user.
- Every README.md must have two last sections: 
  - changelog : add a row every time I ask you change code inside folder, the description must be max 10 worlds
  - "alnao footer" is always the same and never change it if there are not into readme file.

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
  - `AWS/CDK/cdk32wikiS3Vector` and `AWS/CDK/cdk33bedrockServerless`: same command; besides the stack synthesis it tests the Lambdas with fake S3, S3 Vectors and Bedrock clients (no AWS calls). The real deploy needs `./build_layer.sh` first.
  - `AWS/CDK/cdk26blockchainLambda` and `AWS/CDK/cdk30WebSocket`: same command; `tests/unit/test_lambda.py` also tests the Lambdas (blockchain, game rules) with fake DynamoDB tables and WebSocket client.
  - Most projects with Lambdas (cdk05-cdk10, cdk12, cdk15, cdk16) also have a `tests/unit/test_lambda.py` with fake AWS clients. `AWS/CDK/cdk12lambdaApplicationS3Utils` needs `./build_layer.sh` (openpyxl and paramiko, ARM64 wheels, no Docker) before the real deploy; its tests use an empty temporary layer.
  - The CDK tests of every project (cdk01-cdk34) load the `context` of `cdk.json` (feature flags), as the CLI does; every project has a `test_all_resources_tagged` with the list of untaggable types. Every project tags its resources through `<package>/tags.py` (`apply_tags`, priority 300, aspect for raw Role/Lambda; projects with launch templates also tag instances, volumes and network interfaces through them). The `LambdaLogGroups` aspect of `tags.py` gives every Lambda, including CDK's own support Lambdas (bucket auto-delete, S3 notifications, default security group), a stack log group `/aws/lambda/<function name>` (tags, 7 days, deleted on destroy) and replaces `AWSLambdaBasicExecutionRole` with write access to that group only, so Lambda never creates untagged log groups (`test_every_lambda_has_a_stack_log_group`).
  - Resource names (all 34 projects): the stack is `aws-py-cdkXX` (in `app.py` and in the tests' `STACK_NAME`) and every resource is `aws-py-cdkXX-<servizio>`, lowercase with `-`, with the `Name` tag equal to the name; the CloudFormation stack itself gets `Name = aws-py-cdkXX` (`test_stack_tags`), and CloudFormation propagates stack tags only where the resource has no tag with the same key. `<package>/naming.py` (same file in every project) holds the rules: `nome_risorsa(self, "servizio")` for names written in code (needed whenever a resource is referenced by name as a string, e.g. Glue connections/classifiers, AppSync data sources used by resolvers, ARNs built by hand, dashboard URLs), the `PhysicalNames` aspect (registered by `apply_tags`) that names every other resource from its construct id, CDK's own resources included, and `check_template()` used by `test_all_resources_named`. Exceptions: S3 buckets end with the account id (`-<account>`, taken by CDK, never a parameter), IAM roles and instance profiles end with the region, log groups keep the service path (`/aws/lambda/…`, `/aws-glue/jobs/…`, `/aws/vendedlogs/states/…`; AppSync's `/aws/appsync/apis/<id>` is fixed by the service), Glue catalog databases and AppSync data sources use `_` (`aws_py_cdkXX_…`), the ECS capacity provider is `cp-aws-py-cdkXX-…` (names can't start with `aws`), resources without a name property (EC2, EIP, ENI, EFS, VPC, CloudFront, API stages, …) only get the `Name` tag. `check_template()` also reports a replaced name still quoted as a string in the template: such names must be set in code with `nome_risorsa`. The CDK bootstrap (`alnao-dev-cdk`) keeps its own names. `cdk22cloudWatchAlarm` extends the stack class of `../cdk21autoScalingWordpress` (sys.path import): keep the two folders side by side.
  - Robot Framework suites: `robot <file>.robot` inside `RobotFramework/Es0*` and `Docker/10RobotFramework` (they need the services under test running, see each README).
- Docker examples are run with `docker compose up` from their folder (see each README).
- CDK projects that need a network use by default the account's **default VPC** and its subnets: `<package>/network.py` (same file in every project) looks them up at synth (`Vpc.from_lookup(is_default=True)`, or `-c vpc_id=...`) and uses them as defaults of the `vpcid`/`subnetid*` CfnParameters, which stay overridable at deploy. These stacks need `env` (account/region from `CDK_DEFAULT_*`) in `app.py`; `cdk.context.json` is gitignored; the tests pass a fake env and get CDK's dummy VPC (`vpc-12345`, subnets `s-12345`/`s-67890`). Only `cdk25vpcEndpoint` creates its own VPC (it is the subject of the example).
- Every CDK app (`AWS/CDK/cdk*`) uses the account's custom bootstrap from `AWS/CDK/bootstrap/` (bucket and ECR `alnao-dev-cdk`, SSM `/cdk-bootstrap/alnao/dev/version`, qualifier `alnaodev`) through the `SYNTHESIZER` block in `app.py`; a new CDK project must copy that block and pass `synthesizer=SYNTHESIZER` to its stack. `bootstrap.sh create|destroy <region>` creates the bootstrap or removes it from a region (stack, ECR, versioned asset bucket).

## AWS/Managers (Flask web apps)

Same structure for every manager: a class wrapping boto3 (`tag_manager.py`, `cost_explorer.py`, `cloudwatch_manager.py`), `app.py` with Flask pages and a JSON REST API, `templates/` with Bootstrap 5 and `static/` with vanilla JS (libraries only from cdnjs). Settings live in `config.json`, overridable with environment variables. Ports: TagManager 5002, CostExplorer 5003.

- **TagManager**: lists and edits resource tags by merging two sources (Resource Groups Tagging API + Resource Explorer). Its `config.json` (`suggested_tags`, `regions`, `compliant_tags`, `resources_skipped`) is also read by CostExplorer; for `Project` a value that extends a suggested one (`Paths.games.aws.serverless` under `Paths.games`) is shown as its child (`static/tag_match.js`, same rule in CostExplorer).
- **CostExplorer**: cost reports by service and by tag. Every Cost Explorer API request costs 0.01 $, and the design depends on that:
  - the page never calls AWS on its own: it asks the server with `cache_only=1` and, when data is missing, shows "Carica i dati dal cloud" with a confirmation modal that lists the requests and their cost. Do not add automatic Cost Explorer calls.
  - `cost_cache.py`: disk cache that never expires, one file per month (`cache/costs/<filters>/YYYY-MM.json`); a request loads only missing months, one call per run of consecutive months. Months read before month end are marked incomplete and are refreshed only on explicit user request. Never delete or overwrite cached months (the data has been paid for); old-format files were migrated to `cache/legacy/`.
  - `cur_source.py`: free source from AWS Data Exports (CUR 2.0 Parquet on S3, configured in `.env`, template `.env.example`). For each month the order is Data Export → API cache → paid API with confirmation. The Parquet files are reduced to a daily table in `cache/cur/` and queried to produce the same series as the API, with service names mapped to the Cost Explorer ones (`SERVICE_NAMES`, `cur_service_names` in `config.json`).
  - the browser computes charts, cross filters, zoom (month/week/day) and tables from rows `{period, month, service, group, amount}`; `static/charts.js` holds the fixed 8-color palette, colors follow the entity, not its rank.



## AWS Tagging convention (applies to every resource on AWS cloud)

Every resource created/managed in AWS that supports tags carries the standard tags of its example (`Descrizione` = the folder path after the "AWS" level, with "." between subfolders: `AWS/CDK/cdk01bucketS3` becomes `CDK.cdk01bucketS3`, so `Project = Development.aws.py-CDK.cdk01bucketS3`; for folders outside AWS the first level is kept: `Docker/03ApiPersoneNoDb` becomes `Docker.03ApiPersoneNoDb`, so `Project = Development.aws.py-Docker.03ApiPersoneNoDb`):
```
Name        = "aws-py-<Descrizione>"
Environment = "dev"
Project     = "Development.aws.py-<Descrizione>"
Owner       = "AlNao"
CostCenter  = "dev"
ManagedBy   = "Manual/Terraform/CloudFormation/Sh/CDK"
```
`ManagedBy` follows the tool that creates the resource: `Sh` for AWS CLI scripts/commands and Serverless Framework, `CDK` for CDK stacks, `Manual` for the console and for Python code using boto3 (AWS/SDK, AWS/Manager, scripts).
For the CDK examples (`AWS/CDK/cdk*`) `Name` is different for every resource and equals its name, `aws-py-cdkXX-<servizio>` (see the CDK section above); `Project` and the other tags stay as above.


