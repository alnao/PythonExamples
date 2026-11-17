"""Test del job simulato dalle Lambda, in locale: lo stesso giro che fa la Step Function."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "lambda"))

import status  # noqa: E402
import submit  # noqa: E402


def run(event):
    job = submit.lambda_handler(event, None)
    states = [job["status"]]
    while job["status"] == "RUNNING":
        job = status.lambda_handler(job, None)
        states.append(job["status"])
    return job, states


def test_job_succeeds_after_steps():
    job, states = run({"steps": 3})
    assert states == ["RUNNING", "RUNNING", "RUNNING", "SUCCEEDED"]
    assert job["checks"] == 3 and job["jobId"]


def test_job_fails_when_requested():
    job, states = run({"fail": True})
    assert states[-1] == "FAILED"


def test_default_input():
    assert run({})[1] == ["RUNNING", "RUNNING", "SUCCEEDED"]
