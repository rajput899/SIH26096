"""Hidden local credential prompt; pass auth to existing playback check via stdin only."""
import getpass
import json
import subprocess
import sys

if not sys.stdin.isatty():
    raise SystemExit("Use an interactive terminal for hidden password entry")
auth = {"login": input("Existing staff login: ").strip(),
        "password": getpass.getpass("Existing staff password (hidden): ")}
result = subprocess.run(["node", "scripts/verify_submission_media.cjs"],
                        input=json.dumps(auth), text=True, check=False)
raise SystemExit(result.returncode)
