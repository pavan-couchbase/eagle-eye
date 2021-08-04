class Queries:
    # queries
    # ID

    # get data by id
    id_get_data = "SELECT VALUE e FROM `eagle-eye` e WHERE e.id = '{0}'"

    # get data by id and data collector name
    id_dc_get_data = "SELECT VALUE e FROM `eagle-eye` e WHERE e.id = '{0}' AND {1} IS NOT MISSING"

    # get data by id and iteration num
    id_iter_get_data = "SELECT VALUE e FROM `eagle-eye` e WHERE e.id = '{0}' AND e.iter = {1}"

    # get data by id and iteration num and data collector name
    id_iter_dc_get_data = "SELECT VALUE e FROM `eagle-eye` e WHERE e.id = '{0}' AND e.iter = {1} AND {2} IS NOT MISSING"

    # Build and Cluster Name

    # get data by build and cluster name
    bcn_get_data = "SELECT VALUE e FROM `eagle-eye` e WHERE e.`build` = '{0}' and e.cluster_name = '{1}'"

    # get data by build and cluster name and data collector name
    bcn_dc_get_data = "SELECT VALUE e FROM `eagle-eye` e WHERE e.`build` = '{0}' and e.cluster_name = '{1}' AND {2} IS NOT MISSING"

    # get data by id and iteration num
    bcn_iter_get_data = "SELECT VALUE e FROM `eagle-eye` e WHERE e.`build` = '{0}' and e.cluster_name = '{1}' AND e.iter = {2}"

    # get data by id and iteration num and data collector name
    bcn_iter_dc_get_data = "SELECT VALUE e FROM `eagle-eye` e WHERE e.`build` = '{0}' and e.cluster_name = '{1}' AND e.iter = {2} AND {3} IS NOT MISSING"

    # upload to supportal query
    get_logs = "SELECT e.logs.data FROM `eagle-eye` e WHERE e.id = '{0}' AND e.iteration = {1}"
