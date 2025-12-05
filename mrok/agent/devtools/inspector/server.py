from aiohttp import web
from textual_serve.server import Server


class InspectorServer(Server):
    def __init__(self, port: int = 7777, subscriber_port: int = 50001):
        self.subscriber_port = subscriber_port
        super().__init__(
            f"python -m mrok.agent.devtools.inspector -p {subscriber_port}",
            port=port,
        )

    async def on_startup(self, app: web.Application) -> None:
        self.console.print(
            f"Serving mrok inspector web app on {self.public_url} "
            f"(subscriber port {self.subscriber_port})"
        )
        self.console.print("\n[cyan]Press Ctrl+C to quit")
