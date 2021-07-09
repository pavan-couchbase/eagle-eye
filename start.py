from flask_restful import Api, Resource, reqparse
import time
import json
import uuid
from task import Task
from task_manager import TaskManager
from util import get_parameters, print_queue


class Start(Resource):
    def __init__(self, initq, running_map, task_managers, cb, waiting_jobids, num_threads):
        self.initq = initq
        self.running_map = running_map
        self.num_threads = num_threads
        self.task_managers = task_managers
        self.cb = cb
        self.waiting_jobids = waiting_jobids

    # API Request Types
    def get(self):
        return {"Initialized Queue": print_queue(self.initq),
                "Started Queue": self.running_map}, 200

    def post(self):
        parser = reqparse.RequestParser()

        # Unique Identifier
        parser.add_argument('host', required=True)
        parser.add_argument('clustername', required=True)
        parser.add_argument('build', required=True)

        # Optional configuration
        parser.add_argument('configfile', required=False)
        parser.add_argument('restusername', required=False)
        parser.add_argument('restpassword', required=False)
        parser.add_argument('sshusername', required=False)
        parser.add_argument('sshpassword', required=False)
        parser.add_argument('dockerhost', required=False)
        parser.add_argument('emails', required=False)
        parser.add_argument('alertfrequency', required=False)

        args = parser.parse_args()

        # Read configuration file
        if args['configfile'] is not None:
            try:
                run_configuration = json.loads(args['configfile'])
            except Exception as e:
                return {"Error": "Issue loading config",
                        "Msg": str(e)}, 400
        else:
            run_configuration = json.load(open('./config/default.json'))

        # generate unique id
        job_id = uuid.uuid1()

        '''
        while True:
            if is valid:
                break
            else:
                reroll id
        '''

        # parse into task objects
        for task in run_configuration.keys():
            self.initq.put(Task(task_type=task, parameters=get_parameters(run_configuration[task]),
                                loop_interval=run_configuration[task]['loop_interval'], job_id=job_id))
            self.waiting_jobids.put(job_id)

        # if this is a new id, create a new task_manager and store it in the task managers dictionary
        if job_id not in self.task_managers:
            if args['restusername'] is None and args['restpassword'] is None:
                rest_username = 'Administrator'
                rest_password = 'password'
            else:
                rest_username = args['restusername']
                rest_password = args['restpassword']

            if args['sshusername'] is None and args['sshpassword'] is None:
                ssh_username = 'root'
                ssh_password = 'couchbase'
            else:
                ssh_username = args['sshusername']
                ssh_password = args['sshpassword']

            email_list = []
            if args['emails'] is not None:
                email_list = args['emails'].replace(" ", "").split(",")

            # if one is specified, both should be specified
            if (args['alertfrequency'] is not None and args['emails'] is None) or (
                    args['alertfrequency'] is None and args['emails'] is not None):
                return {"Msg": "Both alert frequency and emails must be specified"}, 400

            email_list = []
            if args['emails'] is not None:
                email_list = args['emails'].replace(" ", "").split(",")

            if args['alertfrequency'] is not None:
                try:
                    alert_freq = int(args['alertfrequency'])
                except TypeError as e:
                    return {"Msg": "Alert Frequency must be an int", "Error": e}, 400
            else:
                alert_freq = 3600

            # calculate how many threads we can allocate
            num_tasks = len(run_configuration)
            num_available = self.num_threads - len(self.running_map)

            if num_tasks > num_available and num_available != 0:
                num_tasks = self.num_threads - len(self.running_map) - 1

            start_time = time.time()
            self.task_managers[str(job_id)] = TaskManager(job_id=str(job_id),
                                                          cluster_name=args['clustername'],
                                                          build=args['build'],
                                                          master_node=args['host'],
                                                          num_threads=num_tasks,
                                                          cb_instance=self.cb,
                                                          email_list=email_list,
                                                          rest_username=rest_username, rest_password=rest_password,
                                                          ssh_username=ssh_username, ssh_password=ssh_password,
                                                          alert_interval=alert_freq
                                                          )

        # check if there are available threads
        while self.initq.empty() is not True and len(self.running_map) < self.num_threads:
            try:
                self.task_runner(job_id)
                self.waiting_jobids.get()
            except TypeError as e:
                return {"Msg": "Error starting Data Collectors", "Error": e}, 400

        return {"id": str(job_id)}, 200

    def delete(self):
        pass

    # Helper Functions
    def task_runner(self, job_id):
        # remove from init queue and push to start queue then start task
        task = self.initq.get()
        self.running_map[str(job_id) + ":_:" + str(task)] = self.task_managers[str(job_id)].start_task(task=task)
