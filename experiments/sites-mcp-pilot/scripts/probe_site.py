"""Probe a private Site without recording its access token."""

import json
import subprocess
import sys


config = json.loads(sys.stdin.readline())
base = config["url"]
token = config["token"]
for path in ("/", "/health", "/mcp", "/api/mcp"):
    result = subprocess.run(
        [
            "curl",
            "--config",
            "-",
            "--silent",
            "--show-error",
            "--output",
            "/dev/null",
            "--write-out",
            "%{http_code} %{content_type} pilot=%header{x-qcb-sites-pilot} %{url_effective}",
            base + path,
        ],
        input='header = "OAI-Sites-Authorization: Bearer ' + token + '"\n',
        capture_output=True,
        text=True,
        timeout=15,
    )
    print(path, result.stdout.strip(), result.stderr.strip())
