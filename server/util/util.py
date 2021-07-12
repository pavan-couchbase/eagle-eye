import logging
from datetime import datetime


def print_queue(q):
    str = "["
    num_tasks = q.qsize()
    i = 0
    for task in q.queue:
        if i == num_tasks - 1:
            str += task.__str__()
        else:
            str += task.__str__() + ","
        i += 1
    str += "]"
    return str

def id_print_queue(q, id):
    str = "["
    num_tasks = q.qsize()
    i = 0
    for task in q.queue:
        if task.job_id == id:
            if i == num_tasks - 1:
                str += task.__str__()
            else:
                str += task.__str__() + ","
        i += 1
    str += "]"
    return str


def get_parameters(config_dict, default=['loop_interval']):
    parameters = []
    for k, v in config_dict.items():
        if k not in default and v is not None:
            parameters.append(v)

    return parameters


def logger_init(job_id, logger_dir=".", logger_name=""):
    logger = logging.getLogger("{0}{1}".format(job_id, logger_name))
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    timestamp = str(datetime.now().strftime('%Y%m%dT_%H%M%S'))
    fh = logging.FileHandler("{0}/{1}{2}-{3}.log".format(logger_dir, job_id, logger_name, timestamp))
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger
