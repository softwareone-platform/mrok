import logging

from uvicorn.protocols.http.httptools_impl import HttpToolsProtocol


class MrokHttpToolsProtocol(HttpToolsProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger("mrok.proxy")
        self.access_logger = logging.getLogger("mrok.access")
        self.access_log = self.access_logger.hasHandlers()
