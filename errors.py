def no_app_name_provided():
    return 'No app name provided', 400


def no_app_found():
    return 'No app found with the provided name', 404


def forbidden_access_to_this_app():
    return 'You cannot interact with this app', 403


def missing_file():
    return 'File is missing', 400


def app_name_already_exists():
    return 'App name already exists', 409


def waiting_json_data():
    return 'Needed json data to handle this request', 400


def no_token_provided():
    return 'No token provided', 400


def malformed_json_data():
    return 'The provided json data is malformed', 400


def no_error_file_generated():
    return 'There is no error file generated', 404


def no_url_provided():
    return 'Api url is missing', 400


def cannot_reach_provided_url():
    return 'Url not accepted, cannot reach the provided url', 404


def cannot_convert_interval():
    return 'Cannot convert the provided interval into integer', 400