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

    def __init__(self, api_url, interval=300, event=None):
        Thread.__init__(self)
        self.stopped = event
        self.state = SingletonState.instance()
        self.api_url = api_url
        self.interval = interval

    def run(self):

        self.inject()

        while self.stopped is not None and not self.stopped.wait(self.interval):
            self.inject()

        if self.state.get_state() != 'PAUSE':
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

                print("HERE")

                data = self.download_from_api_url(self.api_url, size, index)

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

                # manager.process_batch(map_id_projections, RECOVERY_PATH, begin_index=recovery_line)

                print(map_id_projections)

                if len(data) < size:
                    print("exit")
                    break

                index = index + 1

        except Exception as e:
            print(traceback.print_exc())
            error_file = open(ERROR_FILE_NAME, "w")
            error_file.write(str(e))
            self.state.set_state('CRASHED')

    def download_from_api_url(self, url, size, index):
        params = {'start': index * size, 'rows': size}
        response = requests.get(url, params=params)

        if 400 <= response.status_code < 500:
            print(response.content)
            raise Exception('Failed to retrieve data')

        content = response.content

        if isinstance(content, bytes):
            content = content.decode("utf-8")

        content = json.loads(content)

        if type(content) != list:
            content = content.get("records")

        if content is None:
            print(response.status_code)
            raise Exception('There is no list in retrieved data')

        return content
