from couchbase.cluster import Cluster, ClusterOptions, QueryOptions
from couchbase_core.cluster import PasswordAuthenticator
from couchbase.exceptions import DocumentExistsException


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

    def get_data(self, id, dc_name=None):
        query = "SELECT VALUE e FROM `eagle-eye` e WHERE e.id = '{0}'".format(id)
        if dc_name is not None:
            query += " AND EXISTS {0}".format(dc_name)

        res = self.cb.query(query)
        result_arr = [x for x in res]
        return result_arr
