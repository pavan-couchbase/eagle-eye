from flask_restful import Resource, reqparse
import time
import json
import uuid
from util.task import Task
from util.task_manager import TaskManager
from util.util import get_parameters, print_queue, check_unique_host, check_unique_cluster_name
from constants.defaults import Default


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

        # Optional configuration
        parser.add_argument('configfile', required=False)
        parser.add_argument('runall', required=False)
        parser.add_argument('restusername', required=False)
        parser.add_argument('restpassword', required=False)
        parser.add_argument('sshusername', required=False)
        parser.add_argument('sshpassword', required=False)
        parser.add_argument('dockerhost', required=False)
        parser.add_argument('emails', required=False)
        parser.add_argument('alertfrequency', required=False)
        parser.add_argument('runone', required=False)

        args = parser.parse_args()

        if check_unique_host(args['host'], self.task_managers):
            return {"Msg": "Host already running data collectors"}, 400

        if check_unique_cluster_name(args['clustername'], self.task_managers):
            return {"Msg": "Cluster name already running"}, 400

        # Read configuration file
        if args['configfile'] is not None:
            try:
                run_configuration = json.loads(args['configfile'])
            except Exception as e:
                return {"Error": "Issue loading config",
                        "Msg": str(e)}, 400
        else:
            if args['runall'] is not None:
                run_configuration = json.load(open('./server/config/run_all.json'))
            else:
                run_configuration = json.load(open('./server/config/default.json'))

        # generate unique id
        job_id = uuid.uuid1()

        while True:
            results = self.cb.get_data(job_id)
            if len(results) == 0:
                break
            else:
                job_id = uuid.uuid1()

        # parse into task objects
        for task in run_configuration.keys():
            self.initq.put(Task(task_type=task, parameters=get_parameters(run_configuration[task]),
                                loop_interval=run_configuration[task]['loop_interval'], job_id=job_id, host=args['host']))
            self.waiting_jobids.put(job_id)

        # if this is a new id, create a new task_manager and store it in the task managers dictionary
        if job_id not in self.task_managers:
            # validate parameters
            try:
                self.validate_parameters(args)
            except TypeError as e:
                return {"Msg": str(e)}, 400

            # calculate how many threads we can allocate
            num_tasks = len(run_configuration)
            num_available = self.num_threads - len(self.running_map)

            if num_tasks > num_available and num_available != 0:
                num_tasks = self.num_threads - len(self.running_map) - 1

            start_time = time.time()

            if args['runone'] == '1':
                runone = True
            else:
                runone = False

            self.task_managers[str(job_id)] = TaskManager(job_id=str(job_id),
                                                          cluster_name=args['clustername'],
                                                          master_node=args['host'],
                                                          num_threads=num_tasks,
                                                          cb_instance=self.cb,
                                                          email_list=self.email_list,
                                                          rest_username=self.rest_username, rest_password=self.rest_password,
                                                          ssh_username=self.ssh_username, ssh_password=self.ssh_password,
                                                          alert_interval=self.alert_freq,
                                                          run_one=runone
                                                          )

            if not runone:
                self.running_map[str(job_id) + ":_:" + "alert"] = self.task_managers[str(job_id)].start_alert()


        # check if there are available threads
        while self.initq.empty() is not True and len(self.running_map) < self.num_threads:
            try:
                self.task_runner(job_id)
                self.waiting_jobids.get()
            except TypeError as e:
                return {"Msg": "Error starting Data Collectors", "Error": str(e)}, 400
            except AttributeError as e:
                return {"Msg": "Unrecognized Data Collector", "Error": str(e)}, 400

        # if run one, start the shut down process for threads and then wait so we can collect data at the end.
        if runone:
            self.task_managers[str(job_id)].shutdown_collect()
            to_delete = []
            for k, v in self.running_map.items():
                if k.split(":_:")[0] == str(job_id):
                    to_delete.append(k)

            # rm -rf the dir, init the stop process, and delete from task managers map and running map
            del self.task_managers[str(job_id)]
            for k in to_delete:
                del self.running_map[k]

        return {"id": str(job_id)}, 200

    def delete(self):
        pass

    # Helper Functions
    def task_runner(self, job_id):
        # remove from init queue and push to start queue then start task
        task = self.initq.get()
        self.running_map[str(job_id) + ":_:" + str(task)] = self.task_managers[str(job_id)].start_task(task=task)

    def validate_parameters(self, args):
        if args['restusername'] is None and args['restpassword'] is None:
            self.rest_username = Default.rest_username
            self.rest_password = Default.rest_password
        else:
            self.rest_username = args['restusername']
            self.rest_password = args['restpassword']

        if args['sshusername'] is None and args['sshpassword'] is None:
            self.ssh_username = Default.ssh_username
            self.ssh_password = Default.ssh_password
        else:
            self.ssh_username = args['sshusername']
            self.ssh_password = args['sshpassword']

        self.email_list = []
        if args['emails'] is not None:
            self.email_list = args['emails'].replace(" ", "").split(",")

        self.email_list = []
        if args['emails'] is not None:
            self.email_list = args['emails'].replace(" ", "").split(",")

        if args['alertfrequency'] is not None:
            try:
                self.alert_freq = int(args['alertfrequency'])
            except TypeError as e:
                # return {"Msg": "Alert Frequency must be an int", "Error": str(e)}, 400
                raise TypeError("Alert Frequency must be an int")
        else:
            self.alert_freq = Default.alert_interval
