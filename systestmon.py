import copy
import json
import logging
import re
import sys
import time
from datetime import datetime, timedelta

import paramiko
import requests


class SysTestMon():
    # Input map of keywords to be mined for in the logs
    configuration = [
        {
            "component": "memcached",
            "logfiles": "babysitter.log*",
            "services": "all",
            "keywords": ["exception occurred in runloop"]
        },
        {
            "component": "memcached",
            "logfiles": "memcached.log.*",
            "services": "all",
            "keywords": ["CRITICAL"]
        },
        {
            "component": "index",
            "logfiles": "indexer.log*",
            "services": "index",
            "keywords": ["panic", "fatal", "Error parsing XATTR"]
        },
        {
            "component": "analytics",
            "logfiles": "analytics_error*",
            "services": "cbas",
            "keywords": ["fata", "Analytics Service is temporarily unavailable", "Failed during startup task", "HYR0",
                         "ASX", "IllegalStateException"]
        },
        {
            "component": "eventing",
            "logfiles": "eventing.log*",
            "services": "eventing",
            "keywords": ["panic", "fatal"]
        },
        {
            "component": "fts",
            "logfiles": "fts.log*",
            "services": "fts",
            "keywords": ["panic", "fatal"]
        },
        {
            "component": "xdcr",
            "logfiles": "*xdcr*.log*",
            "services": "kv",
            "keywords": ["panic", "fatal"]
        },
        {
            "component": "projector",
            "logfiles": "projector.log*",
            "services": "kv",
            "keywords": ["panic", "Error parsing XATTR", "fata"]
        },
        {
            "component": "rebalance",
            "logfiles": "error.log*",
            "services": "all",
            "keywords": ["rebalance exited"]
        },
        {
            "component": "crash",
            "logfiles": "info.log*",
            "services": "all",
            "keywords": ["exited with status"]
        },
        {
            "component": "query",
            "logfiles": "query.log*",
            "services": "n1ql",
            "keywords": ["panic", "fatal"]
        }
    ]
    # Frequency of scanning the logs in seconds
    scan_interval = 3600
    # Level of memory usage after which alert should be raised
    mem_threshold = 90
    # Level of CPU usage after which alert should be raised
    cpu_threshold = 90

    # 1. Get service map for cluster
    # 2. For each component, get nodes for the requested service
    # 3. SSH to those nodes, grep for specified keywords in specified files
    # 4. Reporting

    ignore_list = ["Port exited with status 0", "Fatal:false", "HyracksDataException: HYR0115: Local network error"]

    def run(self):
        # Logging configuration
        self.logger = logging.getLogger("systestmon")
        self.logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        timestamp = str(datetime.now().strftime('%Y%m%dT_%H%M%S'))
        fh = logging.FileHandler("./systestmon-{0}.log".format(timestamp))
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

        master_node = sys.argv[1]
        rest_username = sys.argv[2]
        rest_password = sys.argv[3]
        ssh_username = sys.argv[4]
        ssh_password = sys.argv[5]
        cbcollect_on_high_mem_cpu_usage = sys.argv[6]
        print_all_logs = sys.argv[7]

        node_map = self.get_services_map(master_node, rest_username,
                                         rest_password)
        timestamp = str(datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))

        prev_keyword_counts = None
        keyword_counts = {}
        keyword_counts["timestamp"] = timestamp
        last_scan_timestamp = ""

        while True:
            should_cbcollect = False

            for component in self.configuration:
                nodes = self.find_nodes_with_service(node_map,
                                                     component["services"])
                self.logger.info(
                    "Nodes with {0} service : {1}".format(component["services"],
                                                          str(nodes)))

                for keyword in component["keywords"]:
                    key = component["component"] + "_" + keyword
                    self.logger.info(
                        "--+--+--+--+-- Parsing logs for {0} component looking for {1} --+--+--+--+--".format(
                            component["component"], keyword))
                    total_occurences = 0

                    for node in nodes:
                        command = "zgrep -i \"{0}\" /opt/couchbase/var/lib/couchbase/logs/{1}".format(
                            keyword, component["logfiles"])
                        occurences, output, std_err = self.execute_command(
                            command, node, ssh_username, ssh_password)
                        if occurences > 0:
                            self.logger.warn(
                                "*** {0} occurences of {1} keyword found on {2} ***".format(
                                    occurences,
                                    keyword,
                                    node))
                            if print_all_logs.lower() == "true" or last_scan_timestamp == "":
                                self.logger.info('\n'.join(output))
                            else:
                                self.print_output(output, last_scan_timestamp)
                            # for i in range(len(output)):
                            #    self.logger.info(output[i])
                        total_occurences += occurences

                    keyword_counts[key] = total_occurences
                    if prev_keyword_counts is not None and key in prev_keyword_counts.keys():
                        if total_occurences > int(prev_keyword_counts[key]):
                            self.logger.warn(
                                "There have been more occurences of keyword {0} in the logs since the last iteration. Hence performing a cbcollect.".format(
                                    keyword))
                            should_cbcollect = True
                    else:
                        if total_occurences > 0:
                            should_cbcollect = True

            # Check for health of all nodes
            for node in node_map:
                if node["memUsage"] > self.mem_threshold:
                    self.logger.warn(
                        "***** ALERT : Memory usage on {0} is very high : {1}%".format(
                            node["hostname"], node["memUsage"]))
                    if cbcollect_on_high_mem_cpu_usage:
                        should_cbcollect = True

                if node["cpuUsage"] > self.cpu_threshold:
                    self.logger.warn(
                        "***** ALERT : CPU usage on {0} is very high : {1}%".format(
                            node["hostname"], node["cpuUsage"]))
                    if cbcollect_on_high_mem_cpu_usage:
                        should_cbcollect = True

                if node["status"] != "healthy":
                    self.logger.warn(
                        "***** ALERT : {0} is not healthy. Current status : {1}%".format(
                            node["hostname"], node["status"]))
                    if cbcollect_on_high_mem_cpu_usage:
                        should_cbcollect = True

            last_scan_timestamp = datetime.now() - timedelta(minutes=10.0)
            self.logger.info("Last scan timestamp :" + str(last_scan_timestamp))

            if should_cbcollect:
                self.logger.info("====== RUNNING CBCOLLECT_INFO ======")
                # command = "/opt/couchbase/bin/cbcollect_info outputfile.zip --multi-node-diag --upload-host=s3.amazonaws.com/bugdb/jira --customer=systestmon-{0}".format(
                #    timestamp)
                epoch_time = int(time.time())
                command = "/opt/couchbase/bin/couchbase-cli collect-logs-start -c {0} -u {1} -p {2} --all-nodes --upload --upload-host s3.amazonaws.com/bugdb/jira --customer systestmon-{3}".format(
                    master_node, rest_username, rest_password, epoch_time)
                _, cbcollect_output, std_err = self.execute_command(
                    command, master_node, ssh_username, ssh_password)
                if std_err:
                    self.logger.error(
                        "Error seen while running cbcollect_info ")
                    self.logger.info(std_err)
                else:
                    for i in range(len(cbcollect_output)):
                        self.logger.info(cbcollect_output[i])

                while True:
                    command = "/opt/couchbase/bin/couchbase-cli collect-logs-status -c {0} -u {1} -p {2}".format(
                        master_node, rest_username, rest_password)
                    _, cbcollect_output, std_err = self.execute_command(
                        command, master_node, ssh_username, ssh_password)
                    if std_err:
                        self.logger.error(
                            "Error seen while running cbcollect_info ")
                        self.logger.info(std_err)
                    else:
                        # for i in range(len(cbcollect_output)):
                        #    print cbcollect_output[i]
                        if cbcollect_output[0] == "Status: completed":
                            cbcollect_upload_paths = []
                            for line in cbcollect_output:
                                if "url :" in line:
                                    cbcollect_upload_paths.append(line)
                            self.logger.info("cbcollect upload paths : \n")
                            self.logger.info('\n'.join(cbcollect_upload_paths))
                            # for i in range(len(cbcollect_upload_paths)):
                            #    print cbcollect_upload_paths[i]

                            break
                        elif cbcollect_output[0] == "Status: running":
                            time.sleep(60)
                        else:
                            self.logger.error("Issue with cbcollect")

            prev_keyword_counts = copy.deepcopy(keyword_counts)
            # self.logger.info(prev_keyword_counts)

            self.logger.info(
                "====== Log scan complete. Sleeping for {0} seconds ======".format(
                    self.scan_interval))
            time.sleep(self.scan_interval)

    def print_output(self, output, last_scan_timestamp):
        for line in output:
            match = re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', line)
            if match:
                timestamp_in_log = datetime.strptime(match.group(), '%Y-%m-%dT%H:%M:%S')
                if timestamp_in_log >= last_scan_timestamp and self.check_op_in_ignorelist(line):
                    self.logger.info(line)
            else:
                self.logger.info(line)

    def check_op_in_ignorelist(self, line):
        for ignore_text in self.ignore_list:
            if ignore_text in line:
                return False
        return True

    def get_services_map(self, master, rest_username, rest_password):
        cluster_url = "http://" + master + ":8091/pools/default"
        node_map = []

        # Get map of nodes in the cluster
        response = requests.get(cluster_url, auth=(
            rest_username, rest_password), verify=True)

        if (response.ok):
            response = json.loads(str(response.content))

            for node in response["nodes"]:
                clusternode = {}
                clusternode["hostname"] = node["hostname"].replace(":8091", "")
                clusternode["services"] = node["services"]
                mem_used = int(node["memoryTotal"]) - int(node["memoryFree"])
                clusternode["memUsage"] = round(
                    float(mem_used / float(node["memoryTotal"]) * 100), 2)
                clusternode["cpuUsage"] = round(
                    node["systemStats"]["cpu_utilization_rate"], 2)
                clusternode["status"] = node["status"]
                node_map.append(clusternode)
        else:
            response.raise_for_status()

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
            temp += data
            data = channel.recv(1024)
        channel.close()
        stdin.close()

        output = []
        error = []
        for line in stdout.read().splitlines():
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


if __name__ == '__main__':
    SysTestMon().run()
