from flask import jsonify

from werkzeug.utils import secure_filename

import open_data_injector_thread

import os

import requests

from requests.exceptions import RequestException

import errors

from threading import Event

from state import SingletonState

ERROR_FILE_NAME = "error_dump"


class RequestHandler:

    def __init__(self):
        self.state = SingletonState.instance()
        self.api_url = None
        self.index_field = None
        self.size_field = None
        self.path_data_list = None
        self.stopFlag = None

    def get_state(self):
        return jsonify({"state": self.state.get_state()})

    def pause(self):

        if not self.state.verify_modify_state('RUNNING', 'PAUSE'):
            return 'There is no injector to pause'

        return 'Injector thread paused'

    def get_error(self):

        if not self.state.verify_modify_state('CRASHED', 'AVAILABLE'):
            return 'Application not crashed', 400

        if not os.path.exists(os.path.join('.', ERROR_FILE_NAME)):
            return errors.no_error_file_generated()

        with open(ERROR_FILE_NAME, 'r') as error_file:
            content = error_file.read()

        return str(content), 200

    def set_mapping(self, request):

        # HAVE TO GET LOCKED

        if self.state.get_state() != 'AVAILABLE':
            return 'Injector not available'

        if 'mapping.json' not in request.files:
            return 'No mapping file provide'
        file = request.files['mapping.json']

        if file:
            filename = secure_filename('mapping.json')
            file.save(os.path.join('', filename))

        return 'File accepted'

    def set_data(self, request):

        # HAVE TO GET LOCKED

        if self.state.get_state() != 'AVAILABLE':
            return 'Injector not available'

        try:
            json_data = request.json
        except Exception:
            return errors.malformed_json_data()

        if json_data is None:
            return errors.waiting_json_data()

        open_data_url = json_data.get('api_url')
        if open_data_url is None:
            return errors.no_url_provided()

        try:
            requests.get(open_data_url)
        except RequestException:
            return errors.cannot_reach_provided_url()

        open_data_url = json_data.get('api_url')

        self.api_url = open_data_url

        try:
            self.index_field = json_data['index_field']
        except KeyError:
            return "Missing index field", 400

        try:
            self.size_field = json_data['size_field']
        except KeyError:
            return "Missing size field", 400

        try:
            self.path_data_list = json_data['path_data_list']
        except KeyError:
            return "Missing path to data list", 400

        return 'Data configuration accepted', 200

    def start(self):

        if not self.state.verify_modify_state('AVAILABLE', 'RUNNING'):
            return 'Injector not available'

        thread = open_data_injector_thread.ThreadClass(self.api_url, self.index_field, self.size_field, self.path_data_list)
        thread.setDaemon(True)
        thread.start()

        return 'Injector launch'

    def start_interval(self, request):

        try:
            json_data = request.json
        except Exception:
            return errors.malformed_json_data()

        if json_data is None:
            return errors.waiting_json_data()

        interval = json_data.get('interval')

        if interval is None:
            return errors.interval_parameter_missing()

        try:
            interval = int(interval)
        except Exception:
            return errors.cannot_convert_interval()

        if not self.state.verify_modify_state('AVAILABLE', 'INTERVAL_RUNNING'):
            return 'Injector not available'

        stopFlag = Event()

        self.stopFlag = stopFlag

        thread = open_data_injector_thread.ThreadClass(self.api_url, self.index_field, self.size_field, self.path_data_list, interval=interval, event=stopFlag)
        thread.setDaemon(True)
        thread.start()

        return 'Injector launch'

    def stop(self):

        if not self.state.verify_modify_states(['RUNNING', 'INTERVAL_RUNNING'], 'STOP'):
            return 'There is no injector to stop'

        self.stopFlag.set()

        return 'Injector thread stopped'

    def resume(self):

        if not self.state.verify_modify_state('PAUSE', 'RUNNING'):
            return 'Injector not paused'

        thread = open_data_injector_thread.ThreadClass(self.api_url)
        thread.setDaemon(True)
        thread.start()

        return 'Injector unpaused'
