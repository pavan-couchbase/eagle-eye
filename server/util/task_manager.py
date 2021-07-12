import time
from .eagle_eye import EagleEye
from concurrent.futures import ThreadPoolExecutor
from server.constants.defaults import Default


class TaskManager:
    def __init__(self,
                 job_id,
                 cluster_name,
                 build,
                 master_node,
                 num_threads,
                 cb_instance,
                 email_list=None,
                 rest_username=Default.rest_username, rest_password=Default.rest_password,
                 ssh_username=Default.ssh_username, ssh_password=Default.ssh_password,
                 docker_host=None,
                 cb_host=Default.tm_cb_host,
                 print_all_logs=False,
                 alert_interval=Default.alert_interval):

        self.ee = EagleEye(job_id=job_id,
                           cluster_name=cluster_name,
                           build=build,
                           master_node=master_node,
                           num_tasks=num_threads,
                           cb_instance=cb_instance,
                           email_list=email_list,
                           rest_username=rest_username, rest_password=rest_password,
                           ssh_username=ssh_username, ssh_password=ssh_password,
                           docker_host=docker_host,
                           cb_host=cb_host,
                           print_all_logs=print_all_logs
                           )

        self.task_map = {}
        self.executor = ThreadPoolExecutor(num_threads+1)
        self.running_threads = 0
        self.running = True

        self.alert_interval = alert_interval
        self.next_time = time.time()
        self.task_num = 0

        self.alert_iter = 1

        # init the Alert thread, increment running threads
        self.executor.submit(self.alert)
        self.running_threads += 1

    def start_task(self, task):
        """
        This function allocates a thread for a task
        :param task: task object
        :return: Future object
        """
        if str(task) == "log_parser":
            parameters = task.get_parameters()
            future = self.executor.submit(self.ee.log_parser, self.ee.master_node, task.get_loop_interval(),
                                          self.task_num, parameters[0])
            self.task_num += 1
            self.running_threads += 1
            return future
        elif str(task) == "cpu_collection":
            parameters = task.get_parameters()
            future = self.executor.submit(self.ee.cpu_collection, task.get_loop_interval(), self.task_num, parameters[0])

            self.task_num += 1
            self.running_threads += 1
            return future
        elif str(task) == "mem_collection":
            parameters = task.get_parameters()
            future = self.executor.submit(self.ee.mem_collection, task.get_loop_interval(), self.task_num, parameters[0])

            self.task_num += 1
            self.running_threads += 1
            return future
        elif str(task) == "neg_stat_check":
            parameters = task.get_parameters()
            future = self.executor.submit(self.ee.negative_stat_checker, task.get_loop_interval(), self.task_num, parameters[0])

            self.task_num += 1
            self.running_threads += 1
            return future
        elif str(task) == "failed_query_check":
            parameters = task.get_parameters()
            future = self.executor.submit(self.ee.failed_query_check, task.get_loop_interval(), self.task_num, parameters[0])

            self.task_num += 1
            self.running_threads += 1
            return future
        else:
            raise TypeError("Unrecognized Data Collector")

    def stop(self):
        self.running = False
        self.ee.stop()

    def shutdown(self):
        '''
        Shutdown the thread pool
        '''
        self.stop()
        self.executor.shutdown(wait=True)

    def get_running_threads(self):
        return self.running_threads

    def alert(self):
        while self.running:
            time.sleep(self.alert_interval)
            if self.ee.has_changed:
                self.ee.on_alert(self.alert_iter)
                self.alert_iter += 1
