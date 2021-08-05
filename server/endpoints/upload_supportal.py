from flask_restful import Resource, reqparse
import os
import subprocess
import shutil
import requests
import json
import time


class UploadSupportal(Resource):
    def __init__(self, initq, cb):
        self.cb = cb

    def post(self):
        parser = reqparse.RequestParser()

        parser.add_argument('id', required=True)
        parser.add_argument('iteration', required=True)

        args = parser.parse_args()

        res = self.cb.upload_supportal(args['id'], args['iteration'])

        jobId = args['id']
        # download the files
        for url in res['data']:
            try:
                subprocess.run(["wget", url, "-P", "./server/supportal/{0}".format(jobId)], capture_output=False)
            except Exception as e:
                return {"Msg": str(e)}, 400

        # upload the files
        for filename in os.listdir('./server/supportal/{0}'.format(jobId)):
            try:
                subprocess.run(['curl', '-T', './server/supportal/{0}/{1}'.format(jobId, filename), 'https://cb-engineering.s3.amazonaws.com/cb-qe-eagle-eye/', '-#', '-o', '/dev/null'])
            except Exception as e:
                return {"Msg": str(e)}, 400

        shutil.rmtree("./server/supportal/{0}".format(jobId))

        # probe
        probing = True
        start_time = time.time()
        while probing and time.time() < start_time + (60 * 30):
            response = requests.get('https://supportal.couchbase.com/api/snapshots/CB%20QE%20Eagle%20Eye')

            if response.status_code != 200:
                return {"Msg": "Error accessing supportal snapshots API"}, 400

            content = json.loads(response.content)

            prob_res = self.probe_snapshots(res['data'], content['snapshots'])

            if prob_res != "":
                self.cb.update_snapshot_url(args['id'], args['iteration'], prob_res)
                return {"Msg": "success"}, 200

            time.sleep(300)

        return {"Msg": "No snapshot found in 30 minutes"}, 400

    def probe_snapshots(self, urls, snapshots):
        for snapshot in snapshots:
            if len(list(set([x.lower().split('/')[-1] for x in urls]) & set([x.lower().split('/')[-1] for x in snapshot['urls']]))) > 0:
                return snapshot['snapshot_url']

        return ""
