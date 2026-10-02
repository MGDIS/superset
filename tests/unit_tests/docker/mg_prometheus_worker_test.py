# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
import sys
from collections import deque
from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parents[3] / "docker" / "gunicorn"))

from mg_prometheus_worker import (  # noqa: E402
    MgPrometheusThreadWorker,
    WORKER_BUSY_THREADS,
    WORKER_QUEUED_REQUESTS,
    WORKER_THREADS,
)

THREADS = 4


def gauge_value(metric, worker_id):
    return metric.labels(worker_id=worker_id)._value.get()


def running_future():
    future = Future()
    future.set_running_or_notify_cancel()
    return future


def done_future():
    future = running_future()
    future.set_result(None)
    return future


@pytest.fixture
def worker():
    thread_worker = MgPrometheusThreadWorker.__new__(MgPrometheusThreadWorker)
    thread_worker.cfg = SimpleNamespace(threads=THREADS)
    thread_worker.futures = deque()
    thread_worker.worker_id = "worker_test"
    return thread_worker


@pytest.mark.parametrize(
    "running_count, pending_count, done_count",
    [
        (0, 0, 0),
        (THREADS - 1, 0, 0),
        (THREADS, 0, 1),
        (THREADS, 5, 2),
    ],
)
def test_update_thread_pool_metrics_should_report_busy_threads_and_queued_requests(
    worker, running_count, pending_count, done_count
):
    worker.futures.extend(running_future() for _ in range(running_count))
    worker.futures.extend(Future() for _ in range(pending_count))
    worker.futures.extend(done_future() for _ in range(done_count))

    worker.update_thread_pool_metrics()

    assert gauge_value(WORKER_THREADS, worker.worker_id) == THREADS
    assert gauge_value(WORKER_BUSY_THREADS, worker.worker_id) == running_count
    assert gauge_value(WORKER_QUEUED_REQUESTS, worker.worker_id) == pending_count
