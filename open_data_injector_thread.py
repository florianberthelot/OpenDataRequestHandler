import os
import json
from ziggy_enabler import ziggyClient, converter, injector
from threading import Thread
import collections
import traceback
import requests
from state import SingletonState

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAPPING_PATH = os.path.join(BASE_DIR, "mapping.json")
DATA_PATH = os.path.join(BASE_DIR, "data.json")
NAMESPACE = "TEST_THREAD_INJECTOR"
API_ENDPOINT = "http://ziggy-api-int.nprpaas.ddns.integ.dns-orange.fr/api/"
RECOVERY_PATH = os.path.join(BASE_DIR, "error")
ERROR_FILE_NAME = "error_dump"


class ThreadClass(Thread):

    def extract_subpart_dict(self, dict, first_element):
        return {k: dict[k] for k in list(dict.keys())[first_element:] if k in dict}

    def __init__(self, api_url, index_field, size_field, path_data_list, interval=300, event=None):
        Thread.__init__(self)
        self.stopped = event
        self.state = SingletonState.instance()
        self.api_url = api_url
        self.index_field = index_field
        self.size_field = size_field
        self.path_data_list = path_data_list
        self.separator = '.'

        self.interval = interval

    def run(self):

        self.inject()

        while self.stopped is not None and not self.stopped.wait(self.interval):
            self.inject()

        if self.state.get_state() != 'PAUSE' or self.state.get_state() != 'CRASHED':
            self.state.set_state('AVAILABLE')

    def inject(self):

        print("Inject")

        try:

            if os.path.exists(MAPPING_PATH):
                try:
                    with open(os.path.join(MAPPING_PATH), "r") as f:
                        mapping = json.load(f)
                except Exception as e:
                    raise Exception('Failed to load mapping file as json.\n' + str(e))
            else:
                raise Exception('There is no mapping file')

            client = ziggyClient.ZiggyHTTPClient(NAMESPACE, API_ENDPOINT)
            manager = injector.DataManager(client, mapping)

            if self.api_url is None:
                raise Exception('There is no api URL provided')

            conv = converter.JsonToRDFConverter(mapping)

            index = 0
            size = 5000

            while True:

                data = self.download_from_api_url(size, index)

                map_id_projections = collections.OrderedDict(sorted(conv.parse(data).items()))

                recovery_line = 0

                if os.path.exists(RECOVERY_PATH):
                    f = open(str(RECOVERY_PATH), "r")
                    recovery_line = int(f.readline())

                    map_id_projections = collections.OrderedDict(
                        sorted(self.extract_subpart_dict(map_id_projections, recovery_line).items()))

                    f.close()
                    os.remove(RECOVERY_PATH)

                print("Process")

                manager.process_batch(map_id_projections, RECOVERY_PATH, begin_index=recovery_line)

                print(map_id_projections)

                if len(data) < size:
                    print(data)
                    print(size)
                    break

                index = index + 1

        except Exception as e:
            print(traceback.print_exc())
            error_file = open(ERROR_FILE_NAME, "w")
            error_file.write(str(e))
            self.stopped.set()
            self.state.set_state('CRASHED')

    def download_from_api_url(self, size, index):

        if self.size_field is None:
            raise Exception("Size field is None")
        if self.index_field is None:
            raise Exception("Index field is None")

        params = {str(self.index_field): index * size, str(self.size_field): size}
        response = requests.get(self.api_url, params=params)

        if 400 <= response.status_code < 500:
            print(response.content)
            raise Exception('Failed to retrieve data')

        content = response.content

        if isinstance(content, bytes):
            content = content.decode("utf-8")

        try:
            content = json.loads(content)
        except Exception:
            raise Exception("Cannot convert response content into json")

        content = self.reach_data(content)

        if not isinstance(content, list):
            raise Exception('The given data list path do not refer to a list')

        return content

    def reach_data(self, content):

        if self.path_data_list == "":
            return content

        path_data_list = self.path_data_list.split(self.separator)

        reached_data = content

        for param in path_data_list:

            if isinstance(reached_data, list):
                try:
                    index = int(param)
                except ValueError:
                    raise Exception(
                        "You try to access list value with non integer value.\n Path to the value {}.".format(
                            path_data_list))
                reached_data = reached_data[index]
            else:

                reached_data = reached_data[param]

        return reached_data
