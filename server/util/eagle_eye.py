import json
import time
import re
import paramiko
import httplib2
import os
import zipfile
import base64
import traceback
import socket
import ast
import pytz
from couchbase.cluster import Cluster, PasswordAuthenticator
from datetime import datetime, timedelta
from collections import Mapping, Sequence, Set, deque
from util.util import logger_init


class EagleEye:
    def __init__(self, job_id,
                 cluster_name,
                 master_node, num_tasks,
                 cb_instance,
                 email_list,
                 rest_username, rest_password,
                 ssh_username, ssh_password,
                 docker_host,
                 cb_host,
                 print_all_logs,
                 run_one):
        self.job_id = job_id
        self.cluster_name = cluster_name
        self.master_node = master_node
        self.cb = cb_instance
        self.email_list = ",".join(email_list)
        self.rest_username, self.rest_password = rest_username, rest_password
        self.ssh_username, self.ssh_password = ssh_username, ssh_password
        self.docker_host = docker_host
        self.cb_host = cb_host
        self.print_all_logs = print_all_logs
        self.run_one = run_one

        # create a dir for the job
        # os.mkdir(self.job_id)
        os.makedirs("./server/job_logs/{0}".format(self.job_id))

        # better title for this
        self.logger = logger_init(job_id=self.job_id, logger_dir="./server/job_logs/{0}".format(self.job_id), logger_name="-task_manager")
        self.alert_logger = logger_init(job_id=self.job_id, logger_dir="./server/job_logs/{0}".format(self.job_id), logger_name="-alert_thread")

        self.wait_for_cluster_init(master_node, self.logger)

        try:
            self.cluster = self.get_cluster(cb_host)
            self.bucket = self.get_bucket("system_test_dashboard")
        except Exception:
            pass

        self.node_map = self.get_services_map(self.master_node, self.logger)
        self.running = True

        self.task_num_name_map = {}
        self.system_task_num_name_map = {}

        self.messages = {}
        self.prev_messages = {}
        self.has_changed = False
        self.should_cbcollect = False
        self.collected = False
        self.collect_mem = False
        self.collect_cpu = False

        self.tz = pytz.timezone('America/Los_Angeles')

    def stop(self):
        self.running = False

    def on_alert(self, alert_iter):
        try:
            doc_to_insert = {
                "id": self.job_id,
                "iteration": alert_iter,
                "master_node": self.master_node,
                "cluster_name": self.cluster_name,
                "build": self.build
            }

            email_text = ""

            # for each running task, create the message subject line and send the email with the correct message content
            for k, v in self.messages.items():
                # if there is no completed iterations yet, do not alert
                if v['data'] == "" or v['data'] == []:
                    continue

                # add the data to the document that will be inserted
                doc_to_insert[self.system_task_num_name_map[k]] = v

                # we can utilize less dicts if we create a log_parser class to keep track of all the iterations and messages
                if v['type'] == 'time_series':
                    if self.collect_cpu and self.system_task_num_name_map[k] == 'cpu_collection':
                        email_text += "\n" + "=============================" + self.task_num_name_map[k] + "============================= \n"
                        email_text += str(v['data'])
                        email_text += "\n"
                    if self.collect_mem and self.system_task_num_name_map[k] == 'mem_collection':
                        email_text += "\n" + "=============================" + self.task_num_name_map[k] + "============================= \n"
                        email_text += str(v['data'])
                        email_text += "\n"
                else:
                    email_text += "\n" + "=============================" + self.task_num_name_map[k] + "============================= \n"
                    email_text += v['data']
                    email_text += "\n"

                # we need to clear the stored results every alert interval
                if type(self.messages[k]['data']) is str:
                    self.messages[k] = {"type": "static", "data": ""}
                elif type(self.messages[k]['data']) is list:
                    self.messages[k] = {"type": "time_series", "data": []}

            self.node_map = self.get_services_map(self.master_node, self.logger)

            doc_to_insert['cluster_summary'] = {"type": "csummary", "data": []}

            email_text += "\n============================= Cluster Summary =============================\n"
            for node in self.node_map:
                doc_to_insert['cluster_summary']["data"].append({
                    "hostname": node['hostname'],
                    "status": node['status'],
                    "services": node['services']
                })

                email_text += f"{node['hostname']} ({node['status']}) : {node['services']}"
                email_text += "\n"


            # see if we need to collect logs
            start_time = time.time()
            self.collected = False
            log_content = ""

            self.alert_logger.info("Starting Log Collection at {0}".format(str(datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))))
            try:
                log_content = self.collect_logs(self.master_node, start_time, self.alert_logger)
            except Exception as e:
                self.alert_logger.error(str(e))
            self.alert_logger.info("Log Collection Complete")

            if log_content != "":
                email_text += "\n" + "=============================" + "Logs =============================\n"
                email_text += log_content

                # if there are logs to add, add to document and tell eagle-eye that we should wait to collect again
                doc_to_insert['logs'] = {"type": "logs", "data": []}
                for line in log_content.split("\n"):
                    if line != "" and line != "cbcollect logs: ":
                        doc_to_insert['logs']['data'].append(line.split(" : ")[1])
                self.should_cbcollect = False

            # send consolidated emails
            message_sub = f"Node: {self.master_node} Cluster: {self.cluster_name} : iteration number {alert_iter}"
            self.alert_logger.info("Sending Email: {0}".format(message_sub))
            try:
                self.send_email(message_sub=message_sub, message_content=email_text, email_recipients=self.email_list,
                                logger=self.alert_logger)
                self.alert_logger.info("Email Sent Success")
            except Exception as e:
                self.alert_logger.error("Email Error: " + str(e))

            self.alert_logger.info("Starting insert")
            # call write to CouchbaseDB
            try:
                self.update_cbinstance(doc_to_insert, self.alert_logger)
            except Exception as e:
                self.alert_logger.error(str(e))

            # after we have writen, assume nothing has changed until we check again
            self.has_changed = False
            self.alert_logger.info("Alert iteration {0} finished".format(alert_iter))
        except Exception as e:
            self.alert_logger.error(str(e))


    ######################### TASK FUNCTIONS #########################
    def log_parser(self, loop_interval, task_num, parameters):
        # parse parameters
        config = parameters[0]

        self.messages[task_num] = {"type": "static", "data": ""}
        task_dir, logger = self._task_init(task_num, "Log Parser", "log_parser")
        # config = json.load(config)

        paramiko.util.log_to_file('{0}/paramiko.log'.format(task_dir))

        timestamp = str(datetime.now(tz=self.tz).strftime('%Y-%m-%dT%H:%M:%S'))

        keyword_counts = {}
        keyword_counts["timestamp"] = timestamp

        state_file_dir = task_dir + "/states"
        os.makedirs(state_file_dir)
        state_file = state_file_dir + "/eagle-eye_" + self.master_node + ".state"
        last_scan_timestamp = ""
        iter_count = 1

        try:
            while self.running:
                if os.path.exists(state_file):
                    s = open(state_file, 'r').read()
                    prev_keyword_counts = ast.literal_eval(s)
                    last_scan_timestamp = datetime.strptime(prev_keyword_counts["last_scan_timestamp"],
                                                            "%Y-%m-%d %H:%M:%S.%f")
                else:
                    prev_keyword_counts = None
                dump_dir_name = task_dir + "/dump_collected_" + str(iter_count)
                if not os.path.isdir(dump_dir_name):
                    os.mkdir(dump_dir_name)
                message_content = ""

                if not self.node_map:
                    continue

                for component in config:
                    nodes = self.find_nodes_with_service(self.node_map,
                                                         component["services"])
                    if len(nodes) == 0:
                        logger.info("No Nodes with {0} service : {1} ... SKIPPING".format(component["services"],
                                                                                          str(nodes)))
                        continue

                    logger.info(
                        "Nodes with {0} service : {1}".format(component["services"],
                                                              str(nodes)))

                    for keyword in component['keywords']:
                        key = component["component"] + "_" + keyword
                        logger.info(
                            "--+--+--+--+-- Parsing logs for {0} component looking for {1} --+--+--+--+--".format(
                                component["component"], keyword))
                        total_occurences = 0

                        for node in nodes:
                            if component["ignore_keywords"]:

                                command = "zgrep -i \"{0}\" /opt/couchbase/var/lib/couchbase/logs/{1} | grep -vE \"{2}\"".format(
                                    keyword, component["logfiles"], "|".join(component["ignore_keywords"]))
                            else:
                                command = "zgrep -i \"{0}\" /opt/couchbase/var/lib/couchbase/logs/{1}".format(
                                    keyword, component["logfiles"])
                            occurences = 0
                            try:
                                occurences, output, std_err = self.execute_command(
                                    command, node, self.ssh_username, self.ssh_password)
                            except Exception as e:
                                logger.info("Found an exception {0}".format(e))
                                message_content = message_content + '\n\n' + node + " : " + str(component["component"])
                                message_content = message_content + '\n\n' + "Found an exception {0}".format(e) + "\n"
                            if occurences > 0:
                                logger.warn(
                                    "*** {0} occurences of {1} keyword found on {2} ***".format(
                                        occurences,
                                        keyword,
                                        node))
                                possible_message = '\n\n' + node + " : " + str(component["component"])
                                #message_content = message_content + '\n\n' + node + " : " + str(component["component"])
                                if self.print_all_logs is True or last_scan_timestamp == "":
                                    logger.debug('\n'.join(output))
                                    try:
                                        #message_content = message_content + '\n' + '\n'.join(output)
                                        possible_message += '\n' + '\n'.join(output)
                                    except UnicodeDecodeError as e:
                                        logger.warn(str(e))
                                        #message_content = message_content + '\n' + '\n'.join(output).decode("utf-8")
                                        possible_message += '\n' + '\n'.join(output).decode("utf-8")
                                else:
                                    #message_content = self.print_output(output, last_scan_timestamp, message_content, logger)
                                    possible_message += self.print_output(output, last_scan_timestamp, logger)

                                if possible_message != '\n\n' + node + " : " + str(component["component"]):
                                    message_content += possible_message
                                # for i in range(len(output)):
                                #    self.logger.info(output[i])
                            total_occurences += occurences

                        keyword_counts[key] = total_occurences
                        if prev_keyword_counts is not None and key in prev_keyword_counts.keys():
                            if total_occurences > int(prev_keyword_counts[key]):
                                logger.warn(
                                    "There have been more occurences of keyword {0} in the logs since the last iteration. Hence performing a cbcollect.".format(
                                        keyword))
                                self.should_cbcollect = True
                        else:
                            if total_occurences > 0:
                                self.should_cbcollect = True

                last_scan_timestamp = (datetime.now(tz=self.tz) - timedelta(minutes=10.0)).strftime("%Y-%m-%d %H:%M:%S.%f")
                logger.info("Last scan timestamp :" + str(last_scan_timestamp))
                keyword_counts["last_scan_timestamp"] = str(last_scan_timestamp)

                self.update_state_file(state_file=state_file, keyword_counts=keyword_counts)

                to_break, iter_count = self._task_sleep(loop_interval=loop_interval,
                                                        iter_count=iter_count,
                                                        message_content=message_content,
                                                        task_num=task_num,
                                                        logger=logger,
                                                        dc_name=self.task_num_name_map[task_num])
                if to_break is False or self.run_one:
                    logger.info("Stopping {0}".format(self.task_num_name_map[task_num]))
                    break
        except Exception as e:
            logger.error(str(e))
            self._task_error(logger, str(e), task_num)

    def cpu_collection(self, loop_interval, task_num, parameters):
        # parse parameters
        cpu_threshold = parameters[0]

        self.messages[task_num] = {"type": "time_series", "data": []}
        task_dir, logger = self._task_init(task_num, "CPU Collection", "cpu_collection")

        iter_count = 1
        try:
            while self.running:
                # cpu check and collect
                usages = []
                for node in self.node_map:
                    usages.append({"node": node['hostname'], "timestamp": str(datetime.now(tz=self.tz).strftime('%Y-%m-%dT%H:%M:%S')), "usage": node['cpuUsage']})
                    self.has_changed = True

                    if node["cpuUsage"] > cpu_threshold:
                        logger.warn(
                            "***** ALERT : CPU usage on {0} is very high : {1}%".format(
                                node["hostname"], node["cpuUsage"]))
                        self.should_cbcollect = True
                        self.collect_cpu = True
                        # if cbcollect_on_high_mem_cpu_usage:
                        #    should_cbcollect = True
                    self.check_on_disk_usage(node['hostname'], logger)

                to_break, iter_count = self._task_sleep(loop_interval=loop_interval, iter_count=iter_count, message_content=usages, task_num=task_num, logger=logger, dc_name=self.task_num_name_map[task_num])
                if to_break is False or self.run_one:
                    logger.info("Stopping {0}".format(self.task_num_name_map[task_num]))
                    break
        except Exception as e:
            logger.error(str(e))
            self._task_error(logger, str(e), task_num)

    def mem_collection(self, loop_interval, task_num, parameters):
        # parse parameters
        mem_threshold = parameters[0]

        self.messages[task_num] = {"type": "time_series", "data": []}
        task_dir, logger = self._task_init(task_num, "Memory Collection", "mem_collection")

        iter_count = 1
        try:
            while self.running:
                # cpu check and collect
                usages = []
                for node in self.node_map:
                    usages.append({"node": node['hostname'], "timestamp": str(datetime.now(tz=self.tz).strftime('%Y-%m-%dT%H:%M:%S')), "usage": node['memUsage']})
                    self.has_changed = True

                    if node["memUsage"] > mem_threshold:
                        logger.warn(
                            "***** ALERT : Memory usage on {0} is very high : {1}%".format(
                                node["hostname"], node["memUsage"]))
                        self.should_cbcollect = True
                        self.collect_mem = True
                    self.check_on_disk_usage(node['hostname'], logger)

                logger.info(
                    "====== {0} iteration number {1} complete. Sleeping for {2} seconds ======".format(
                        self.task_num_name_map[task_num], iter_count, loop_interval))

                to_break, iter_count = self._task_sleep(loop_interval=loop_interval, iter_count=iter_count,
                                                        message_content=usages, task_num=task_num, logger=logger,
                                                        dc_name=self.task_num_name_map[task_num])
                if to_break is False or self.run_one:
                    logger.info("Stopping {0}".format(self.task_num_name_map[task_num]))
                    break
        except Exception as e:
            logger.error(str(e))
            self._task_error(logger, str(e), task_num)

    def neg_stat_check(self, loop_interval, task_num, parameters):
        # parse parameters
        config = parameters[0]

        self.messages[task_num] = {"type": "static", "data": ""}
        task_dir, logger = self._task_init(task_num, "Negative Stat Checker", "neg_stat_check")

        iter_count = 1
        message_content = ""

        try:
            while self.running:
                if not self.node_map:
                    continue

                for component in config:
                    nodes = self.find_nodes_with_service(self.node_map, component['services'])

                    logger.info("Nodes with {0} service : {1}".format(component["services"],
                                                                      str(nodes)))

                    for node in nodes:
                        possible_message = '\n\n' + node + " : " + str(component["component"])
                        # message_content = message_content + '\n\n' + node + " : " + str(component["component"])
                        try:
                            fin_neg_stat, possible_message = self.check_stats_api(node, component, possible_message, logger)
                            if fin_neg_stat.__len__() != 0:
                                self.should_cbcollect = True
                        except Exception as e:
                            logger.info("Found an exception {0}".format(e))

                        if possible_message != '\n\n' + node + " : " + str(component["component"]):
                            message_content += possible_message

                to_break, iter_count = self._task_sleep(loop_interval=loop_interval,
                                                                         iter_count=iter_count,
                                                                         message_content=message_content,
                                                                         task_num=task_num,
                                                                         logger=logger,
                                                                         dc_name=self.task_num_name_map[task_num])
                if to_break is False or self.run_one:
                    logger.info("Stopping {0}".format(self.task_num_name_map[task_num]))
                    break
        except Exception as e:
            logger.error(str(e))
            self._task_error(logger, str(e), task_num)

    def failed_query_check(self, loop_interval, task_num, parameters):
        # parse parameters
        port = parameters[0]

        self.messages[task_num] = {"type": "static", "data": ""}
        task_dir, logger = self._task_init(task_num, "Failed Query Check", "failed_query_check")

        iter_count = 1
        message_content = ""

        try:
            while self.running:
                if not self.node_map:
                    continue

                n1ql_nodes = self.find_nodes_with_service(self.node_map, "n1ql")
                if n1ql_nodes:
                    # Check to make sure all nodes are healthy
                    self.logger.info("Checking if all query nodes are healthy")
                    message = self.check_nodes_healthy(nodes=n1ql_nodes, port=port, logger=logger)

                    if not message == '':
                        message_content = message_content + '\n\n' + str(n1ql_nodes) + " : query"
                        message_content = message_content + '\n\n' + message + "\n"
                    # Check system:completed_requests for errors
                    self.logger.info("Checking system:completed requests for errors")
                    message = self.check_completed_requests(nodes=n1ql_nodes,
                                                                            port=port,
                                                                            logger=logger)

                    if not message == '':
                        message_content = message_content + '\n\n' + str(n1ql_nodes) + " : query"
                        message_content = message_content + '\n\n' + message + "\n"
                    # Check active_requests to make sure that are no more than 1k active requests at a single time
                    self.logger.info("Checking system:active requests for too many requests")
                    message = self.check_active_requests(nodes=n1ql_nodes,
                                                                         port=port,
                                                                         logger=logger)

                    if not message == '':
                        message_content = message_content + '\n\n' + str(n1ql_nodes) + " : query"
                        message_content = message_content + '\n\n' + message + "\n"

                to_break, iter_count = self._task_sleep(loop_interval=loop_interval,
                                                                         iter_count=iter_count,
                                                                         message_content=message_content,
                                                                         task_num=task_num,
                                                                         logger=logger,
                                                                         dc_name=self.task_num_name_map[task_num])
                if to_break is False or self.run_one:
                    logger.info("Stopping {0}".format(self.task_num_name_map[task_num]))
                    break
        except Exception as e:
            logger.error(str(e))
            self._task_error(logger, str(e), task_num)

    def _task_init(self, task_num, name, sys_name):
        self.task_num_name_map[task_num] = name
        self.system_task_num_name_map[task_num] = sys_name

        # make dir for the task
        task_dir = "./server/job_logs/{0}/{1}".format(self.job_id, sys_name)
        os.makedirs(task_dir)

        logger = logger_init(job_id=self.job_id, logger_dir=task_dir, logger_name="-{0}".format(sys_name))

        return task_dir, logger

    def _task_sleep(self, loop_interval, iter_count, message_content, task_num, logger, dc_name):
        logger.info(
            "====== {0} iteration number {1} complete. Sleeping for {2} seconds ======".format(
                dc_name, iter_count, loop_interval))

        # if something has changed, change flag for task manager
        if message_content != "" or message_content != []:
            self.has_changed = True

        # do not add the message content you already emailed to the user
        if iter_count == 1 and self.messages[task_num]['type'] == 'static' and message_content != "":
            logger.info("Sending first iteration email")
            message_sub = f"Node: {self.master_node} : {self.task_num_name_map[task_num]} First Iteration Complete"
            try:
                self.send_email(message_sub=message_sub, message_content=message_content,
                            email_recipients=self.email_list,
                            logger=self.logger)
                logger.info("First iteration email success")
            except Exception as e:
                logger.error(str(e))
        # add the message content from the iteration
        if type(message_content) is str:
            self.messages[task_num]["data"] += message_content
        else:
            self.messages[task_num]["data"].extend(message_content)



        iter_count += 1
        self._sleep(loop_interval)

        if not self.running:
            logger.info("Stopping {0}".format(dc_name))
            return False, iter_count

        return True, iter_count

    def _sleep(self, loop_interval):
        for i in range(0, loop_interval):
            if not self.running:
                break
            time.sleep(1)

    def _task_error(self, logger, e, task_num):
        traceback_msg = traceback.print_exc()
        logger.error(traceback_msg)

        message_sub = "Error Raised in {0}: {1}".format(self.task_num_name_map[task_num], str(e))
        self.send_email(message_sub=message_sub, message_content=traceback_msg, email_recipients=self.email_list, logger=logger)

    ######################### HELPER FUNCTIONS #########################
    def collect_logs(self, master_node, start_time, logger):
        message_content = ""
        while self.should_cbcollect and not self.collected and time.time() < (start_time + (60 * 60)):
            logger.info("====== RUNNING CBCOLLECT_INFO ======")
            # command = "/opt/couchbase/bin/cbcollect_info outputfile.zip --multi-node-diag --upload-host=s3.amazonaws.com/bugdb/jira --customer=systestmon-{0}".format(
            #    timestamp)
            epoch_time = int(time.time())
            command = "/opt/couchbase/bin/couchbase-cli collect-logs-start -c {0} -u {1} -p {2} --all-nodes --upload --upload-host cb-jira.s3.us-east-2.amazonaws.com/logs --customer systestmon-{3}".format(
                master_node, self.rest_username, self.rest_password, epoch_time)
            _, cbcollect_output, std_err = self.execute_command(
                command, master_node, self.ssh_username, self.ssh_password)
            if std_err:
                logger.error(
                    "Error seen while running cbcollect_info ")
                logger.info(std_err)
            else:
                for i in range(len(cbcollect_output)):
                    logger.info(cbcollect_output[i])

            while True:
                command = "/opt/couchbase/bin/couchbase-cli collect-logs-status -c {0} -u {1} -p {2}".format(
                    master_node, self.rest_username, self.rest_password)
                _, cbcollect_output, std_err = self.execute_command(
                    command, master_node, self.ssh_username, self.ssh_password)
                if std_err:
                    self.logger.error(
                        "Error seen while running cbcollect_info ")
                    self.logger.info(std_err)
                    break
                else:
                    # for i in range(len(cbcollect_output)):
                    #    print cbcollect_output[i]
                    if cbcollect_output[0] == "Status: completed":
                        cbcollect_upload_paths = []
                        for line in cbcollect_output:
                            if "url :" in line:
                                cbcollect_upload_paths.append(line)
                        logger.info("cbcollect upload paths : \n")
                        logger.info('\n'.join(cbcollect_upload_paths))
                        message_content = message_content + '\n\ncbcollect logs: \n\n' + '\n'.join(
                            cbcollect_upload_paths)
                        # for i in range(len(cbcollect_upload_paths)):
                        #    print cbcollect_upload_paths[i]
                        self.collected = True
                        break
                    elif cbcollect_output[0] == "Status: running":
                        time.sleep(60)
                    elif cbcollect_output[0] == "Status: cancelled":
                        self.collected = False
                        break
                    else:
                        logger.error("Issue with cbcollect")
                        break

        return message_content

    def get_ssh_client(self, host, username, password):
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=username, password=password, timeout=120, banner_timeout=120)
        return client

    def check_on_disk_usage(self, node, logger):
        logger.info("=======" + node + "===========")
        command = "df -kh /data"
        _, df_output, std_err = self.execute_command(
            command, node, self.ssh_username, self.ssh_password)
        if std_err:
            logger.error(
                "Error seen while running df -kh ")
            logger.info(std_err)
        else:
            for i in range(len(df_output)):
                logger.info(df_output[i])

    '''
    Function not user currently (do we still want?)
    def check_on_ntp_status(self, node):
        self.logger.info("=======" + node + "===========")
        command = "timedatectl status | grep NTP"
        _, df_output, std_err = self.execute_command(
            command, node, ssh_username, ssh_password)
        if std_err:
            self.logger.error(
                "Error seen while running df -kh ")
            self.logger.info(std_err)
        else:
            for i in range(len(df_output)):
                self.logger.info(df_output[i])
    '''

    def get_cluster(self, cb_host):
        try:
            cluster = Cluster('couchbase://{}'.format(cb_host))
            authenticator = PasswordAuthenticator(self.rest_username, self.rest_password)
            cluster.authenticate(authenticator)
            return cluster
        except Exception:
            from couchbase.cluster import ClusterOptions
            cluster = Cluster('couchbase://{}'.format(cb_host),
                              ClusterOptions(PasswordAuthenticator(self.rest_username, self.rest_password)))
            return cluster

    def get_bucket(self, name):
        try:
            return self.cluster.open_bucket(name)
        except Exception:
            return self.cluster.bucket(name)

    def append_list(self, key, value):
        try:
            self.bucket.list_append(key, value, create=True)
        except Exception:
            self.bucket.default_collection().list_append(key, value, create=True)

    def store_results(self, message_sub, message_content):
        build_id = os.getenv("BUILD_NUMBER")
        if build_id is not None:
            key = "log_parser_results_" + build_id
            self.append_list(key, message_sub + "\n" + message_content)

    def send_email(self, message_sub, message_content, email_recipients, logger):
        SENDMAIL = "/usr/sbin/sendmail"  # sendmail location

        FROM = "eagle-eye@couchbase.com"
        TO = email_recipients

        SUBJECT = message_sub

        TEXT = message_content

        # Prepare actual message
        message = ('From: %s\n'
                   'To: %s\n'
                   'Subject: %s\n'
                   '\n'
                   '%s\n') % (FROM, TO, SUBJECT, TEXT)

        # Send the mail
        import os

        p = os.popen("%s -t -i" % SENDMAIL, "w")
        try:
            p.write(message)
        except UnicodeEncodeError as e:
            logger.warn(str(e))
            p.write(message.encode("utf-8"))
        status = p.close()
        if status:
            print("Sendmail exit status", status)

    def update_cbinstance(self, doc, logger):
        try:
            id = doc["id"] + "_" + str(doc["iteration"])
        except Exception as e:
            print(e)

        logger.info("Inserting Document")
        if self.cb.insert_doc(id, doc):
            logger.info("Insert Success")
        else:
            logger.error("Insert Fail")

    def update_state_file(self, state_file, keyword_counts):
        target = open(state_file, 'w')
        target.write(str(keyword_counts))

    def collect_dumps(self, node, component, message_content, dump_dir_name, logger):
        goroutine_dump_name, cpupprof_dump_name, heappprof_dump_name = self.get_dumps(node, component["port"],
                                                                                      dump_dir_name, logger)
        message_content = message_content + '\n' + "Dump Location : " + '\n' + goroutine_dump_name + '\n' + cpupprof_dump_name + '\n' + heappprof_dump_name
        return message_content

    def check_stats_api(self, node, component, message_content, logger):

        fin_neg_stat = []
        for stat in component["stats_api_list"]:
            stat_json = self.get_stats(stat, node, component["port"], logger)
            neg_stat = self.check_for_negative_stat(stat_json)
            if neg_stat.__len__() != 0:
                fin_neg_stat.append(neg_stat)
            else:
                neg_stat = None
            logger.info(str(stat) + " : " + str(neg_stat))
            if neg_stat is not None:
                message_content = message_content + '\n' + str(stat) + " : " + str(neg_stat)

        return fin_neg_stat, message_content

    def check_for_negative_stat(self, stat_json):
        queue = deque([stat_json])
        neg_stats = []
        while queue:
            node = queue.popleft()
            nodevalue = node
            if type(node) is tuple:
                nodekey = node[0]
                nodevalue = node[1]

            if isinstance(nodevalue, Mapping):
                for k, v in nodevalue.items():
                    queue.extend([(k, v)])
            elif isinstance(nodevalue, (Sequence, Set)) and not isinstance(nodevalue, str):
                queue.extend(nodevalue)
            else:
                if isinstance(nodevalue, int) and nodevalue < 0 and "mutation_queue_size" not in nodekey:
                    neg_stats.append(node)

        return neg_stats

    def get_dumps(self, node, port, dump_dir_name, logger):
        goroutine_dump_name = "{0}/{1}/goroutine_{2}".format(os.getcwd(), dump_dir_name, node)
        cpupprof_dump_name = "{0}/{1}/cpupprof_{2}".format(os.getcwd(), dump_dir_name, node)
        heappprof_dump_name = "{0}/{1}/heappprof_{2}".format(os.getcwd(), dump_dir_name, node)

        heap_dump_cmd = "curl http://{0}:{1}/debug/pprof/heap?debug=1 -u Administrator:password > {2}".format(node,
                                                                                                              port,
                                                                                                              heappprof_dump_name)
        cpu_dump_cmd = "curl http://{0}:{1}/debug/pprof/profile?debug=1 -u Administrator:password > {2}".format(node,
                                                                                                                port,
                                                                                                                cpupprof_dump_name)
        goroutine_dump_cmd = "curl http://{0}:{1}/debug/pprof/goroutine?debug=1 -u Administrator:password > {2}".format(
            node, port, goroutine_dump_name)

        logger.info(heap_dump_cmd)
        os.system(heap_dump_cmd)

        logger.info(cpu_dump_cmd)
        os.system(cpu_dump_cmd)

        logger.info(goroutine_dump_cmd)
        os.system(goroutine_dump_cmd)

        return goroutine_dump_name, cpupprof_dump_name, heappprof_dump_name

    def get_stats(self, stat, node, port, logger):
        api = "http://{0}:{1}/{2}".format(node, port, stat)
        json_parsed = {}

        status, content, header = self._http_request(api, logger)
        if status:
            json_parsed = json.loads(content)
            # self.logger.info(json_parsed)
        return json_parsed

    def convert_output_to_json(self, output):
        list_to_string = ''
        list_to_string = list_to_string.join(output)
        json_output = json.loads(list_to_string)
        return json_output

    def check_nodes_healthy(self, nodes, port, logger):
        message_content = ''
        for node in nodes:
            command = "curl http://{0}:{1}/query/service -u {2}:{3} -d 'statement=select 1'".format(node,
                                                                                                    port,
                                                                                                    self.rest_username,
                                                                                                    self.rest_password)
            logger.info("Running curl: {0}".format(command))
            try:
                occurences, output, std_err = self.execute_command(
                    command, node, self.ssh_username, self.ssh_password)
                logger.info("Node:{0} Results:{1}".format(node, str(output)))
                if "Empty reply from server" in str(output) or "failed to connect" in str(output) or "timeout" in str(
                        output):
                    logger.error(
                        "The n1ql service appears to be unhealthy! Select 1 from node {0} failed! {1}".format(node,
                                                                                                              output))
                    self.should_cbcollect = True
            except Exception as e:
                logger.info("Found an exception {0}".format(e))
                message_content = message_content + '\n\n' + node + " : query"
                message_content = message_content + '\n\n' + "Found an exception {0}".format(e) + "\n"

        return message_content

    def check_completed_requests(self, nodes, port, logger):
        message_content = ''
        collection_timestamp = time.time()
        collection_timestamp = datetime.fromtimestamp(collection_timestamp).strftime('%Y-%m-%dT%H:%M:%S')
        path = os.getcwd()
        file = "query_completed_requests_errors_{0}.txt".format(collection_timestamp)
        # Group the errors by the number of occurences of each distinct error message
        command = "curl http://{0}:{1}/query/service -u {2}:{3} -d 'statement=select count(errors[0].message) as errorCount, errors[0].message from system:completed_requests where errorCount > 0 group by errors[0].message'".format(
            nodes[0], port, self.rest_username, self.rest_password)
        logger.info("Running curl: {0}".format(command))
        try:
            occurences, output, std_err = self.execute_command(
                command, nodes[0], self.ssh_username, self.ssh_password)
            # Convert the output to a json dict that we can parse
            results = self.convert_output_to_json(output)
            if results['metrics']['resultCount'] > 0:
                for result in results['results']:
                    if 'message' in result:
                        # Filter out known errors
                        # Some errors can be filtered out based on errors[0].message, add those error messages here
                        if "Timeout" in result['message'] and "exceeded" in result["message"]:
                            try:
                                logger.info(
                                    "Error message {0} is a known error, we will skip it and remove it from completed_requests".format(
                                        result['message']))
                                command = "curl http://{0}:{1}/query/service -u {2}:{3} -d 'statement=delete from system:completed_requests where errors[0].message = \"{4}\"'".format(
                                    nodes[0], port, self.rest_username, self.rest_password, result['message'])
                                logger.info("Running curl: {0}".format(command))
                                occurences, output, std_err = self.execute_command(
                                    command, nodes[0], self.ssh_username, self.ssh_password)
                                results = self.convert_output_to_json(output)
                            except Exception as e:
                                if "errors" in str(e):
                                    continue
                                else:
                                    self.logger.info("There was an exception {0}".format(str(e)))
                        # Some errors need to be checked out further in order to see if they need to be filtered
                        elif "Commit Transaction statement error" in result['message']:
                            try:
                                command = "curl http://{0}:{1}/query/service -u {2}:{3} -d 'statement=select * from system:completed_requests where errors[0].message = \"{4}\"'".format(
                                    nodes[0], port, self.rest_username, self.rest_password, result['message'])
                                logger.info("Running curl: {0}".format(command))
                                occurences, output, std_err = self.execute_command(
                                    command, nodes[0], self.ssh_username, self.ssh_password)
                                # Convert the output to a json dict that we can parse
                                results = self.convert_output_to_json(output)
                                # Check the causes field for known errors, if we encounter one, remove them from completed_requests
                                for result in results['results']:
                                    if "cause" in result['errors'][0]:
                                        if "deadline expired before WWC" in result['errors'][0]['cause']['cause'][
                                            'cause']:
                                            logger.info(
                                                "Error message {0} is a known error, we will skip it and remove it from completed_requests".format(
                                                    result['errors'][0]['cause']['cause']['cause']))
                                            command = "curl http://{0}:{1}/query/service -u {2}:{3} -d 'statement=delete from system:completed_requests where errors[0].cause.cause.cause = \"{4}\"'".format(
                                                nodes[0], port, self.rest_username, self.rest_password,
                                                result['errors'][0]['cause']['cause']['cause'])
                                            logger.info("Running curl: {0}".format(command))
                                            occurences, output, std_err = self.execute_command(
                                                command, nodes[0], self.ssh_username, self.ssh_password)
                            except Exception as e:
                                if "errors" in str(e):
                                    continue
                                else:
                                    logger.info("There was an exception {0}".format(str(e)))
                            # add elifs here to mimic the above to filter more known causes of error messages
                command = "curl http://{0}:{1}/query/service -u {2}:{3} -d 'statement=select count(errors[0].message) as errorCount, errors[0].message from system:completed_requests where errorCount > 0 group by errors[0].message'".format(
                    nodes[0], port, self.rest_username, self.rest_password)
                occurences, output, std_err = self.execute_command(
                    command, nodes[0], self.ssh_username, self.ssh_password)
                # Convert the output to a json dict that we can parse
                results = self.convert_output_to_json(output)
                if results['metrics']['resultCount'] > 0:
                    logger.info("Errors found: {0}".format(results['results']))
                    for result in results['results']:
                        if 'message' in result:
                            logger.info(
                                "Number of occurences of message '{0}':{1}".format(result['message'],
                                                                                   result['errorCount']))
                            # Look for an example of each error message, and print it out timestamped
                            command = "curl http://{0}:{1}/query/service -u {2}:{3} -d 'statement=select * from system:completed_requests where errors[0].message = \"{4}\" limit 1'".format(
                                nodes[0], port, self.rest_username, self.rest_password, result['message'])
                            logger.info("Running curl: {0}".format(command))
                            occurences, output, std_err = self.execute_command(
                                command, nodes[0], self.ssh_username, self.ssh_password)
                            # Convert the output to a json dict that we can parse
                            results = self.convert_output_to_json(output)
                            logger.info(
                                "Sample result for error message '{0}' at time {1}: {2}".format(result['message'],
                                                                                                results['results'][0][
                                                                                                    'completed_requests'][
                                                                                                    'requestTime'],
                                                                                                results['results']))
                            # Update message_content to show errors were found
                            message_content = message_content + '\n\n' + nodes[0] + " : query"
                            message_content = message_content + '\n\n' + "Sample result for error message '{0}' at time {1}: {2}".format(
                                result['message'],
                                results['results'][0][
                                    'completed_requests'][
                                    'requestTime'],
                                results['results']) + "\n"
                    # Get the entire completed_requests errors and dump them to a file
                    command = "curl http://{0}:{1}/query/service -u {2}:{3} -d 'statement=select * from system:completed_requests where errorCount > 0 order by requestTime desc'".format(
                        nodes[0], port, self.rest_username, self.rest_password)
                    logger.info("Running curl: {0}".format(command))
                    try:
                        occurences, output, std_err = self.execute_command(
                            command, nodes[0], self.ssh_username, self.ssh_password)
                        # Convert the output to a json dict that we can parse
                        results = self.convert_output_to_json(output)
                        # If there are results store the results in a file
                        if results['metrics']['resultCount'] > 0:
                            logger.info("We found errors in completed requests, storing errors to a file")
                            with open(os.path.join(path, file), 'w') as fp:
                                json.dump(results, fp, indent=4)
                                fp.close()
                            zipname = path + "/query_completed_requests_errors_{0}.zip".format(
                                collection_timestamp)
                            zipfile.ZipFile(zipname, mode='w').write(file)
                            os.remove(file)
                            file = file.replace(".txt", ".zip")
                            logger.info(
                                "Errors from completed_requests stored at {0}/{1}".format(path, file))
                            logger.info(
                                "After storing competed_requests_errors we will delete them from the server")

                            command = "curl http://{0}:{1}/query/service -u {2}:{3} -d 'statement=delete from system:completed_requests where errorCount > 0'".format(
                                nodes[0], port, self.rest_username, self.rest_password)
                            logger.info("Running curl: {0}".format(command))
                            occurences, output, std_err = self.execute_command(
                                command, nodes[0], self.ssh_username, self.ssh_password)
                            self.should_cbcollect = True
                    except Exception as e:
                        logger.info("Found an exception {0}".format(e))
                        message_content = message_content + '\n\n' + nodes[0] + " : query"
                        message_content = message_content + '\n\n' + "Found an exception {0}".format(e) + "\n"

        except Exception as e:
            logger.info("Found an exception {0}".format(e))
            message_content = message_content + '\n\n' + nodes[0] + " : query"
            message_content = message_content + '\n\n' + "Found an exception {0}".format(e) + "\n"

        return message_content

    def check_active_requests(self, nodes, port, logger):
        message_content = ''
        collection_timestamp = time.time()
        collection_timestamp = datetime.fromtimestamp(collection_timestamp).strftime('%Y-%m-%dT%H:%M:%S')
        path = os.getcwd()
        file = "query_active_requests_{0}.txt".format(collection_timestamp)
        command = "curl http://{0}:{1}/query/service -u {2}:{3} -d 'statement=select * from system:active_requests'".format(
            nodes[0], port, self.rest_username, self.rest_password)
        logger.info("Running curl: {0}".format(command))
        try:
            occurences, output, std_err = self.execute_command(
                command, nodes[0], self.ssh_username, self.ssh_password)
            # Convert the output to a json dict that we can parse
            results = self.convert_output_to_json(output)
            # If there are results store the results in a file
            if results['metrics']['resultCount'] > 1000:
                logger.info(
                    "There are more than 1000 queries running at time {0}, this should not be the case. Storing active_requests for further review".format(
                        collection_timestamp))
                message_content = message_content + '\n\n' + nodes[0] + " : query"
                message_content = message_content + '\n\n' + "There are more than 1000 queries running at time {0}, this should not be the case. Storing active_requests for further review".format(
                    collection_timestamp) + "\n"
                with open(os.path.join(path, file), 'w') as fp:
                    json.dump(results, fp, indent=4)
                    fp.close()
                zipname = path + "/query_active_requests_{0}.zip".format(collection_timestamp)
                zipfile.ZipFile(zipname, mode='w').write(file)
                os.remove(file)
                file = file.replace(".txt", ".zip")
                logger.info("Active requests stored at {0}/{1}".format(path, file))
                self.should_cbcollect = True
        except Exception as e:
            logger.info("Found an exception {0}".format(e))
            message_content = message_content + '\n\n' + nodes[0] + " : query"
            message_content = message_content + '\n\n' + "Found an exception {0}".format(e) + "\n"

        return message_content

    def _create_headers(self):
        # authorization = base64.encodebytes(f"{self.rest_username}:{self.rest_password}".encode('utf-8',errors='strict'))
        authorization = base64.encodebytes(
            bytes(f"{self.rest_username}:{self.rest_password}", encoding='ascii')).decode('ascii')
        return {'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'Basic {authorization}',
                'Accept': '*/*'}

    def _get_auth(self, headers):
        key = 'Authorization'
        if key in headers:
            val = headers[key]
            if val.startswith("Basic "):
                return f"auth: {base64.decodebytes(val[6:])}"
        return ""

    def _http_request(self, api, logger, method='GET', params='', headers=None, timeout=120):
        if not headers:
            headers = self._create_headers()
        end_time = time.time() + timeout
        logger.info("Executing {0} request for following endpoints {1}".format(method, api))
        count = 1
        while True:
            try:
                response, content = httplib2.Http(timeout=timeout).request(api, method,
                                                                           params, headers)
                if response['status'] in ['200', '201', '202']:
                    return True, content, response
                else:
                    try:
                        json_parsed = json.loads(content)
                    except ValueError as e:
                        json_parsed = {}
                        json_parsed["error"] = "status: {0}, content: {1}" \
                            .format(response['status'], content)
                    reason = "unknown"
                    if "error" in json_parsed:
                        reason = json_parsed["error"]
                    message = '{0} {1} body: {2} headers: {3} error: {4} reason: {5} {6} {7}'. \
                        format(method, api, params, headers, response['status'], reason,
                               content.rstrip('\n'), self._get_auth(headers))
                    logger.error(message)
                    logger.debug(''.join(traceback.format_stack()))
                    return False, content, response
            except socket.error as e:
                if count < 4:
                    logger.error("socket error while connecting to {0} error {1} ".format(api, e))
                if time.time() > end_time:
                    logger.error("Tried ta connect {0} times".format(count))
                    raise Exception()
            except httplib2.ServerNotFoundError as e:
                if count < 4:
                    logger.error("ServerNotFoundError error while connecting to {0} error {1} " \
                                 .format(api, e))
                if time.time() > end_time:
                    logger.error("Tried ta connect {0} times".format(count))
                    raise Exception()
            time.sleep(3)
            count += 1

    def print_output(self, output, last_scan_timestamp, logger,
                     ignore_list=["Port exited with status 0", "Fatal:false",
                                  "HyracksDataException: HYR0115: Local network error",
                                  "No such file or directory"]):
        message_content = ""
        for line in output:
            match = re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', line)
            if match:
                timestamp_in_log = datetime.strptime(match.group(), '%Y-%m-%dT%H:%M:%S')
                timestamp_in_log = self.tz.localize(timestamp_in_log)
                timestamp_in_log = datetime.strptime(timestamp_in_log.strftime("%Y-%m-%d %H:%M:%S.%f"), "%Y-%m-%d %H:%M:%S.%f")
                if timestamp_in_log >= last_scan_timestamp and self.check_op_in_ignorelist(line):
                    logger.debug(line)
                    message_content = message_content + '\n' + line
            else:
                logger.debug(line)
                message_content = message_content + '\n' + line
                if line.strip() not in ignore_list:
                    ignore_list.append(line.strip())

        return message_content

    def check_op_in_ignorelist(self, line, ignore_list=["Port exited with status 0", "Fatal:false",
                                                        "HyracksDataException: HYR0115: Local network error",
                                                        "No such file or directory"]):
        for ignore_text in ignore_list:
            if ignore_text in line:
                return False
        return True

    def get_services_map(self, master, logger):
        cluster_url = "http://" + master + ":8091/pools/default"
        node_map = []
        retry_count = 5
        while retry_count:
            try:
                # Get map of nodes in the cluster
                status, content, header = self._http_request(cluster_url, logger)

                if status:
                    response = json.loads(str(content, encoding='utf-8'))

                    # extract the build
                    for node in response['nodes']:
                        if node['hostname'].split(":")[0] == master:
                            self.build = node['version']
                            break

                    for node in response["nodes"]:
                        clusternode = {}
                        clusternode["hostname"] = node["hostname"].replace(":8091", "")
                        clusternode["services"] = node["services"]
                        mem_used = int(node["memoryTotal"]) - int(node["memoryFree"])
                        if node["memoryTotal"]:
                            clusternode["memUsage"] = round(
                                float(float(mem_used) / float(node["memoryTotal"]) * 100), 2)
                        else:
                            clusternode["memUsage"] = 0
                        clusternode["cpuUsage"] = round(
                            node["systemStats"]["cpu_utilization_rate"], 2)
                        clusternode["status"] = node["status"]
                        node_map.append(clusternode)

                    break
            except Exception as e:
                logger.info("Found an exception {0}".format(e))
                logger.info(status)
                logger.info(content)
                node_map = None

            time.sleep(300)
            retry_count -= 1
        return node_map

    def find_nodes_with_service(self, node_map, service):
        nodelist = []
        for node in node_map:
            if service == "all":
                nodelist.append(node["hostname"])
            else:
                if service in node["services"]:
                    nodelist.append(node["hostname"])
        return nodelist

    def wait_for_cluster_init(self, master_node, logger):
        start_time = time.time()
        cluster_url = "http://" + master_node + ":8091/pools/default"
        while time.time() < start_time + (30 * 60):
            logger.info("Waiting for cluster {} init".format(master_node))
            try:
                status, content, _ = self._http_request(cluster_url, logger)
                if status:
                    response = json.loads(content)
                    for node in response['nodes']:
                        if node['hostname'].split(':')[0] == master_node and node['clusterMembership'] == 'active':
                            return
            except Exception as e:
                print(str(e))
                pass
            time.sleep(10)

        # if longer than 30 minutes
        self.running = False

    def execute_command(self, command, hostname, ssh_username, ssh_password):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, username=ssh_username, password=ssh_password,
                    timeout=120, banner_timeout=120)

        channel = ssh.get_transport().open_session()
        channel.get_pty()
        channel.settimeout(900)
        stdin = channel.makefile('wb')
        stdout = channel.makefile('rb')
        stderro = channel.makefile_stderr('rb')

        channel.exec_command(command)
        data = channel.recv(1024)
        temp = ""
        while data:
            temp += data.decode("utf-8")
            data = channel.recv(1024)
        channel.close()
        stdin.close()

        output = []
        error = []
        for line in stdout.read().splitlines():
            if "No such file or directory" not in line:
                output.append(line)
        for line in stderro.read().splitlines():
            error.append(line)
        if temp:
            line = temp.splitlines()
            output.extend(line)
        stdout.close()
        stderro.close()

        # self.logger.info("Executing on {0}: {1}".format(hostname, command))
        # ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)

        # output = ""
        # while not ssh_stdout.channel.exit_status_ready():
        #    # Only print data if there is data to read in the channel
        #    if ssh_stdout.channel.recv_ready():
        #        rl, wl, xl = select.select([ssh_stdout.channel], [], [], 0.0)
        #        if len(rl) > 0:
        #            tmp = ssh_stdout.channel.recv(1024)
        #            output += tmp.decode()

        # output = output.split("\n")

        ssh.close()

        # return len(output) - 1, output, ssh_stderr
        return len(output), output, error
