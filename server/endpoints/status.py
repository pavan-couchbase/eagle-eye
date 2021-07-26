from flask_restful import Resource, reqparse
from server.util.util import id_print_queue


class Status(Resource):
    def __init__(self, initq, running_map, task_manager):
        self.initq = initq
        self.running_map = running_map
        self.task_manager = task_manager

    def post(self):
        parser = reqparse.RequestParser()

        # required
        parser.add_argument("id", required=True)

        args = parser.parse_args()

        running = {}

        for k, v in self.running_map.items():
            if k.split(":_:")[0] == args['id']:
                running[k.split(":_:")[1]] = str(v)

        return {"Running": str(running), "Waiting": id_print_queue(self.initq, args['id'])}, 200
