from datetime import datetime


def from_iso_format(datestr: str) -> datetime:
    if '.' not in datestr:
        return datetime.fromisoformat(datestr)
    mills = datestr.split(".")[-1]
    if len(mills) == 6:
        return datetime.fromisoformat(datestr)
    datestr_copy = ".".join(datestr.split(".")[:-1])
    datestr_copy += "." + mills.zfill(6)
    return datetime.fromisoformat(datestr_copy)
