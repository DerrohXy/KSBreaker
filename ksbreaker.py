#!/opt/ksbreaker/venv/bin/python3

import logging
import subprocess
import time
from collections import deque
from typing import Any
import os
import psutil
import json
from datetime import datetime


def get_process_exe(pid: int) -> str:
    exe = f"/proc/{pid}/exe"
    try:
        return os.readlink(exe)
    except Exception as e:
        logging.error(f"Error getting process *exe* : {e}")
        return "--UNKNOWN--"


def generate_incident_report_attachment_bundle(
    stats: dict[str, Any],
    cpu_avg: float,
    cpu_now: float,
) -> str:
    path = f"/var/log/ksbreaker/incident-{datetime.now().isoformat()}.json"
    bundle = {
        "timestamp": time.time(),
        "cpu_current": cpu_now,
        "cpu_average": cpu_avg,
        "system": stats.get("system"),
        "processes": stats.get("processes"),
    }

    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w") as f:
        json.dump(bundle, f, indent=2)

    return path


def send_incident_report_alert(
    stats,
    cpu_avg: float,
    cpu_now: float,
) -> None:
    """
    Relies on "tmail" util, if installed
    :param stats:
    :param cpu_avg:
    :param cpu_now:
    :return:
    """
    attachment_path = generate_incident_report_attachment_bundle(
        stats, cpu_avg, cpu_now
    )

    system = stats["system"]
    top_procs = stats.get("processes", [])[:5]

    process_summary = "\n".join(
        [
            f"PID={p['pid']} "
            f"NAME={p.get('name')} "
            f"CPU={p.get('cpu_percent')}% "
            f"MEM={p.get('memory_percent')}% "
            f"EXE={p.get('exe')}"
            for p in top_procs
        ]
    )

    message = f"""
SERVER BREAKER ALERT

CPU current: {cpu_now:.2f}%
CPU average: {cpu_avg:.2f}%
Memory: {system['memory']['percent']:.2f}%

Top processes:
{process_summary}

Full incident report attached if available.
"""

    cmd = [
        "tmail",
        "send",
        "--subject",
        "SERVER EXHAUSTION ALERT - AUTO REBOOT INITIATED",
        "--message",
        message,
        "--to",
        "SELF",
    ]

    if attachment_path:
        cmd.extend(["--file", attachment_path])

    subprocess.run(cmd, check=False)


def get_system_usage(
    top_n: int = 10,
    sort_by: str = "cpu",
) -> dict[str, Any]:
    system = {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "cpu_count": psutil.cpu_count(),
        "memory": dict(psutil.virtual_memory()._asdict()),
        "swap": dict(psutil.swap_memory()._asdict()),
        "boot_time": psutil.boot_time(),
    }

    processes = []

    for proc in psutil.process_iter(
        [
            "pid",
            "name",
            "username",
            "cpu_percent",
            "memory_percent",
            "status",
        ]
    ):
        try:
            processes.append(
                {
                    "pid": proc.info["pid"],
                    "name": proc.info["name"],
                    "user": proc.info["username"],
                    "cpu_percent": proc.info["cpu_percent"],
                    "memory_percent": proc.info["memory_percent"],
                    "status": proc.info["status"],
                    "exe": get_process_exe(proc.info["pid"]),
                }
            )
        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            continue

    if sort_by == "memory":
        processes.sort(
            key=lambda p: p["memory_percent"],
            reverse=True,
        )
    else:
        processes.sort(
            key=lambda p: p["cpu_percent"],
            reverse=True,
        )

    return {
        "system": system,
        "processes": processes[:top_n],
    }


def reboot_if_system_unhealthy(
    cpu_threshold: float = 95.0,
    moving_average_window: int = 30,
    sustained_breach_minutes: int = 10,
    check_interval_seconds: int = 10,
    require_memory_pressure: bool = False,
    memory_threshold: float = 95.0,
) -> None:
    samples = deque(maxlen=moving_average_window)
    breach_start = None

    while True:
        stats = get_system_usage()
        cpu = stats["system"]["cpu_percent"]
        mem = stats["system"]["memory"]["percent"]

        samples.append(cpu)
        avg_cpu = sum(samples) / len(samples)
        cpu_critical = avg_cpu >= cpu_threshold

        if require_memory_pressure:
            unhealthy = cpu_critical and mem >= memory_threshold
        else:
            unhealthy = cpu_critical

        if unhealthy:
            if breach_start is None:
                breach_start = time.time()

            elapsed = time.time() - breach_start
            logging.warning(
                "CPU=%.1f%% AVG=%.1f%% MEM=%.1f%% " "Critical duration=%ds",
                cpu,
                avg_cpu,
                mem,
                int(elapsed),
            )

            if elapsed >= sustained_breach_minutes * 60:
                verification_stats = get_system_usage()
                verification_cpu = verification_stats["system"]["cpu_percent"]
                verification_mem = verification_stats["system"]["memory"]["percent"]
                final_unhealthy = verification_cpu >= cpu_threshold

                if require_memory_pressure:
                    final_unhealthy = (
                        final_unhealthy and verification_mem >= memory_threshold
                    )

                if final_unhealthy:
                    logging.critical(
                        "System unhealthy for %s minutes. " "Preparing reboot.",
                        sustained_breach_minutes,
                    )
                    logging.critical("Top offending processes:")

                    for process in verification_stats["processes"]:
                        logging.critical(
                            "PID=%s NAME=%s CPU=%.1f%% MEM=%.1f%% EXE=%s",
                            process["pid"],
                            process["name"],
                            process["cpu_percent"],
                            process["memory_percent"],
                            process["exe"],
                        )

                    send_incident_report_alert(
                        verification_stats,
                        avg_cpu,
                        verification_cpu,
                    )
                    time.sleep(5)

                    subprocess.run(
                        ["sync"],
                        check=False,
                    )
                    subprocess.run(
                        ["shutdown", "-r", "now"],
                        check=False,
                    )

                    return

        else:
            breach_start = None

        time.sleep(check_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    reboot_if_system_unhealthy(
        cpu_threshold=95.0,
        moving_average_window=100,
        sustained_breach_minutes=15,
        check_interval_seconds=300,
        require_memory_pressure=False,
    )
