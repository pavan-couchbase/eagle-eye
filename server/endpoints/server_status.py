from flask_restful import Resource


class ServerStatus(Resource):
    def __init__(self, initq, task_managers):
        self.task_managers = task_managers

    def post(self):
        try:
            data = []
            for k, v in self.task_managers.items():
                data.append(v.tm_JSON())

            return {"data": data}, 200
        except Exception as e:
            return {"Msg": str(e)}, 400
