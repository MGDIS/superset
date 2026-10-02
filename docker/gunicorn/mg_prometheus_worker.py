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
from gunicorn_prometheus_exporter import PrometheusThreadWorker
from prometheus_client import Gauge

WORKER_THREADS = Gauge(
    "gunicorn_worker_threads",
    "Size of the worker thread pool",
    ["worker_id"],
    multiprocess_mode="liveall",
)
WORKER_BUSY_THREADS = Gauge(
    "gunicorn_worker_busy_threads",
    "Threads currently processing a request",
    ["worker_id"],
    multiprocess_mode="liveall",
)
WORKER_QUEUED_REQUESTS = Gauge(
    "gunicorn_worker_queued_requests",
    "Connections waiting for a free thread",
    ["worker_id"],
    multiprocess_mode="liveall",
)


class MgPrometheusThreadWorker(PrometheusThreadWorker):
    """Thread worker exporting thread pool occupancy on top of the exporter metrics."""

    def notify(self) -> None:
        """Refresh the thread pool gauges on each iteration of the worker main loop."""
        super().notify()
        self.update_thread_pool_metrics()

    def update_thread_pool_metrics(self) -> None:
        """Set the thread pool gauges from the connections submitted to the pool."""
        submitted_connections = list(self.futures)
        busy_threads = sum(1 for future in submitted_connections if future.running())
        queued_requests = sum(
            1
            for future in submitted_connections
            if not future.running() and not future.done()
        )
        WORKER_THREADS.labels(worker_id=self.worker_id).set(self.cfg.threads)
        WORKER_BUSY_THREADS.labels(worker_id=self.worker_id).set(busy_threads)
        WORKER_QUEUED_REQUESTS.labels(worker_id=self.worker_id).set(queued_requests)
