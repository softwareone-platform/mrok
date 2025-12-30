import json
from collections import OrderedDict, deque
from typing import Literal
from uuid import uuid4

import zmq.asyncio
from rich.table import Table
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.events import Resize
from textual.widgets import (
    Collapsible,
    DataTable,
    Digits,
    Header,
    Label,
    Placeholder,
    Sparkline,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
    Tree,
)
from textual.widgets.data_table import ColumnKey
from textual.worker import get_current_worker

from mrok import __version__
from mrok.proxy.models import Event, HTTPHeaders, HTTPResponse, ServiceMetadata, WorkerMetrics


def build_tree(node, data):
    if isinstance(data, dict):
        for key, value in data.items():
            child = node.add(str(key))
            build_tree(child, value)
    elif isinstance(data, list):
        for index, value in enumerate(data):
            child = node.add(f"[{index}]")
            build_tree(child, value)
    else:
        node.add(repr(data))


def hexdump(data, width=16):
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i : i + width]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
        lines.append(f"{hex_part:<{width * 3}} {ascii_part}")
    return "\n".join(lines)


class Counter(Digits):
    DEFAULT_CSS = """
    Counter {
        text-align: center;
        border: round #00BBFF;
    }
    """

    def __init__(
        self,
        counter_name: str,
        value: str = "",
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        self.counter_name = counter_name
        super().__init__(
            value,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )

    def on_mount(self) -> None:
        self.border_title = self.counter_name


class HostInfo(Static):
    BORDER_TITLE = "Process"
    DEFAULT_CSS = """
    HostInfo {
        border: round #00BBFF;
        layout: grid;
        grid-size: 2 2;
        grid-gutter: 0;
        grid-columns: 1fr 2fr;
        height: 100%;
        width: 25;
        content-align: center middle;
    }
    """

    def __init__(
        self,
        content="",
        *,
        expand=False,
        shrink=False,
        markup=True,
        name=None,
        id=None,
        classes=None,
        disabled=False,
    ) -> None:
        super().__init__(
            content,
            expand=expand,
            shrink=shrink,
            markup=markup,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )
        self.mem_values: deque = deque([0] * 100, maxlen=100)
        self.cpu_values: deque = deque([0] * 100, maxlen=100)

    def compose(self) -> ComposeResult:
        yield Label("CPU")
        yield Sparkline(self.cpu_values, id="cpu")
        yield Label("Memory")
        yield Sparkline(self.mem_values, id="mem")

    def update_info(self, cpu: int, mem: int):
        self.cpu_values.append(cpu)
        self.mem_values.append(mem)
        self.query_one("#cpu", Sparkline).data = self.cpu_values
        self.query_one("#mem", Sparkline).data = self.mem_values


class InfoPanel(Static):
    BORDER_TITLE = "Info"

    DEFAULT_CSS = """
    InfoPanel {
        background: black;
        height: 100%;
        border: round #0088FF;
    }
    """

    def __init__(
        self,
        content="",
        *,
        expand=False,
        shrink=False,
        markup=True,
        name=None,
        id=None,
        classes=None,
        disabled=False,
    ) -> None:
        super().__init__(
            content,
            expand=expand,
            shrink=shrink,
            markup=markup,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )

    def compose(self) -> ComposeResult:
        yield DataTable(show_header=False, cursor_type="none")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Label", "Value")

        # if len(self.workers_metrics):
        #     hinfo = self.query_one(HostInfo)
        #     hinfo.update_info(
        #         cpu=int(mean([m.process.cpu for m in self.workers_metrics.values()])),
        #         mem=int(mean([m.process.mem for m in self.workers_metrics.values()])),
        #     )

    def update_meta(self, meta: ServiceMetadata) -> None:
        table = self.query_one(DataTable)
        if len(table.rows) == 0:
            table.add_row("URL", f"https://{meta.extension}.{meta.domain}")
            table.add_row("Extension ID", meta.extension.upper())
            table.add_row("Instance ID", meta.instance.upper())
            table.add_row("mrok version ID", __version__)
            self.loading = False


class Requests(Static):
    BORDER_TITLE = "Requests"
    DEFAULT_CSS = """
    Requests {
        background: black;
        height: 100%;
        border: round #0088FF;
    }
    """

    def compose(self) -> ComposeResult:
        # give the table an id so CSS can target it; enable zebra stripes
        yield DataTable(id="requests", zebra_stripes=True, cursor_type="row")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_column(
            "Method",
            width=7,
        )
        table.add_column(
            "Status",
            width=6,
        )
        table.add_column("Path", width=25, key="path")
        table.add_column(
            "Duration (ms)",
            width=13,
        )


class Details(Static):
    BORDER_TITLE = "Details"

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Headers"):
                with VerticalScroll():
                    with Collapsible(title="General", collapsed=False):
                        yield DataTable(id="general-data", show_header=False, show_cursor=False)

                    with Collapsible(
                        title="Request Headers", collapsed=False, id="request-headers"
                    ):
                        yield Static(id="request-headers-table")
                    with Collapsible(
                        title="Response Headers", collapsed=False, id="response-headers"
                    ):
                        yield Static(id="response-headers-table")
            with TabPane("Payload"):
                yield Placeholder("payload")
            with TabPane("Preview"):
                yield Tree("Preview")
            with TabPane("Response"):
                yield TextArea(id="raw-response", read_only=True)

    def update_headers(self, type: Literal["request", "response"], headers: HTTPHeaders):
        collapsible = self.query_one(f"#{type}-headers", Collapsible)
        collapsible.title = (
            f"{type.capitalize()} Headers ({len(headers)})"
            if len(headers)
            else f"{type.capitalize()} Headers"
        )
        if len(headers):
            headers_table = Table(show_header=False, box=None)
            for k, v in headers.items():
                headers_table.add_row(f"[orange3]{k}[/]", v)
            self.query_one(f"#{type}-headers-table", Static).content = headers_table
        else:
            self.query_one(f"#{type}-headers-table", Static).content = ""

    def update_preview(self, response: HTTPResponse):
        tree = self.query_one(Tree)
        tree.clear()
        if (
            response.headers.get("Content-Type", "").startswith("application/json")
            and response.body
        ):
            build_tree(tree.root, json.loads(response.body.decode()))

    def update_response(self, response: HTTPResponse):
        text_area = self.query_one("#raw-response", TextArea)
        text_area.clear()
        if response.body:
            text_area.text = response.body.decode()

    def update_info(self, response: HTTPResponse):
        general_table = self.query_one("#general-data", DataTable)
        general_table.clear()
        url = response.request.url
        if response.request.query_string:
            url = f"{url}?{response.request.query_string.decode()}"
        general_table.add_row("Request Url", url)
        general_table.add_row("Request Method", self.format_method(response.request.method))
        general_table.add_row("Status Code", self.format_status(response.status))
        self.update_headers("request", response.request.headers)
        self.update_headers("response", response.headers)
        self.update_preview(response)
        self.update_response(response)

    def format_status(self, status: int) -> str:
        if status < 400:
            return f"🟢 [green]{status}[/]"
        elif status < 500:
            return f"🟠 [orange3]{status}[/]"
        else:
            return f"🔴 [red]{status}[/]"

    def format_method(self, method: str) -> str:
        method = method.upper()
        if method in ["POST", "PUT", "PATCH"]:
            return f"[orange3]{method}[/]"
        elif method == "DELETE":
            return f"[red]{method}[/]"
        else:
            return f"[blue]{method}[/]"

    def on_mount(self) -> None:
        general_table = self.query_one("#general-data", DataTable)
        general_table.add_columns("Label", "Value")


class LeftPanel(Static):
    DEFAULT_CSS = """
    LeftPanel {
        layout: grid;
        grid-size: 1 3;
        grid-rows: 1fr 2fr 4fr;
        grid-columns: 1fr;
        background: black;
        height: 100%;
        width: 100%;
    }
    Details {
        background: black;
        height: 100%;
        border: round #0088FF;
    }
    """

    def compose(self):
        yield InfoPanel()
        yield Requests()
        yield Details()


class MetricsPanel(Static):
    BORDER_TITLE = "Metrics"
    DEFAULT_CSS = """
    MetricsPanel {
        background: black;
        layout: grid;
        grid-size: 1 4;
        grid-gutter: 0;
        content-align: center top;
        border: round #0088FF;
        height: 100%;
        grid-rows: auto auto auto auto;
    }
    #requests-rps {
        color: #0088FF;
    }
    #requests-ok {
        color: green;
    }
    #requests-ko {
        color: red;
    }
    """

    def __init__(
        self,
        content="",
        *,
        expand=False,
        shrink=False,
        markup=True,
        name=None,
        id=None,
        classes=None,
        disabled=False,
    ) -> None:
        super().__init__(
            content,
            expand=expand,
            shrink=shrink,
            markup=markup,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )
        self.workers_metrics: dict[str, WorkerMetrics] = {}

    def compose(self) -> ComposeResult:
        yield Counter("RPS", id="requests-rps")
        yield Counter("Total", id="requests-total")
        yield Counter("Success", id="requests-ok")
        yield Counter("Failed", id="requests-ko")

    def on_mount(self) -> None:
        self.set_interval(5.0, self.update_stats)

    def update_stats(self) -> None:
        self.query_one("#requests-rps", Digits).update(
            str(sum(m.requests.rps for m in self.workers_metrics.values()))
        )
        self.query_one("#requests-total", Digits).update(
            str(sum(m.requests.total for m in self.workers_metrics.values()))
        )
        self.query_one("#requests-ok", Digits).update(
            str(sum(m.requests.successful for m in self.workers_metrics.values()))
        )
        self.query_one("#requests-ko", Digits).update(
            str(sum(m.requests.failed for m in self.workers_metrics.values()))
        )
        self.loading = False

        # if len(self.workers_metrics):
        #     hinfo = self.query_one(HostInfo)
        #     hinfo.update_info(
        #         cpu=int(mean([m.process.cpu for m in self.workers_metrics.values()])),
        #         mem=int(mean([m.process.mem for m in self.workers_metrics.values()])),
        #     )

    def update_metrics(self, metrics: WorkerMetrics) -> None:
        self.workers_metrics[metrics.worker_id] = metrics


class InspectorApp(App):
    TITLE = "mrok Dev Console"
    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 1;
        grid-columns: 5fr 1fr;
        background: black;
    }
    DataTable {
        background: black;
        color: #dddddd;
        height: auto;
        max-height: 100%;
    }

    /* Header row: white title text, neon underline */
    DataTable > .datatable--header {
        text-style: bold;
        background: black;
        color: white;
        border-bottom: solid #0088FF;
    }

    /* Cells inherit neon text on black */
    DataTable .cell {
        color: #0088FF;
        background: black;
    }

    /* Zebra stripes: even rows slightly lighter than black */
    DataTable > .datatable--even-row {
        background: rgb(10,10,14);
    }
    DataTable > .datatable--odd-row {
        background: black;
    }

    /* Hover and focus styles */
    DataTable > .datatable--hover {
        background: rgb(6,12,20);
    }
    DataTable:focus > .datatable--cursor {
        background: rgb(2,40,70);
        color: white;
    }

    /* Fixed columns/rows use a muted neon background */
    DataTable > .datatable--fixed {
        background: rgb(6,6,10);
        color: #00CFFF;
    }
    Collapsible {
        background: black;
        border: round #00BBFF;
    }
    """

    def __init__(
        self,
        subscriber_port: int,
        max_requests: int = 1000,
        driver_class=None,
        css_path=None,
        watch_css=False,
        ansi_color=False,
    ):
        super().__init__(driver_class, css_path, watch_css, ansi_color)
        self.ctx = zmq.asyncio.Context()
        self.socket = self.ctx.socket(zmq.SUB)
        self.socket.connect(f"tcp://127.0.0.1:{subscriber_port}")
        self.max_requests = max_requests
        self.requests: OrderedDict = OrderedDict()

    def compose(self) -> ComposeResult:
        yield Header()
        yield LeftPanel()
        yield MetricsPanel()

    async def on_mount(self):
        self.query_one(InfoPanel).loading = True
        self.query_one(MetricsPanel).loading = True
        self.socket.subscribe("")
        self.consumer()

    @work(exclusive=True)
    async def consumer(self):
        worker = get_current_worker()
        requests_table = self.query_one("#requests", DataTable)
        while not worker.is_cancelled:
            try:
                self.log("Waiting for event")
                event = Event.model_validate_json(await self.socket.recv_string())
                self.log(f"Event received: {event}")
                if event.type == "status":
                    info_widget = self.query_one(InfoPanel)
                    info_widget.update_meta(event.data.meta)
                    metrics_widget = self.query_one(MetricsPanel)
                    metrics_widget.update_metrics(event.data.metrics)
                    continue

                response = event.data
                if len(self.requests) == self.max_requests:
                    self.requests.popitem(last=False)
                req_id = str(uuid4())
                self.requests[req_id] = response
                requests_table.clear()
                for key, response in reversed(self.requests.items()):
                    requests_table.add_row(
                        response.request.method,
                        response.status,
                        response.request.url,
                        response.duration * 1000,
                        key=key,
                    )
            except Exception as e:
                self.log(e)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if not event.row_key:
            return
        response = self.requests[event.row_key]
        details = self.query_one(Details)
        details.update_info(response)

    @on(Resize)
    def resize_requests_table(self, event: Resize):
        width = event.size.width
        table = self.query_one("#requests", DataTable)
        table.columns[ColumnKey("path")].width = width - 69
