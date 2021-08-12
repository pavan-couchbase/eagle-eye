from couchbase.cluster import Cluster, ClusterOptions, ClusterTimeoutOptions
from couchbase_core.cluster import PasswordAuthenticator
from couchbase.exceptions import DocumentExistsException
from constants.queries import Queries
from datetime import timedelta


class CBConnection:
    def __init__(self, username, password, host):
        timeout_options = ClusterTimeoutOptions(kv_timeout=timedelta(seconds=300), query_timeout=timedelta(seconds=360))
        options = ClusterOptions(PasswordAuthenticator(username, password), timeout_options=timeout_options)
        self.cluster = Cluster("couchbase://{0}".format(host), options=options)

        self.cb = self.cluster.bucket("eagle-eye")
        self.cb_coll = self.cb.default_collection()

    def insert_doc(self, id, doc):
        # logger.info("Inserting Document")
        try:
            self.cb_coll.insert(id, doc)
            return True
        except DocumentExistsException:
            return False

    def upload_supportal(self, id, iteration):
        query = Queries.get_logs.format(id, iteration)

        res = self.cb.query(query)
        result_arr = [x for x in res]

        return result_arr[0]

    def update_snapshot_url(self, job_id, iteration, snap_url):
        query = Queries.update_snapshot_url.format(snap_url, job_id, iteration)
        res = self.cb.query(query)
        if res.meta['status'] == 'success':
            print("Success Changed")

    def update_snapshot_status(self, job_id, iteration, status):
        query = Queries.update_snapshot_progress_status.format(status, job_id, iteration)
        res = self.cb.query(query)
        if res.meta['status'] == 'success':
            print("Success Changed")

    def update_snapshot_error(self, job_id, iteration, error):
        query = Queries.update_snapshot_progress_error.format(error, job_id, iteration)
        res = self.cb.query(query)
        if res.meta['status'] == 'success':
            print("Success Changed")

    def get_data(self, id=None, cluster_name=None, build=None, iter_num=None, dc_name=None):
        # logic to run the correct query
        if id is not None:
            query = Queries.id_get_data.format(id)
        else:
            query = Queries.bcn_get_data.format(build, cluster_name)

        if dc_name is not None:
            if id is not None:
                query = Queries.id_dc_get_data.format(id, dc_name)
            else:
                query = Queries.bcn_dc_get_data.format(build, cluster_name, dc_name)
        if iter_num is not None and dc_name is None:
            if id is not None:
                query = Queries.id_iter_get_data(id, iter_num)
            else:
                query = Queries.bcn_iter_get_data.format(build, cluster_name, iter_num)
        if iter_num is not None and dc_name is not None:
            if id is not None:
                query = Queries.id_iter_dc_get_data(id, iter_num, dc_name)
            else:
                query = Queries.bcn_iter_dc_get_data.format(build, cluster_name, iter_num, dc_name)

        res = self.cb.query(query)
        result_arr = [x for x in res]
        return result_arr
