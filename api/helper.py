import re

def check_string(string,variable_name=None):
    pattern = r"^[a-zA-Z0-9\s_.-@]*$"
    if not bool(re.match(pattern, string)):
        raise Exception(f"Not a valid string value : {variable_name}")
    return string