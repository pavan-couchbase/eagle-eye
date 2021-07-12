from flask_restful import Api, Resource, reqparse


class GetData(Resource):
    def __init__(self, initq, running_map, task_managers, cb):
        self.initq = initq
        self.running_map = running_map
        self.task_managers = task_managers
        self.cb = cb

    def post(self):
        parser = reqparse.RequestParser()

        # required
        parser.add_argument('id', required=True)

        # optional
        parser.add_argument('iter-num', required=False)
        parser.add_argument('data-collector-name', required=False)

        args = parser.parse_args()

        res = self.cb.get_data(args['id'], args['iter-num'], args['data-collector-name'])

        return {"data": res}, 200
