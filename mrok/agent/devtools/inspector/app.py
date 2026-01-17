import argparse
import json
from collections import OrderedDict, deque
from statistics import mean
from typing import Literal
from uuid import uuid4

import zmq.asyncio
from rich.table import Table
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.events import Resize
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Collapsible,
    ContentSwitcher,
    DataTable,
    Digits,
    Header,
    Label,
    ProgressBar,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
    Tree,
)
from textual.widgets.data_table import ColumnKey
from textual.worker import get_current_worker

from mrok import __version__
from mrok.agent.devtools.inspector.utils import (
    build_tree,
    get_highlighter_language_by_content_type,
    hexdump,
    humanize_bytes,
    parse_content_type,
    parse_form_data,
)
from mrok.proxy.models import (
    Event,
    HTTPHeaders,
    HTTPRequest,
    HTTPResponse,
    ServiceMetadata,
    WorkerMetrics,
)

MIN_COLS = 160
MIN_ROWS = 45


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


class ProcessInfoBar(Static):
    DEFAULT_CSS = """
    ProcessInfoBar {
        width: 100%;
        align: center middle;
        padding: 1;
    }
    ProgressBar {
        width: 100%;
    }
    ProgressBar > Bar {
        width: 24;
    }
    ProgressBar > Bar > .bar--complete {
        color: red;
    }
    Vertical {
        width: auto;
        align: center middle;
    }
    """

    def __init__(self, label: str, **kwargs):
        super().__init__(**kwargs)
        self.label_text = label

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(f"[b]{self.label_text}[/b]")
            yield ProgressBar(
                total=100,
                show_percentage=True,
                show_eta=False,
            )

    def update_value(self, value: float) -> None:
        self.query_one(ProgressBar).update(progress=value)


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

    def update_meta(self, meta: ServiceMetadata) -> None:
        table = self.query_one(DataTable)
        if len(table.rows) == 0:
            table.add_row("URL", f"https://{meta.extension}.{meta.domain}")
            table.add_row("Extension ID", meta.extension.upper())
            table.add_row("Instance ID", meta.instance.upper())
            table.add_row("mrok version", __version__)
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
                with ContentSwitcher(initial="payload-tree", id="payload-switcher"):
                    yield Tree("Payload", id="payload-tree")
                    yield DataTable(show_header=False, show_cursor=False, id="payload-formdata")
                    yield TextArea(id="payload-other", read_only=True)
            with TabPane("Preview"):
                with ContentSwitcher(initial="preview-tree", id="preview-switcher"):
                    yield Tree("Preview", id="preview-tree")
                    yield TextArea(id="preview-other", read_only=True)
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
        tree = self.query_one("#preview-tree", Tree)
        tree.clear()
        self.query_one("#preview-switcher", ContentSwitcher).current = "preview-tree"
        if not response.body:
            return
        content_type_info = parse_content_type(response.headers["Content-Type"])
        if content_type_info.content_type == "application/json":
            build_tree(
                tree.root,
                json.loads(response.body.decode(encoding=content_type_info.charset)),  # type: ignore[arg-type]
            )
            return
        text = (
            hexdump(response.body)
            if content_type_info.binary
            else response.body.decode(encoding=content_type_info.charset)  # type: ignore[arg-type]
        )
        txtarea = self.query_one("#preview-other", TextArea)
        txtarea.text = text
        txtarea.language = get_highlighter_language_by_content_type(content_type_info.content_type)
        self.query_one("#preview-switcher", ContentSwitcher).current = "preview-other"

    def update_payload(self, request: HTTPRequest):
        tree = self.query_one("#payload-tree", Tree)
        tree.clear()
        form_data_table = self.query_one("#payload-formdata", DataTable)
        form_data_table.clear()
        self.query_one("#payload-switcher", ContentSwitcher).current = "payload-tree"
        if not request.body:
            return
        content_type_info = parse_content_type(request.headers["Content-Type"])
        if content_type_info.content_type == "application/json":
            build_tree(
                tree.root,
                json.loads(request.body.decode(encoding=content_type_info.charset)),  # type: ignore[arg-type]
            )
            return
        if content_type_info.content_type == "multipart/form-data" and not request.body_truncated:
            for name, value in parse_form_data(request.body, content_type_info.boundary):  # type: ignore[arg-type]
                form_data_table.add_row(name, value)
            self.query_one("#payload-switcher", ContentSwitcher).current = "payload-formdata"
            return
        text = (
            hexdump(request.body)
            if content_type_info.binary
            else request.body.decode(encoding=content_type_info.charset)  # type: ignore[arg-type]
        )
        txtarea = self.query_one("#payload-other", TextArea)
        txtarea.text = text
        self.query_one("#payload-switcher", ContentSwitcher).current = "payload-other"

    def update_response(self, response: HTTPResponse):
        text_area = self.query_one("#raw-response", TextArea)
        text_area.clear()
        if response.body:
            content_type_info = parse_content_type(response.headers["Content-Type"])
            text = (
                hexdump(response.body)
                if content_type_info.binary
                else response.body.decode(encoding=content_type_info.charset)  # type: ignore[arg-type]
            )
            text_area.text = text
            text_area.language = get_highlighter_language_by_content_type(
                content_type_info.content_type
            )

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
        self.update_payload(response.request)
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
        form_data_table = self.query_one("#payload-formdata", DataTable)
        form_data_table.add_columns("Name", "Value")


class LeftPanel(Static):
    DEFAULT_CSS = """
    LeftPanel {
        layout: grid;
        grid-size: 1 3;
        grid-rows: 6 2fr 4fr;
        grid-columns: 1fr;
        background: black;
        height: 100%;
        width: 5fr;
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


class ProcessMetrics(Static):
    BORDER_TITLE = "Process"
    DEFAULT_CSS = """
    ProcessMetrics {
        border: round #00BBFF;
        layout: grid;
        grid-size: 1 2;
        grid-gutter: 0;
        height: 100%;
        align: center middle;
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
        self.mem_values: deque = deque([0] * 10, maxlen=10)
        self.cpu_values: deque = deque([0] * 10, maxlen=10)
        self.workers_metrics: dict[str, WorkerMetrics] = {}

    def compose(self) -> ComposeResult:
        yield ProcessInfoBar("CPU", id="cpu")
        yield ProcessInfoBar("Memory", id="mem")

    def on_mount(self) -> None:
        self.query_one("#cpu", ProcessInfoBar).update_value(0)
        self.query_one("#mem", ProcessInfoBar).update_value(0)

    def update_stats(self) -> None:
        cpu = mean([m.process.cpu for m in self.workers_metrics.values()])
        mem = mean([m.process.mem for m in self.workers_metrics.values()])

        self.query_one("#cpu", ProcessInfoBar).update_value(cpu)
        self.query_one("#mem", ProcessInfoBar).update_value(mem)

    def update_metrics(self, metrics: WorkerMetrics) -> None:
        self.workers_metrics[metrics.worker_id] = metrics
        self.update_stats()


class RequestsMetrics(Static):
    BORDER_TITLE = "Requests"
    DEFAULT_CSS = """
    RequestsMetrics {
        background: black;
        layout: grid;
        grid-size: 1 4;
        grid-gutter: 0;
        align-vertical: middle;
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
        self.update_stats()

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

    def update_metrics(self, metrics: WorkerMetrics) -> None:
        self.workers_metrics[metrics.worker_id] = metrics
        self.update_stats()


class DataTransferMetrics(Static):
    BORDER_TITLE = "Transfer"
    DEFAULT_CSS = """
    DataTransferMetrics {
        background: black;
        layout: grid;
        grid-size: 1 2;
        grid-gutter: 0;
        align-vertical: middle;
        border: round #0088FF;
        height: 100%;
        grid-rows: auto auto auto auto;
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
        yield Counter("In", id="in")
        yield Counter("Out", id="out")

    def on_mount(self) -> None:
        self.update_stats()

    def update_stats(self) -> None:
        amount, unit = humanize_bytes(
            sum(m.data_transfer.bytes_in for m in self.workers_metrics.values())
        )
        self.query_one("#in", Digits).border_title = f"In ({unit})"
        self.query_one("#in", Digits).update(str(amount))
        amount, unit = humanize_bytes(
            sum(m.data_transfer.bytes_out for m in self.workers_metrics.values())
        )
        self.query_one("#out", Digits).border_title = f"Out ({unit})"
        self.query_one("#out", Digits).update(str(amount))
        self.loading = False

    def update_metrics(self, metrics: WorkerMetrics) -> None:
        self.workers_metrics[metrics.worker_id] = metrics
        self.update_stats()


class RightPanel(Static):
    DEFAULT_CSS = """
    RightPanel {
        layout: grid;
        grid-size: 1 3;
        grid-rows: 1fr 22 12;
        grid-columns: 1fr;
        background: black;
        height: 100%;
        width: 33;
    }
    .hidden {
        display: none;
    }
    """

    def compose(self):
        yield ProcessMetrics()
        yield RequestsMetrics()
        yield DataTransferMetrics()


class TooSmallScreen(ModalScreen):
    CSS = """
    TooSmallScreen {
        align: center middle;
    }
    #dialog {
        grid-size: 1 3;
        grid-rows: 1fr 2fr 3;
        padding: 0 1;
        width: 60;
        height: 15;
        border: thick $background 80%;
        background: $surface;
    }
    #title {
        column-span: 1;
        height: 1fr;
        width: 1fr;
        content-align: center middle;
        background: $panel;
        color: $foreground;
        text-style: bold;
    }
    #message {
        margin-top: 1;
        column-span: 1;
        height: 1fr;
        width: 1fr;
        content-align: center top;
    }
    Button {
        width: 100%;
    }
    """

    def __init__(self):
        super().__init__()
        self.dialog_title = "Terminal too small"
        self.dialog_message = (
            f"Your current terminal size is {self.app.size.width}x{self.app.size.height}. "
            f"For the best experience please resize your terminal to {MIN_COLS}x{MIN_ROWS}."
        )
        self.btn_label = "dismiss"
        self.btn_variant = "primary"

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(self.dialog_title, id="title"),
            Label(self.dialog_message, id="message"),
            Button(self.btn_label, variant=self.btn_variant, id="dismiss"),
            id="dialog",
        )

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "dismiss":
            self.app.pop_screen()

    def update_message(self):
        self.query_one("#message", Label).content = (
            f"Your current terminal size is {self.app.size.width}x{self.app.size.height}. "
            f"For the best experience please resize your terminal to {MIN_COLS}x{MIN_ROWS}."
        )


class InspectorApp(App):
    TITLE = "mrok Dev Console"
    CSS = """
    Screen {
        background: black;
    }
    # Screen {
    #     layout: grid;
    #     grid-size: 2 1;
    #     grid-columns: 5fr 1fr;
    #     background: black;
    # }
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
    Tree {
        background: black;
    }
    TextArea {
        background: black;
    }
    RightPanel.-hidden {
        display: none;
    }
    """

    BINDINGS = [
        Binding("m", "toggle_metrics()", "Toggle Metrics"),
    ]

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
        with Horizontal():
            yield LeftPanel()
            yield RightPanel()

    async def on_mount(self):
        self._check_minimum_size(self.size.width, self.size.height)
        self.socket.subscribe("")
        self.consumer()

    async def on_unmount(self):
        self.socket.close()
        self.ctx.term()

    @work(exclusive=True)
    async def consumer(self):
        worker = get_current_worker()
        requests_table = self.query_one("#requests", DataTable)
        while not worker.is_cancelled:
            try:
                event = Event.model_validate_json(await self.socket.recv_string())
                if event.type == "status":
                    info_widget = self.query_one(InfoPanel)
                    info_widget.update_meta(event.data.meta)
                    process_metrics_widget = self.query_one(ProcessMetrics)
                    process_metrics_widget.update_metrics(event.data.metrics)
                    requests_metrics_widget = self.query_one(RequestsMetrics)
                    requests_metrics_widget.update_metrics(event.data.metrics)
                    data_transfer_metrics_widget = self.query_one(DataTransferMetrics)
                    data_transfer_metrics_widget.update_metrics(event.data.metrics)
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

    def action_toggle_metrics(self):
        self.query_one(RightPanel).toggle_class("-hidden")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if not event.row_key:
            return
        response = self.requests[event.row_key]
        details = self.query_one(Details)
        details.update_info(response)

    @on(Resize)
    def handle_resize(self, event: Resize):
        self._check_minimum_size(event.size.width, event.size.height)
        width = event.size.width
        table = self.query_one("#requests", DataTable)
        table.columns[ColumnKey("path")].width = width - 69

    def _check_minimum_size(self, width: int, height: int):
        if width < MIN_COLS or height < MIN_ROWS:
            if not isinstance(self.screen, TooSmallScreen):
                self.push_screen(TooSmallScreen())
            else:
                self.screen.update_message()
            return

        if isinstance(self.screen, TooSmallScreen):
            self.pop_screen()


def module_main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="mrok devtools agent")
    parser.add_argument(
        "-p",
        "--subscriber-port",
        type=int,
        default=50001,
        help="Port for subscriber (default: 50001)",
    )
    args = parser.parse_args(argv)
    app = InspectorApp(args.subscriber_port)
    app.run()
