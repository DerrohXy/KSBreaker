# KSBreaker

KSBreaker is a lightweight Python watchdog service that monitors system resource usage and automatically reboots a server if it remains under sustained critical load for an extended period.

The goal is to recover from situations where a server becomes effectively unusable due to runaway CPU consumption, deadlocks, or other resource exhaustion scenarios.

## Features

* Monitors overall CPU utilization
* Calculates a moving average to avoid reacting to short spikes
* Requires sustained threshold violations before taking action
* Logs resource information to systemd journal
* Captures top resource-consuming processes before rebooting
* Runs as a systemd service
* Automatically starts on boot
* Automatically restarts if the watchdog itself crashes

## Requirements

* Linux system with systemd
* Python 3.8+
* psutil

## Installation

Place the watchdog script (`ksbreaker.py`) and installer (`install.sh`) in the same directory.

Run:

```bash
chmod +x install.sh
sudo ./install.sh
```

The installer will:

* Install Python dependencies
* Install the watchdog under `/opt/ksbreaker`
* Create a systemd service named `ksbreaker`
* Enable automatic startup on boot
* Start the service immediately

## Service Management

Check service status:

```bash
sudo systemctl status ksbreaker
```

Restart the service:

```bash
sudo systemctl restart ksbreaker
```

Stop the service:

```bash
sudo systemctl stop ksbreaker
```

View logs:

```bash
journalctl -u ksbreaker -f
```

## Configuration

Configuration values are currently defined directly in the Python script.

Example:

```python
reboot_if_system_unhealthy(
    cpu_threshold=95.0,
    moving_average_window=30,
    sustained_breach_minutes=10,
    check_interval_seconds=10,
    require_memory_pressure=False,
)
```

### Parameters

| Parameter                | Description                                                     |
| ------------------------ | --------------------------------------------------------------- |
| cpu_threshold            | CPU percentage required before a system is considered unhealthy |
| moving_average_window    | Number of CPU samples used to calculate the moving average      |
| sustained_breach_minutes | Duration the threshold must remain exceeded before reboot       |
| check_interval_seconds   | Time between checks                                             |
| require_memory_pressure  | Require memory pressure in addition to CPU pressure             |
| memory_threshold         | Memory threshold used when memory pressure is enabled           |

## How Reboot Decisions Are Made

The watchdog does not reboot on a single high CPU reading.

Instead it:

1. Samples CPU usage continuously.
2. Calculates a moving average.
3. Verifies that the average remains above the configured threshold.
4. Tracks how long the threshold remains exceeded.
5. Performs a final verification check.
6. Logs the top resource-consuming processes.
7. Initiates a reboot.

This approach helps reduce false positives caused by temporary CPU spikes.

## Uninstallation

Run:

```bash
sudo ./uninstall.sh
```

Or manually:

```bash
sudo systemctl stop ksbreaker
sudo systemctl disable ksbreaker

sudo rm -f /etc/systemd/system/ksbreaker.service
sudo rm -rf /opt/ksbreaker

sudo systemctl daemon-reload
```

## Warning

This software intentionally reboots the host machine.

Improper threshold configuration may result in unnecessary reboots or reboot loops. Test thoroughly in a non-production environment before deploying to critical systems.

Consider implementing process termination, alerting, or remote monitoring before enabling automatic reboots in production.

## License

Provided as-is without warranty. Review and modify the code to suit your operational requirements before deployment.
