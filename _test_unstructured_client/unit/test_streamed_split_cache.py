"""Cached split response ownership, retry and cancellation regressions."""
import asyncio
import io
import gzip
import threading
from pathlib import Path

import httpx
import pytest

from unstructured_client._hooks.custom import request_utils as ru
from unstructured_client._hooks.custom import split_pdf_hook as hook_module
from unstructured_client._hooks.custom.split_pdf_hook import SplitPdfHook


class Body(httpx.AsyncByteStream):
    def __init__(self, chunks=(), error=None, gate=None):
        self.chunks = chunks
        self.error = error
        self.gate = gate
        self.closed = False

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk
        if self.gate is not None:
            await self.gate.wait()
        if self.error is not None:
            raise self.error

    async def aclose(self):
        self.closed = True


def policy(retry=False):
    return ru.RetryConfig(
        "backoff" if retry else "none",
        ru.BackoffStrategy(1, 1, 1, 5, min_attempts=2, absolute_max_elapsed_time_ms=1000),
        True,
    )


async def call(client, directory, *, retry=False, limiter=None, source=None):
    return await ru.call_api_async(
        client, httpx.Request("POST", "https://example.test/partition", content=b"input"),
        source if source is not None else io.BytesIO(b"input"),
        limiter if limiter is not None else asyncio.Semaphore(1),
        retry_config=policy(retry), cache_response_dir=str(directory) if directory else None,
    )


@pytest.mark.asyncio
async def test_cached_response_preserves_bytes_and_path_contract(tmp_path):
    payload = b'{"text":"caf\xc3\xa9"}\n' + b'x' * 150000
    body = Body([payload[:17], payload[17:]])
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, stream=body, headers={"Content-Type": "application/x-ndjson"})
    )) as client:
        response = await call(client, tmp_path)
    assert Path(response.text).read_bytes() == payload
    assert body.closed
    assert len(list(tmp_path.iterdir())) == 1
    assert not list(tmp_path.glob("*.partial"))
    # A server-provided content-type does not mint the SDK's trusted final-file marker.
    assert ru.ELEMENTS_FILE_EXTENSION_KEY not in response.extensions


@pytest.mark.asyncio
async def test_noncached_response_stays_buffered(tmp_path):
    body = Body([b"one", b"two"])
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, stream=body)
    )) as client:
        response = await call(client, None)
    assert response.content == b"onetwo"
    assert body.closed
    assert not list(tmp_path.iterdir())


@pytest.mark.asyncio
async def test_body_retry_uses_fresh_partial_and_closes_each_response(tmp_path):
    bodies = []
    observed = []
    def handler(request):
        observed.append(list(tmp_path.iterdir()))
        body = Body([b"partial"], httpx.ReadError("broken")) if not bodies else Body([b"complete"])
        bodies.append(body)
        return httpx.Response(200, stream=body)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        response = await call(client, tmp_path, retry=True)
    assert len(bodies) == 2
    assert observed == [[], []]
    assert all(body.closed for body in bodies)
    assert Path(response.text).read_bytes() == b"complete"
    assert len(list(tmp_path.iterdir())) == 1


@pytest.mark.asyncio
async def test_persistent_body_failure_leaves_no_cache(tmp_path):
    bodies = []
    def handler(request):
        body = Body([b"partial"], httpx.ReadTimeout("stalled"))
        bodies.append(body)
        return httpx.Response(200, stream=body)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.ReadTimeout):
            await call(client, tmp_path, retry=True)
    assert len(bodies) >= 2
    assert all(body.closed for body in bodies)
    assert not list(tmp_path.iterdir())


@pytest.mark.asyncio
async def test_cancellation_settles_repeatedly_cancelled_write_before_cleanup(tmp_path, monkeypatch):
    current = asyncio.current_task()
    all_tasks = asyncio.all_tasks
    monkeypatch.setattr(hook_module.asyncio, "all_tasks", lambda: all_tasks() - {current})
    entered, release = threading.Event(), threading.Event()
    original = ru._write_all
    def slow_write(file, content):
        entered.set()
        assert release.wait(3)
        original(file, content)
    monkeypatch.setattr(ru, "_write_all", slow_write)
    body = Body([b"x" * 65536])
    limiter = asyncio.Semaphore(1)
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, stream=body)
    )) as client:
        task = asyncio.create_task(call(client, tmp_path, limiter=limiter))
        try:
            assert await asyncio.to_thread(entered.wait, 2)
            hook_module._cancel_running_tasks()
            await asyncio.sleep(0)
            hook_module._cancel_running_tasks()
            await asyncio.sleep(0)
            assert not task.done()
            assert limiter.locked()
            assert list(tmp_path.glob("*.partial"))
        finally:
            release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert body.closed
    assert not limiter.locked()
    assert not list(tmp_path.iterdir())


@pytest.mark.asyncio
async def test_disk_failure_is_not_network_retried(tmp_path, monkeypatch):
    bodies = []
    def handler(request):
        body = Body([b"content"])
        bodies.append(body)
        return httpx.Response(200, stream=body)
    def failed_write(file, content):
        raise OSError("disk full")
    monkeypatch.setattr(ru, "_write_all", failed_write)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(OSError, match="disk full"):
            await call(client, tmp_path, retry=True)
    assert len(bodies) == 1
    assert bodies[0].closed
    assert not list(tmp_path.iterdir())


@pytest.mark.asyncio
async def test_file_close_failure_cannot_publish(tmp_path, monkeypatch):
    original = ru.os.fdopen
    class FailedClose:
        def __init__(self, file): self.file = file
        @property
        def closed(self): return self.file.closed
        def write(self, data): return self.file.write(data)
        def close(self):
            self.file.close()
            raise OSError("close failed")
    monkeypatch.setattr(ru.os, "fdopen", lambda *a, **kw: FailedClose(original(*a, **kw)))
    body = Body([b"content"])
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, stream=body)
    )) as client:
        with pytest.raises(OSError, match="close failed"):
            await call(client, tmp_path)
    assert body.closed
    assert not list(tmp_path.iterdir())


@pytest.mark.asyncio
async def test_response_close_failure_cannot_publish(tmp_path):
    class FailedClose(Body):
        async def aclose(self):
            self.closed = True
            raise OSError("response close failed")
    body = FailedClose([b"content"])
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, stream=body)
    )) as client:
        with pytest.raises(OSError, match="response close failed"):
            await call(client, tmp_path)
    assert body.closed
    assert not list(tmp_path.iterdir())


@pytest.mark.asyncio
@pytest.mark.parametrize("retry", [False, True])
async def test_503_body_readable_and_retry_unchanged(tmp_path, retry):
    bodies = []
    def handler(request):
        status = 503 if not bodies else 200
        body = Body([b"try later" if status == 503 else b"done"])
        bodies.append(body)
        return httpx.Response(status, stream=body)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        response = await call(client, tmp_path, retry=retry)
    if retry:
        assert len(bodies) == 2
        assert Path(response.text).read_bytes() == b"done"
    else:
        assert response.status_code == 503
        assert response.content == b"try later"
        assert not list(tmp_path.iterdir())
    assert all(body.closed for body in bodies)


@pytest.mark.asyncio
async def test_admission_is_held_until_body_and_cache_write_finish(tmp_path, monkeypatch):
    gate = asyncio.Event()
    body = Body([b"a" * 65536], gate=gate)
    entered, release = threading.Event(), threading.Event()
    original = ru._write_all
    def slow_write(file, content):
        entered.set()
        assert release.wait(3)
        original(file, content)
    monkeypatch.setattr(ru, "_write_all", slow_write)
    limiter = asyncio.Semaphore(1)
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, stream=body)
    )) as client:
        task = asyncio.create_task(call(client, tmp_path, limiter=limiter))
        try:
            assert await asyncio.to_thread(entered.wait, 2)
            assert limiter.locked()
            release.set()
            await asyncio.sleep(0)
            assert limiter.locked()
            gate.set()
            result = await task
        finally:
            release.set()
            gate.set()
    assert not limiter.locked()
    assert Path(result.text).read_bytes() == b"a" * 65536


@pytest.mark.asyncio
async def test_hook_cached_operations_keep_separate_paths_and_close_input(tmp_path):
    hook = SplitPdfHook()
    dirs = [tmp_path / "one", tmp_path / "two"]
    for directory in dirs: directory.mkdir()
    sources = [open(tmp_path / f"input-{i}", "w+b") for i in range(2)]
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, stream=Body([request.content]))
    )) as client:
        results = await asyncio.gather(*(hook.call_api_partial(
            pdf_chunk_request=httpx.Request("POST", "https://example.test", content=str(i).encode()),
            pdf_chunk_file=sources[i], limiter=asyncio.Semaphore(1), _operation_id=str(i),
            chunk_index=1, page_number=1, async_client=client, retry_config=policy(),
            cache_tmp_data_feature=True, temp_dir_path=str(dirs[i]),
        ) for i in range(2)))
    assert [Path(r.text).read_bytes() for r in results] == [b"0", b"1"]
    assert all(source.closed for source in sources)
    assert all(Path(result.text).parent == directory for result, directory in zip(results, dirs))


@pytest.mark.asyncio
async def test_missing_cache_directory_closes_owned_input_without_request(tmp_path):
    hook = SplitPdfHook()
    source = open(tmp_path / "input", "w+b")
    def unexpected_request(request):
        raise AssertionError("invalid cache directory must fail before send")
    async with httpx.AsyncClient(transport=httpx.MockTransport(unexpected_request)) as client:
        with pytest.raises(RuntimeError, match="Temp directory"):
            await hook.call_api_partial(
                pdf_chunk_request=httpx.Request("POST", "https://example.test"),
                pdf_chunk_file=source, limiter=asyncio.Semaphore(1), _operation_id="missing",
                chunk_index=1, page_number=1, async_client=client, retry_config=policy(),
                cache_tmp_data_feature=True, temp_dir_path=None,
            )
    assert source.closed


@pytest.mark.asyncio
async def test_cancellation_during_httpx_automatic_close_settles_before_cleanup(tmp_path, monkeypatch):
    current = asyncio.current_task()
    all_tasks = asyncio.all_tasks
    monkeypatch.setattr(hook_module.asyncio, "all_tasks", lambda: all_tasks() - {current})
    entered = asyncio.Event()
    release = asyncio.Event()
    class SlowClose(Body):
        async def aclose(self):
            entered.set()
            await release.wait()
            self.closed = True
    body = SlowClose([b"content"])
    limiter = asyncio.Semaphore(1)
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, stream=body)
    )) as client:
        task = asyncio.create_task(call(client, tmp_path, limiter=limiter))
        await asyncio.wait_for(entered.wait(), 2)
        hook_module._cancel_running_tasks()
        await asyncio.sleep(0)
        hook_module._cancel_running_tasks()
        await asyncio.sleep(0)
        assert not task.done()
        assert limiter.locked()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert body.closed
    assert not list(tmp_path.iterdir())
    assert not limiter.locked()


@pytest.mark.asyncio
async def test_compressed_cached_response_decodes_entity_only(tmp_path):
    payload = b'{"text":"hello"}\n'
    body = Body([gzip.compress(payload)])
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, stream=body, headers={"Content-Encoding": "gzip"})
    )) as client:
        response = await call(client, tmp_path)
    assert Path(response.text).read_bytes() == payload
    assert "content-encoding" not in response.headers


@pytest.mark.asyncio
async def test_cleanup_close_error_preserves_body_retry(tmp_path, monkeypatch):
    original = ru.os.fdopen
    opened = []
    class FailedClose:
        def __init__(self, file):
            self.file = file
        @property
        def closed(self):
            return self.file.closed
        def write(self, content):
            return self.file.write(content)
        def close(self):
            self.file.close()
            raise OSError("secondary close failure")
    def fdopen(*args, **kwargs):
        file = original(*args, **kwargs)
        opened.append(file)
        return FailedClose(file) if len(opened) == 1 else file
    monkeypatch.setattr(ru.os, "fdopen", fdopen)
    bodies = []
    def handler(request):
        body = Body([b"partial"], httpx.ReadError("broken")) if not bodies else Body([b"complete"])
        bodies.append(body)
        return httpx.Response(200, stream=body)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        response = await call(client, tmp_path, retry=True)
    assert len(bodies) == 2
    assert all(body.closed for body in bodies)
    assert Path(response.text).read_bytes() == b"complete"
    assert not list(tmp_path.glob("*.partial"))


@pytest.mark.asyncio
async def test_failed_publication_cleans_reserved_final_and_keeps_existing_artifact(tmp_path, monkeypatch):
    existing = tmp_path / "existing.json"
    existing.write_bytes(b"previous result")
    body = Body([b"new result"])
    def failed_replace(source, destination):
        assert Path(destination).exists()
        assert Path(destination) != existing
        raise OSError("publication failure")
    monkeypatch.setattr(ru.os, "replace", failed_replace)
    async with httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, stream=body)
    )) as client:
        with pytest.raises(OSError, match="publication failure"):
            await call(client, tmp_path, retry=True)
    assert body.closed
    assert list(tmp_path.iterdir()) == [existing]
    assert existing.read_bytes() == b"previous result"
