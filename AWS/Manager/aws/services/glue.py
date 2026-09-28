"""Glue: job ed esecuzioni."""

from aws.services import paginate


class AwsGlue:
    def __init__(self, session):
        self.client = session.client('glue')

    def jobs(self):
        return paginate(self.client, 'get_jobs', 'Jobs')

    def job(self, name):
        return self.client.get_job(JobName=name)['Job']

    def runs(self, name, limit=100):
        return paginate(self.client, 'get_job_runs', 'JobRuns', limit=limit, JobName=name)
