#!/usr/bin/env bash
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
HYPHEN_SYMBOL='-'

GUNICORN_EXTRA_ARGS=()
WORKER_CLASS="${SERVER_WORKER_CLASS:-gthread}"
if [ "${GUNICORN_PROMETHEUS_ENABLED:-false}" = "true" ]; then
    export PROMETHEUS_METRICS_PORT="${PROMETHEUS_METRICS_PORT:-9091}"
    export PROMETHEUS_BIND_ADDRESS="${PROMETHEUS_BIND_ADDRESS:-0.0.0.0}"
    export PROMETHEUS_MULTIPROC_DIR="${PROMETHEUS_MULTIPROC_DIR:-/tmp/prometheus_multiproc}"
    export GUNICORN_WORKERS="${SERVER_WORKER_AMOUNT:-1}"
    # Metric files of a previous run would be reported as live workers after a container restart
    rm -rf "${PROMETHEUS_MULTIPROC_DIR}"
    mkdir -p "${PROMETHEUS_MULTIPROC_DIR}"
    GUNICORN_EXTRA_ARGS=(--config /app/docker/gunicorn/gunicorn.conf.py)
    WORKER_CLASS="${SERVER_WORKER_CLASS:-mg_prometheus_worker.MgPrometheusThreadWorker}"
fi

gunicorn \
    "${GUNICORN_EXTRA_ARGS[@]}" \
    --bind "${SUPERSET_BIND_ADDRESS:-0.0.0.0}:${SUPERSET_PORT:-8088}" \
    --access-logfile "${ACCESS_LOG_FILE:-$HYPHEN_SYMBOL}" \
    --error-logfile "${ERROR_LOG_FILE:-$HYPHEN_SYMBOL}" \
    --workers ${SERVER_WORKER_AMOUNT:-1} \
    --worker-class ${WORKER_CLASS} \
    --threads ${SERVER_THREADS_AMOUNT:-20} \
    --log-level "${GUNICORN_LOGLEVEL:info}" \
    --timeout ${GUNICORN_TIMEOUT:-60} \
    --keep-alive ${GUNICORN_KEEPALIVE:-2} \
    --max-requests ${WORKER_MAX_REQUESTS:-0} \
    --max-requests-jitter ${WORKER_MAX_REQUESTS_JITTER:-0} \
    --limit-request-line ${SERVER_LIMIT_REQUEST_LINE:-0} \
    --limit-request-field_size ${SERVER_LIMIT_REQUEST_FIELD_SIZE:-0} \
    "${FLASK_APP}"
