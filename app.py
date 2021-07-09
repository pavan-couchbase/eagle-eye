from flask import Flask
from flask_restful import Api, Resource, reqparse
import queue
from start import Start
from stop import Stop
from get_data import GetData
from status import Status
from cb_util import CBConnection


num_threads = 15


class App:
    def __init__(self):
        self.app = Flask(__name__)
        self.api = Api(self.app)

        self.initq = queue.Queue()
        self.waiting_jobids = queue.Queue()
        self.running_map = {}
        self.task_managers = {}

        # establish connection to the CB Database
        self.cb = CBConnection("Administrator", "password", "172.23.100.10")

        self.api.add_resource(Start, '/start', resource_class_args=(self.initq, self.running_map, self.task_managers, self.cb, self.waiting_jobids, num_threads))
        self.api.add_resource(Stop, '/stop', resource_class_args=(self.initq, self.running_map, self.task_managers, self.waiting_jobids, num_threads))
        self.api.add_resource(GetData, '/get-data', resource_class_args=(self.initq, self.running_map, self.task_managers, self.cb))
        self.api.add_resource(Status, '/status', resource_class_args=(self.initq, self.running_map, self.task_managers))

    def run(self):
        self.app.run()


if __name__ == '__main__':
    App().run()
