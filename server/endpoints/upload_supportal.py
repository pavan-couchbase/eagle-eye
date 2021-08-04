from flask_restful import Resource, reqparse
import os
import subprocess
import shutil

class UploadSupportal(Resource):
    def __init__(self, initq, cb):
        self.cb = cb


    def post(self):
        parser = reqparse.RequestParser()

        parser.add_argument('id', required=True)
        parser.add_argument('iteration', required=True)

        args = parser.parse_args()

        res = self.cb.upload_supportal(args['id'], args['iteration'])

        # download the files
        for url in res['data']:
            try:
                subprocess.run(["wget", url, "-P", "./server/supportal"], capture_output=False)
            except Exception as e:
                return {"Msg": str(e)}, 400

        # upload the files
        for filename in os.listdir('./server/supportal'):
            try:
                subprocess.run(['curl', '-T', './server/supportal/{0}'.format(filename), 'https://cb-engineering.s3.amazonaws.com/cb-qe-eagle-eye/', '-#', '-o', '/dev/null'])
            except Exception as e:
                return {"Msg": str(e)}, 400

        shutil.rmtree("./server/supportal")

        return {"Msg": "success"}, 200
