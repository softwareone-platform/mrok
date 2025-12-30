from __future__ import annotations

import asyncio
import logging
import os
import time

import psutil
from hdrh.histogram import HdrHistogram

from mrok.proxy.models import (
    DataTransferMetrics,
    ProcessMetrics,
    RequestsMetrics,
    ResponseTimeMetrics,
    WorkerMetrics,
)

logger = logging.getLogger("mrok.proxy")


def _collect_process_usage(interval: float) -> ProcessMetrics:
    proc = psutil.Process(os.getpid())
    total_cpu = 0.0
    total_mem = 0.0

    try:
        total_cpu = proc.cpu_percent(None)
    except Exception:
        total_cpu = 0.0

    if interval and interval > 0:  # pragma: no branch
        time.sleep(interval)

    try:
        total_cpu = proc.cpu_percent(None)
    except Exception:  # pragma: no cover
        total_cpu = 0.0

    try:
        total_mem = proc.memory_percent()
    except Exception:  # pragma: no cover
        total_mem = 0.0

    return ProcessMetrics(cpu=total_cpu, mem=total_mem)


async def get_process_metrics(interval: float = 0.1) -> ProcessMetrics:
    return await asyncio.to_thread(_collect_process_usage, interval)


class MetricsCollector:
    def __init__(self, worker_id: str, lowest=1, highest=60000, sigfigs=3):
        self.worker_id = worker_id
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.bytes_in = 0
        self.bytes_out = 0

        self._tick_last = time.time()
        self._tick_requests = 0

        self.hist = HdrHistogram(lowest, highest, sigfigs)

        self._lock = asyncio.Lock()

    async def on_request_start(self, scope):
        return time.perf_counter()

    async def on_request_body(self, length):
        async with self._lock:
            self.bytes_in += length

    async def on_response_start(self, status_code):
        pass  # reserved

    async def on_response_chunk(self, length):
        async with self._lock:
            self.bytes_out += length

    async def on_request_end(self, start_time, status_code):
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        async with self._lock:
            self.total_requests += 1
            self._tick_requests += 1

            if status_code < 500:
                self.successful_requests += 1
            else:
                self.failed_requests += 1

            self.hist.record_value(elapsed_ms)

    async def snapshot(self) -> WorkerMetrics:
        async with self._lock:
            now = time.time()
            delta = now - self._tick_last
            rps = int(self._tick_requests / delta) if delta > 0 else 0
            data = WorkerMetrics(
                worker_id=self.worker_id,
                process=await get_process_metrics(),
                requests=RequestsMetrics(
                    rps=rps,
                    total=self.total_requests,
                    successful=self.successful_requests,
                    failed=self.failed_requests,
                ),
                data_transfer=DataTransferMetrics(
                    bytes_in=self.bytes_in,
                    bytes_out=self.bytes_out,
                ),
                response_time=ResponseTimeMetrics(
                    avg=self.hist.get_mean_value(),
                    min=self.hist.get_min_value(),
                    max=self.hist.get_max_value(),
                    p50=self.hist.get_value_at_percentile(50),
                    p90=self.hist.get_value_at_percentile(90),
                    p99=self.hist.get_value_at_percentile(99),
                ),
            )

            self._tick_last = now
            self._tick_requests = 0

            return data
