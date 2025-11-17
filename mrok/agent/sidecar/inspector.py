import httpx
import typer
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import DataTable, Footer, Header, Static, TabbedContent, TabPane

from mrok.conf import get_settings


def color_for_status(status: int) -> str:
    if 200 <= status < 300:
        return "green"
    return "red"


class RequestDetailCard(Widget):
    request = reactive(None, recompose=True)

    def compose(self):
        with Vertical():
            if self.request:
                yield from self._build_card()
            else:
                yield Static("Select a request to view details.", classes="summary")

    def _build_card(self):
        r = self.request or {}  # type: ignore
        method = r.get("method", "")
        path = r.get("path", "")
        status = int(r.get("status", 0))
        duration = int(r.get("duration", 0) * 1000)
        parameters = r.get("query_string")
        req_headers = r.get("request_headers", [])
        res_headers = r.get("response_headers", [])
        req_body = r.get("request_body")
        res_body = r.get("response_body")

        summary_text = Text()
        summary_text.append(f"{method} ", style="bold cyan")
        summary_text.append(f"{path}\n", style="bold")
        summary_text.append("Status: ", style="bold")
        summary_text.append(f"{status} ", style=f"bold {color_for_status(status)}")
        summary_text.append(f"• Duration: {duration} ms", style="dim")
        req_headers_formatted = "\n".join(f"[yellow]{k}[/]: {v}" for k, v in req_headers)
        res_headers_formatted = "\n".join(f"[yellow]{k}[/]: {v}" for k, v in res_headers)

        yield Static(Panel(summary_text, title="Request Summary", expand=False))
        with TabbedContent(initial="response"):
            with TabPane("Response body", id="response"):
                if res_body:
                    yield VerticalScroll(
                        Static(Syntax(res_body, "json", theme="monokai", word_wrap=True))
                    )
                else:
                    yield Static("No body")
            with TabPane("Request headers", id="req_headers"):
                yield VerticalScroll(
                    Static(Panel(req_headers_formatted or "<none>", title="Headers"))
                )
            with TabPane("Response headers", id="res_headers"):
                yield VerticalScroll(
                    Static(Panel(res_headers_formatted or "<none>", title="Headers"))
                )
            with TabPane("Request body", id="request"):
                if req_body:
                    yield VerticalScroll(
                        Static(Syntax(req_body, "json", theme="monokai", word_wrap=True))
                    )
                else:
                    yield Static("No body")
            with TabPane("Request parameters", id="params"):
                yield VerticalScroll(Static(parameters or "No parameters"))


class InspectorApp(App):
    TITLE = "mrok Agent Web Inspection Interface"
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]
    CSS = """
        #app-grid {
            layout: grid;
            grid-size: 2;
            grid-columns: 1fr 2fr;
            grid-rows: 1fr;
            height: 100%;
            width: 100%;
        }

        #left-pane {
            background: $panel;
            padding: 1;
            border: round $accent;
            height: 100%;
        }

        #right-pane {
            background: $boost;
            padding: 1;
            border: round $accent-darken-1;
            height: 100%;
            overflow: auto;
        }

        #right-pane > Static {
            background: $surface;
            height: 100%;
            overflow: auto;
            padding: 1;
        }
        """

    def __init__(self):
        super().__init__()
        self.table = DataTable(zebra_stripes=True, cursor_type="row")
        self.detail_card = RequestDetailCard()
        self.refresh_interval = 10.0
        self.requests = {}
        self.last_request = 0
        self.settings = get_settings()
        self.store_port = self.settings.sidecar.store_port

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="app-grid"):
            with VerticalScroll(id="left-pane"):
                yield self.table
            with Horizontal(id="right-pane"):
                yield self.detail_card
        yield Footer()

    async def on_mount(self):
        self.table.add_columns(("ID", "id"), "Method", "Status", "Path", "Duration (ms)")
        await self.refresh_data()
        self.set_interval(self.refresh_interval, self.refresh_data)

    async def refresh_data(self):
        try:
            async with httpx.AsyncClient() as client:
                query = f"?offset={self.last_request}" if self.last_request else ""
                resp = await client.get(f"http://127.0.0.1:{self.store_port}/requests/{query}")
            requests = resp.json()
        except Exception as e:
            typer.echo(f"[red]Refresh_data failed:[/red] {e}")
            return

        for r in requests:
            self.table.add_row(
                r["id"],
                r.get("method", ""),
                r.get("status", ""),
                r.get("path", ""),
                int((r.get("duration", 0)) * 1000),
                key=str(r["id"]),
            )
            self.requests[str(r["id"])] = r
            self.last_request = max(self.last_request, r["id"])
        self.table.sort("id", reverse=True)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        req_id = event.row_key.value
        self.detail_card.request = self.requests.get(req_id)


if __name__ == "__main__":  # pragma: no cover
    app = InspectorApp()
    app.run()
