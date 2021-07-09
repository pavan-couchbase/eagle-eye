from flask_restful import Api, Resource, reqparse
import shutil

"""
The code that handles the /stop API end point
"""


class Stop(Resource):
    def __init__(self, initq, running_map, task_managers, waiting_jobids, num_threads):
        # have access to the app init queue, running threads, and active task managers
        self.initq = initq
        self.running_map = running_map
        self.task_managers = task_managers
        self.waiting_jobids = waiting_jobids
        self.num_threads = num_threads

    def post(self):
        """
        Handles the post request to the /stop API end point
        :return: JSON object and status code
        """
        parser = reqparse.RequestParser()
        parser.add_argument('id', required=True)

        args = parser.parse_args()

        if args['id'] is not None:
            if args['id'] in self.task_managers.keys():
                # shutdown will wait for all threads to stop
                self.task_managers[args['id']].shutdown()

                to_delete = []
                for k, v in self.running_map.items():
                    if k.split(":_:")[0] == args['id']:
                        to_delete.append(k)

                # rm -rf the dir, init the stop process, and delete from task managers map and running map
                del self.task_managers[args['id']]
                for k in to_delete:
                    del self.running_map[k]

                shutil.rmtree("./" + args['id'])

                # if there are tasks waiting, start them
                started_jobs = []
                while self.initq.empty() is not True and len(self.running_map) < self.num_threads:
                    try:
                        job_id = self.waiting_jobids.get()
                        started_jobs.append(str(job_id))
                        self.task_runner(job_id)
                    except TypeError as e:
                        return {"Msg": "Error starting Data Collectors", "Error": e}, 400

                if len(started_jobs) > 0:
                    return {"Msg": "Jobs Stopped", "Started Jobs": started_jobs}, 200

                return {"Msg": "Jobs Stopped"}, 200
            else:
                # id is not present, return error code
                return {"Msg": "ID not active"}, 400
        else:
            # user did not add id to post request, return error code
            return {"Msg": "Missing ID Parameter"}, 400

    def get(self):
        return {"Msg": "GET not supported for stop API"}, 400

    def delete(self):
        return {"Msg": "DELETE not supported for stop API"}, 400

    # Helper Functions
    def task_runner(self, job_id):
        # remove from init queue and push to start queue then start task
        task = self.initq.get()
        self.running_map[str(job_id) + ":_:" + str(task)] = self.task_managers[str(job_id)].start_task(task=task)
