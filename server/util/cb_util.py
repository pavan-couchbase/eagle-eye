from couchbase.cluster import Cluster, ClusterOptions
from couchbase_core.cluster import PasswordAuthenticator
from couchbase.exceptions import DocumentExistsException
from constants.queries import Queries

class CBConnection:
    def __init__(self, username, password, host):
        self.cluster = Cluster("couchbase://{0}".format(host), ClusterOptions(
            PasswordAuthenticator(username, password)
        ))

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
