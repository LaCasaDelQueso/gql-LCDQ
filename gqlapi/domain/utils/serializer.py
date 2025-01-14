import datetime

from uuid import UUID


def data_to_json(generic):
    obj = vars(generic)
    for key in obj:
        if isinstance(obj[key], UUID):
            obj[key] = "placeholder"
        elif isinstance(obj[key], datetime.datetime):
            obj[key] = obj[key].strftime("%Y-%m-%d %H:%M:%S")

    return obj
