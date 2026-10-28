
import platform
import re
import subprocess
import shutil


def ping_host(host, timeout_ms=1500):
    """Return (status, response_ms) after pinging a host."""

    # Prevent invalid or missing host values
    if not isinstance(host, str) or not host.strip():
        return "Offline", None

    host = host.strip()

    # Find the system ping executable
    ping_exe = shutil.which("ping")
    if not ping_exe:
        return "Offline", None

    system = platform.system().lower()

    if system == "windows":
        command = [
            ping_exe, "-n", "1", "-w",
            str(timeout_ms), host
        ]
        timeout_seconds = timeout_ms / 1000 + 2
    else:
        command = [
            ping_exe, "-c", "1", "-W",
            str(max(1, round(timeout_ms / 1000))), host
        ]
        timeout_seconds = timeout_ms / 1000 + 3

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False
        )

        output = (result.stdout or "") + "\n" + (result.stderr or "")

        if result.returncode != 0:
            return "Offline", None

        match = re.search(
            r"time\s*[=<]\s*(\d+(?:\.\d+)?)\s*ms",
            output,
            re.IGNORECASE
        )

        if match:
            return "Online", float(match.group(1))

        return "Online", None

    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "Offline", None
