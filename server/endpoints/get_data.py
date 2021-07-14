from flask_restful import Api, Resource, reqparse


class GetData(Resource):
    def __init__(self, initq, running_map, task_managers, cb):
        self.initq = initq
        self.running_map = running_map
        self.task_managers = task_managers
        self.cb = cb

    def post(self):
        parser = reqparse.RequestParser()

        # optional
        parser.add_argument('id', required=False)
        parser.add_argument('iter-num', required=False)
        parser.add_argument('data-collector-name', required=False)
        parser.add_argument('build', required=False)
        parser.add_argument('cluster-name', required=False)

        args = parser.parse_args()

        try:
            self.validate_parameters(args)
        except TypeError as e:
            return {"Msg": str(e)}, 400

        res = self.cb.get_data(args['id'], args['cluster-name'], args['build'], args['iter-num'], args['data-collector-name'])

        return {"data": res}, 200

    def validate_parameters(self, args):
        if args['id'] is None and args['build'] is None and args['cluster-name'] is None:
            raise TypeError("Must specify ID or (build, cluster-name)")

        if args['build'] is not None and args['cluster-name'] is None:
            raise TypeError("Must specify both build and cluster-name")

        if args['build'] is None and args['cluster-name'] is not None:
            raise TypeError("Must specify both build and cluster-name")
