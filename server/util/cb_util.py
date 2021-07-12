from couchbase.cluster import Cluster, ClusterOptions
from couchbase_core.cluster import PasswordAuthenticator
from couchbase.exceptions import DocumentExistsException
from server.constants.queries import Queries

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

    def get_data(self, id, iter_num=None, dc_name=None):
        # logic to run the correct query
        query = Queries.id_get_data.format(id)
        if dc_name is not None:
            query = Queries.id_dc_get_data.format(id, dc_name)
        if iter_num is not None and dc_name is None:
            query = Queries.id_iter_get_data(id, iter_num)
        if iter_num is not None and dc_name is not None:
            query = Queries.id_iter_dc_get_data(id, iter_num, dc_name)

        res = self.cb.query(query)
        result_arr = [x for x in res]
        return result_arr
