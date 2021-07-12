class Queries:
    # queries
    # get data by id
    id_get_data = "SELECT VALUE e FROM `eagle-eye` e WHERE e.id = '{0}'"

    # get data by id and data collector name
    id_dc_get_data = "SELECT VALUE e FROM `eagle-eye` e WHERE e.id = '{0}' AND {1} IS NOT MISSING"

    # get data by id and iteration num
    id_iter_get_data = "SELECT VALUE e FROM `eagle-eye` e WHERE e.id = '{0}' AND e.iter = {1}"

    # get data by id and iteration num and data collector name
    id_iter_dc_get_data = "SELECT VALUE e FROM `eagle-eye` e WHERE e.id = '{0}' AND e.iter = {1} AND {2} IS NOT MISSING"
