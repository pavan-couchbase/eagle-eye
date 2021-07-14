class Task:
    def __init__(self, task_type, parameters, loop_interval, job_id, host):
        self.task_type = task_type
        self.parameters = parameters
        self.loop_interval = loop_interval
        self.job_id = job_id
        self.host = host

    def get_task_type(self):
        return self.task_type

    def get_parameters(self):
        return self.parameters

    def get_loop_interval(self):
        return self.loop_interval

    def get_job_id(self):
        return self.job_id

    def get_host(self):
        return self.host

    def __str__(self):
        return self.task_type

