import logging
import socket

from uvicorn import server

server.logger = logging.getLogger("mrok.proxy")


class MrokServer(server.Server):
    async def serve(self, sockets: list[socket.socket] | None = None) -> None:
        if not sockets:
            sockets = [self.config.bind_socket()]
        with self.capture_signals():
            await self._serve(sockets)
