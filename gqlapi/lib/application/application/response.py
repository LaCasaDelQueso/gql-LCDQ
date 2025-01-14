import pickle

from starlette.responses import (
    Response,
    JSONResponse
)


class AppResponse(Response):
    media_type = "text/plain"


class AppJSONResponse(JSONResponse):
    media_type = "application/json"


class AppPickeResponse(Response):
    media_type = "text/plain"

    def __init__(self, data):
        serialized = pickle.dumps(data).decode('raw_unicode_escape')
        super(AppPickeResponse, self).__init__(serialized)
