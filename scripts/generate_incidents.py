from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "incidents"


@dataclass
class Scenario:
    root_cause: str
    action: str
    alert_templates: list[str]
    log_templates: list[list[str]]
    mttr_range: tuple[float, float]


def render_logs(lines: list[str], pod: str, ns: str) -> str:
    rendered = []
    for line in lines:
        try:
            rendered.append(line.format(pod=pod, ns=ns))
        except (KeyError, ValueError):
            rendered.append(line)
    return "\n".join(rendered)


def add_noise(lines: list[str], pod: str, ns: str, count: int) -> list[str]:
    noise_pool = [
        "2026-02-05T09:00:01.001Z {pod} app[1]: INFO request_id=af2c latency_ms=12 status=200",
        "2026-02-05T09:00:01.120Z {pod} app[1]: INFO cache hit key=user:18491",
        "2026-02-05T09:00:02.241Z {pod} app[1]: DEBUG feature_flag=checkout_v2 enabled=true",
        "2026-02-05T09:00:02.555Z {pod} envoy: http2: stream closed (NO_ERROR)",
        "2026-02-05T09:00:03.881Z {pod} app[1]: INFO db query ok rows=42",
        "2026-02-05T09:00:05.313Z {pod} app[1]: INFO healthcheck passed",
        "2026-02-05T09:00:06.044Z {pod} kubelet: Container {pod} readiness probe succeeded",
        "2026-02-05T09:00:06.812Z {pod} app[1]: INFO background job completed id=job-9122",
        "2026-02-05T09:00:07.512Z {pod} app[1]: INFO write path latency_ms=18",
        "2026-02-05T09:00:08.114Z {pod} app[1]: DEBUG retries=0",
    ]
    noise = random.sample(noise_pool, k=min(count, len(noise_pool)))
    return [n.format(pod=pod, ns=ns) for n in noise] + lines


def add_structured_logs(lines: list[str], pod: str, ns: str, count: int) -> list[str]:
    templates = [
        {
            "ts": "2026-02-05T09:00:09.310Z",
            "level": "INFO",
            "msg": "request completed",
            "http": {"method": "GET", "path": "/v1/items", "status": 200, "latency_ms": 14},
            "trace_id": "f1a2b3c4d5",
        },
        {
            "ts": "2026-02-05T09:00:10.011Z",
            "level": "WARN",
            "msg": "retrying upstream",
            "upstream": "search-indexer",
            "attempt": 1,
            "trace_id": "a8b7c6d5e4",
        },
        {
            "ts": "2026-02-05T09:00:11.221Z",
            "level": "ERROR",
            "msg": "timeout contacting upstream",
            "upstream": "payments-db",
            "timeout_ms": 2000,
            "trace_id": "9f8e7d6c5b",
        },
    ]
    chosen = random.sample(templates, k=min(count, len(templates)))
    rendered = []
    for entry in chosen:
        entry = dict(entry)
        entry["pod"] = pod
        entry["namespace"] = ns
        rendered.append(json.dumps(entry))
    return rendered + lines


def alert_prometheus(base: str, ns: str, pod: str, severity: str, alertname: str) -> str:
    return (
        f"ALERT {alertname} severity={severity} namespace={ns} pod={pod} "
        f"summary=\"{base}\""
    )


def main() -> None:
    random.seed(7)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    scenarios = [
        Scenario(
            root_cause="pod_memory_oom",
            action="increase_memory_limit",
            alert_templates=[
                "High restart count on {pod} in {ns}",
                "OOMKills detected for {pod} ({ns})",
            ],
            log_templates=[
                [
                    "2026-02-05T09:14:22.118Z {pod} kernel: Memory cgroup out of memory: Kill process 9821 (app) score 982 or sacrifice child",
                    "2026-02-05T09:14:22.119Z {pod} kernel: Killed process 9821 (app) total-vm:2147483648kB, anon-rss:812344kB",
                    "2026-02-05T09:14:22.121Z {pod} kubelet: Container {pod} in {ns} was OOMKilled",
                    "2026-02-05T09:14:23.411Z {pod} app[1]: Fatal: out of memory while allocating 128MB buffer",
                    "2026-02-05T09:14:23.512Z {pod} app[1]: stacktrace: MemoryError at allocator.cc:147",
                ],
                [
                    "2026-02-05T09:18:09.009Z {pod} app[1]: ERROR fatal error: runtime: out of memory",
                    "2026-02-05T09:18:09.010Z {pod} app[1]: goroutine 2241 [running]:",
                    "2026-02-05T09:18:09.012Z {pod} app[1]: main.(*Cache).Allocate(0xc000a2f4f0, 0x8000000)",
                    "2026-02-05T09:18:09.015Z {pod} kubelet: Container {pod} in {ns} terminated with exit code 137",
                ],
            ],
            mttr_range=(6.0, 12.0),
        ),
        Scenario(
            root_cause="disk_full",
            action="clear_disk",
            alert_templates=[
                "Node disk pressure on {ns} worker",
                "Pod scheduling failures due to disk pressure in {ns}",
            ],
            log_templates=[
                [
                    "2026-02-05T10:02:09.772Z kubelet: eviction manager: must evict pod(s) to reclaim ephemeral-storage",
                    "2026-02-05T10:02:11.022Z {pod} kubelet: Error: failed to create pod sandbox: rpc error: code = Unknown desc = failed to create containerd task: no space left on device",
                    "2026-02-05T10:02:11.045Z {pod} containerd: failed to create temp dir /var/lib/containerd/tmp: no space left on device",
                ],
                [
                    "2026-02-05T10:05:22.901Z {pod} kubelet: Image garbage collection failed: failed to delete image",
                    "2026-02-05T10:05:23.011Z {pod} kubelet: DiskPressure=true; available 1.2Gi",
                    "2026-02-05T10:05:23.121Z {pod} containerd: write /var/lib/containerd/io.containerd.content.v1.content/blobs: no space left on device",
                ],
            ],
            mttr_range=(9.0, 14.0),
        ),
        Scenario(
            root_cause="dns_failure",
            action="flush_dns_cache",
            alert_templates=[
                "DNS resolution failures for {pod}",
                "NXDOMAIN spike for service discovery in {ns}",
            ],
            log_templates=[
                [
                    "2026-02-05T11:18:45.608Z {pod} app[1]: error: dial tcp: lookup payments-db on 10.96.0.10:53: no such host",
                    "2026-02-05T11:18:45.609Z {pod} app[1]: retrying in 1000ms",
                    "2026-02-05T11:18:46.612Z {pod} app[1]: error: DNS query failed (NXDOMAIN)",
                    "2026-02-05T11:18:50.010Z coredns: [ERROR] plugin/errors: 2 payments-db.default.svc.cluster.local. A: read udp 10.96.0.10:53: i/o timeout",
                ],
                [
                    "2026-02-05T11:22:30.122Z {pod} app[1]: lookup auth-service.default.svc.cluster.local: no such host",
                    "2026-02-05T11:22:30.221Z coredns: [ERROR] plugin/errors: 2 auth-service.default.svc.cluster.local. A: read udp 10.96.0.10:53: i/o timeout",
                ],
            ],
            mttr_range=(5.0, 9.0),
        ),
        Scenario(
            root_cause="bad_config",
            action="roll_back_config",
            alert_templates=[
                "Config rollout caused errors for {pod}",
                "Invalid config detected in {ns}",
            ],
            log_templates=[
                [
                    "2026-02-05T12:03:12.202Z {pod} app[1]: config validation failed: missing required field 'timeout_ms'",
                    "2026-02-05T12:03:12.203Z {pod} app[1]: startup aborted",
                    "2026-02-05T12:03:13.114Z {pod} kubelet: Container {pod} in {ns} terminated with exit code 1",
                ],
                [
                    "2026-02-05T12:08:01.501Z {pod} app[1]: ERROR invalid value for 'retries': -1",
                    "2026-02-05T12:08:01.502Z {pod} app[1]: config schema validation failed",
                ],
            ],
            mttr_range=(7.0, 12.0),
        ),
        Scenario(
            root_cause="cpu_spike",
            action="scale_deployment",
            alert_templates=[
                "CPU saturation on {pod}",
                "HPA throttling disabled; CPU > 90% in {ns}",
            ],
            log_templates=[
                [
                    "2026-02-05T13:44:02.112Z {pod} app[1]: latency p95=920ms; qps=1800",
                    "2026-02-05T13:44:02.113Z {pod} app[1]: cpu usage 96% for 8m",
                    "2026-02-05T13:44:05.771Z {pod} kubelet: CPU throttling detected; cfs_quota_us=100000",
                ],
                [
                    "2026-02-05T13:49:11.900Z {pod} app[1]: WARN request backlog increasing; queue_depth=820",
                    "2026-02-05T13:49:12.102Z {pod} app[1]: cpu usage 92% for 5m",
                ],
            ],
            mttr_range=(6.0, 11.0),
        ),
        Scenario(
            root_cause="service_unavailable",
            action="restart_deployment",
            alert_templates=[
                "5xx error rate above 20% for {pod}",
                "Upstream connection failures for {pod}",
            ],
            log_templates=[
                [
                    "2026-02-05T14:22:35.980Z {pod} envoy: upstream connect error or disconnect/reset before headers. reset reason: connection failure",
                    "2026-02-05T14:22:36.012Z {pod} app[1]: ReadTimeout: downstream search-indexer timed out",
                    "2026-02-05T14:22:37.031Z {pod} app[1]: error: connection refused to http://indexer:9200",
                ],
                [
                    "2026-02-05T14:28:03.110Z {pod} app[1]: ERROR upstream closed connection before response headers",
                    "2026-02-05T14:28:04.221Z {pod} app[1]: WARN retrying upstream after 502",
                ],
            ],
            mttr_range=(5.0, 10.0),
        ),
    ]

    pods = [
        "payments-api-6b8c4f7d7c-4t2hx",
        "checkout-79c9d65c89-qt4sk",
        "search-api-5b4c7cd6c8-9m5qk",
        "recommendation-6c7c6c69b4-8qz9p",
        "orders-7f6c8b9cd8-j2l4m",
        "auth-6bb9c7f8c9-v8l2x",
        "inventory-5b6dbf7cdb-h7m5w",
        "profile-7c5d6b7d66-r2d8h",
    ]
    namespaces = ["default", "prod", "payments", "checkout", "search"]
    alertnames = {
        "pod_memory_oom": "PodOOMKilled",
        "disk_full": "NodeDiskPressure",
        "dns_failure": "DNSFailure",
        "bad_config": "ConfigInvalid",
        "cpu_spike": "CPUSaturation",
        "service_unavailable": "Service5xx",
    }

    count = 32
    for idx in range(count):
        scenario = random.choice(scenarios)
        pod = random.choice(pods)
        ns = random.choice(namespaces)
        alert_base = random.choice(scenario.alert_templates).format(pod=pod, ns=ns)
        alert = alert_prometheus(
            base=alert_base,
            ns=ns,
            pod=pod,
            severity=random.choice(["warning", "critical"]),
            alertname=alertnames[scenario.root_cause],
        )
        log_lines = random.choice(scenario.log_templates)
        noisy_lines = add_noise(log_lines, pod=pod, ns=ns, count=random.randint(3, 6))
        structured_lines = add_structured_logs(noisy_lines, pod=pod, ns=ns, count=random.randint(1, 3))
        logs = render_logs(structured_lines, pod=pod, ns=ns)
        mttr = round(random.uniform(*scenario.mttr_range), 1)

        incident = {
            "id": f"gen-{idx+1:03d}",
            "alert": alert,
            "logs": logs,
            "expected_root_cause": scenario.root_cause,
            "expected_action": scenario.action,
            "mttr_baseline_minutes": mttr,
        }
        (OUT_DIR / f"gen_{idx+1:03d}.json").write_text(
            json.dumps(incident, indent=2),
            encoding="utf-8",
        )

    print(f"Generated {count} incidents in {OUT_DIR}")


if __name__ == "__main__":
    main()
