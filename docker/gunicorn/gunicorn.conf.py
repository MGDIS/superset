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
from gunicorn.arbiter import Arbiter
from gunicorn.workers.base import Worker
from gunicorn_prometheus_exporter.hooks import (
    default_on_exit,
    default_on_starting,
    default_post_fork,
    default_when_ready,
    default_worker_int,
)
from prometheus_client import multiprocess

pythonpath = "/app/docker/gunicorn"

on_starting = default_on_starting
when_ready = default_when_ready
post_fork = default_post_fork
worker_int = default_worker_int
on_exit = default_on_exit


def child_exit(server: Arbiter, worker: Worker) -> None:
    """Drop the liveall gauges of an exited worker so it stops being reported.

    :param server: Gunicorn arbiter
    :param worker: Exited worker
    """
    multiprocess.mark_process_dead(worker.pid)
