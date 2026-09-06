#!/usr/bin/env bash
# 追踪接入的环境前置：四个变量 + 代理绕过，缺一条上报会静默失败。
# 用法： source langfuse-env.sh [HOST]     默认 HOST=http://localhost:3000
# 公私钥从环境读，未设则用自托管部署时预置的那对。

HOST="${1:-http://localhost:3000}"

export LANGFUSE_PUBLIC_KEY="${LANGFUSE_PUBLIC_KEY:-pk-lf-course-demo-public}"
export LANGFUSE_SECRET_KEY="${LANGFUSE_SECRET_KEY:-sk-lf-course-demo-secret}"
export LANGFUSE_HOST="$HOST"
# v4 SDK 底层走 OpenTelemetry 上报，漏设此项调用链产生了也导不到后端
export OTEL_EXPORTER_OTLP_ENDPOINT="$HOST/api/public/otel"
# 本机有系统代理时，不绕过会导致连接超时
export NO_PROXY="localhost,127.0.0.1"

echo "LANGFUSE_HOST            = $LANGFUSE_HOST"
echo "OTEL_EXPORTER_OTLP_ENDPOINT = $OTEL_EXPORTER_OTLP_ENDPOINT"
echo "NO_PROXY                 = $NO_PROXY"
echo "LANGFUSE_PUBLIC_KEY      = ${LANGFUSE_PUBLIC_KEY:0:6}***"
echo "LANGFUSE_SECRET_KEY      = ${LANGFUSE_SECRET_KEY:0:6}***"
