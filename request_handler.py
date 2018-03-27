from flask import jsonify

from werkzeug.utils import secure_filename

import open_data_injector_thread

import os

import requests

import errors

from threading import Event

from state import SingletonState

from subprocess import call

ERROR_FILE_NAME = "error_dump"




class RequestHandler:

    def __init__(self):
        self.state = SingletonState.instance()

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

        return (str(content), 200)

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

        call(["ls"])

        return 'File accepted'

    def set_data(self, request):

        # HAVE TO GET LOCKED

        if self.state.get_state() != 'AVAILABLE':
            return 'Injector not available'

        try:
            json_data = request.json
        except:
            return errors.malformed_json_data()

        if json_data is None:
            return errors.waiting_json_data()

        open_data_url = json_data.get('api_url')
        if open_data_url is None:
            return errors.no_url_provided()

        try:
            requests.get(open_data_url)
        except:
            return errors.cannot_reach_provided_url()

        self.api_url = open_data_url

        return 'URL accepted', 200

    def start(self):

        if not self.state.verify_modify_state('AVAILABLE', 'RUNNING'):
            return 'Injector not available'

        thread = open_data_injector_thread.ThreadClass(self.api_url)
        thread.setDaemon(True)
        thread.start()

        return 'Injector launch'

    def start_interval(self, request):

        try:
            json_data = request.json
        except:
            return errors.malformed_json_data()

        if json_data is None:
            return errors.waiting_json_data()

        interval = json_data.get('interval')

        try:
            interval = int(interval)
        except:
            errors.cannot_convert_interval()

        if not self.state.verify_modify_state('AVAILABLE', 'INTERVAL_RUNNING'):
            return 'Injector not available'

        stopFlag = Event()

        self.stopFlag = stopFlag

        thread = open_data_injector_thread.ThreadClass(self.api_url, interval=interval, event=stopFlag)
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
