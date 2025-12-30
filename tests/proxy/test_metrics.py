import pytest
from pytest_mock import MockerFixture

from mrok.proxy.metrics import MetricsCollector, get_process_metrics
from mrok.proxy.models import ProcessMetrics


@pytest.mark.asyncio
async def test_get_process_metrics(
    mocker: MockerFixture,
):
    mocker.patch("mrok.proxy.metrics.os.getpid", return_value=1122)
    m_proc = mocker.MagicMock()
    m_proc.cpu_percent.side_effect = [Exception("oh"), 34.2]
    m_proc.memory_percent.return_value = 75.0
    m_proc_ctor = mocker.patch("mrok.proxy.metrics.psutil.Process", return_value=m_proc)

    metrics = await get_process_metrics(0.0001)
    assert metrics.cpu == 34.2
    assert metrics.mem == 75.0
    m_proc_ctor.assert_called_once_with(1122)


@pytest.mark.asyncio
async def test_worker_metrics_collector(
    mocker: MockerFixture,
):
    mocker.patch("mrok.proxy.metrics.time.perf_counter", side_effect=[0, 33, 75, 99])
    mocker.patch(
        "mrok.proxy.metrics.get_process_metrics", return_value=ProcessMetrics(cpu=7.3, mem=44.1)
    )
    collector = MetricsCollector("my-worker-id")
    begin = await collector.on_request_start({})
    await collector.on_request_body(23)
    await collector.on_request_body(32)
    await collector.on_response_start(200)
    await collector.on_response_chunk(11)
    await collector.on_response_chunk(13)
    await collector.on_request_end(begin, 200)

    begin = await collector.on_request_start({})
    await collector.on_request_body(11)
    await collector.on_request_body(4)
    await collector.on_response_start(500)
    await collector.on_request_end(begin, 500)

    snapshot = await collector.snapshot()

    assert snapshot.worker_id == "my-worker-id"
    assert snapshot.data_transfer.bytes_in == 70
    assert snapshot.data_transfer.bytes_out == 24
    assert snapshot.process.cpu == 7.3
    assert snapshot.process.mem == 44.1
    assert snapshot.requests.total == 2
    assert snapshot.requests.successful == 1
    assert snapshot.requests.failed == 1
    assert snapshot.requests.rps > 0
    assert snapshot.response_time.avg > 0
    assert snapshot.response_time.max > 0
    assert snapshot.response_time.min > 0
    assert snapshot.response_time.p50 > 0
    assert snapshot.response_time.p90 > 0
    assert snapshot.response_time.p99 > 0
