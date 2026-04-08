#!/usr/bin/env python3
"""
Network Device Backup Automation Script
========================================
Automates SSH-based backup of network device configurations.
Supports Cisco IOS, Cisco ASA, Juniper JunOS, and Arista EOS.

Author: Jonathan Zaldivar
Blog: networkthinktank.blog
License: MIT
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from netmiko import ConnectHandler
    from netmiko.exceptions import (
        NetmikoTimeoutException,
        NetmikoAuthenticationException,
    )
except ImportError:
    print("ERROR: Netmiko is required. Install it with: pip install netmiko")
    sys.exit(1)

# -- Logging Configuration ----------------------------------------------------
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("network_backup")


# -- Default Settings ---------------------------------------------------------
DEFAULT_BACKUP_DIR = "backups"
DEFAULT_INVENTORY = "inventory.json"
MAX_WORKERS = 5

# Map of device_type -> show command for running config
BACKUP_COMMANDS = {
    "cisco_ios": "show running-config",
    "cisco_asa": "show running-config",
    "cisco_nxos": "show running-config",
    "juniper_junos": "show configuration | display set",
    "arista_eos": "show running-config",
    "linux": "cat /etc/network/interfaces",
}

def load_inventory(inventory_path: str) -> list[dict]:
    """Load device inventory from a JSON file.

    Expected JSON structure:
    [
        {
            "hostname": "core-rtr-01",
            "host": "192.168.1.1",
            "device_type": "cisco_ios",
            "username": "admin",
            "password": "secret",
            "port": 22,
            "secret": "enable_secret"   // optional
        },
        ...
    ]
    """
    path = Path(inventory_path)
    if not path.exists():
        logger.error(f"Inventory file not found: {inventory_path}")
        sys.exit(1)

    with open(path, "r") as fh:
        try:
            devices = json.load(fh)
        except json.JSONDecodeError as exc:
            logger.error(f"Invalid JSON in inventory file: {exc}")
            sys.exit(1)

    logger.info(f"Loaded {len(devices)} device(s) from {inventory_path}")
    return devices


def ensure_backup_directory(backup_dir: str) -> Path:
    """Create the backup directory tree if it does not exist."""
    today = datetime.now().strftime("%Y-%m-%d")
    target = Path(backup_dir) / today
    target.mkdir(parents=True, exist_ok=True)
    return target

def backup_device(device: dict, backup_dir: Path) -> dict:
    """Connect to a single device, pull its config, and save to disk.

    Returns a result dict with status information.
    """
    hostname = device.get("hostname", device.get("host", "unknown"))
    result = {
        "hostname": hostname,
        "host": device.get("host"),
        "status": "success",
        "message": "",
        "file": "",
        "timestamp": datetime.now().isoformat(),
    }

    device_type = device.get("device_type", "cisco_ios")
    command = BACKUP_COMMANDS.get(device_type, "show running-config")

    # Build the Netmiko connection parameters
    connection_params = {
        "device_type": device_type,
        "host": device["host"],
        "username": device["username"],
        "password": device["password"],
        "port": device.get("port", 22),
        "timeout": device.get("timeout", 30),
        "banner_timeout": 15,
    }

    # Optional enable secret
    if device.get("secret"):
        connection_params["secret"] = device["secret"]
    try:
        logger.info(f"[{hostname}] Connecting to {device['host']}...")
        connection = ConnectHandler(**connection_params)

        # Enter enable mode if a secret was provided
        if device.get("secret"):
            connection.enable()

        logger.info(f"[{hostname}] Running: {command}")
        output = connection.send_command(command, read_timeout=60)

        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_hostname = hostname.replace(" ", "_").replace("/", "_")
        filename = f"{safe_hostname}_{timestamp}.cfg"
        filepath = backup_dir / filename

        with open(filepath, "w") as cfg_file:
            cfg_file.write(f"! Backup of {hostname} ({device['host']})\n")
            cfg_file.write(f"! Date: {datetime.now().isoformat()}\n")
            cfg_file.write(f"! Device Type: {device_type}\n")
            cfg_file.write(f"! Command: {command}\n")
            cfg_file.write("!" + "=" * 60 + "\n\n")
            cfg_file.write(output)

        result["file"] = str(filepath)
        result["message"] = f"Backup saved to {filepath}"
        logger.info(f"[{hostname}] Backup saved -> {filepath}")

        connection.disconnect()
    except NetmikoTimeoutException:
        result["status"] = "failed"
        result["message"] = f"Connection timed out to {device['host']}"
        logger.error(f"[{hostname}] Timeout connecting to {device['host']}")

    except NetmikoAuthenticationException:
        result["status"] = "failed"
        result["message"] = f"Authentication failed for {device['host']}"
        logger.error(f"[{hostname}] Auth failed for {device['host']}")

    except Exception as exc:
        result["status"] = "failed"
        result["message"] = str(exc)
        logger.error(f"[{hostname}] Error: {exc}")

    return result

def run_backups(
    inventory_path: str,
    backup_dir: str = DEFAULT_BACKUP_DIR,
    max_workers: int = MAX_WORKERS,
) -> list[dict]:
    """Orchestrate the backup of all devices in the inventory.

    Uses a thread pool to back up multiple devices concurrently.
    """
    devices = load_inventory(inventory_path)
    target_dir = ensure_backup_directory(backup_dir)

    results = []

    logger.info(
        f"Starting backup run -- {len(devices)} device(s), "
        f"max {max_workers} concurrent connections"
    )
    logger.info(f"Backup directory: {target_dir}")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(backup_device, dev, target_dir): dev
            for dev in devices
        }

        for future in as_completed(futures):
            result = future.result()
            results.append(result)
    # -- Summary ---------------------------------------------------------------
    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")

    logger.info("=" * 60)
    logger.info("BACKUP RUN COMPLETE")
    logger.info(f"  Total devices : {len(devices)}")
    logger.info(f"  Successful    : {success}")
    logger.info(f"  Failed        : {failed}")
    logger.info("=" * 60)

    # Save a summary report
    report_path = target_dir / "backup_report.json"
    with open(report_path, "w") as rpt:
        json.dump(
            {
                "run_date": datetime.now().isoformat(),
                "total_devices": len(devices),
                "successful": success,
                "failed": failed,
                "results": results,
            },
            rpt,
            indent=2,
        )
    logger.info(f"Report saved -> {report_path}")

    return results

# -- CLI Entry Point -----------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Network Device Backup Automation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python network_backup.py
  python network_backup.py -i devices.json -o /var/backups/network
  python network_backup.py --workers 10 --verbose
        """,
    )
    parser.add_argument(
        "-i", "--inventory",
        default=DEFAULT_INVENTORY,
        help=f"Path to device inventory JSON (default: {DEFAULT_INVENTORY})",
    )
    parser.add_argument(
        "-o", "--output",
        default=DEFAULT_BACKUP_DIR,
        help=f"Backup output directory (default: {DEFAULT_BACKUP_DIR})",
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=MAX_WORKERS,
        help=f"Max concurrent connections (default: {MAX_WORKERS})",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug-level logging",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    results = run_backups(args.inventory, args.output, args.workers)

    # Exit with error code if any backups failed
    if any(r["status"] == "failed" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
