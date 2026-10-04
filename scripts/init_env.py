"""Create local configuration once; never print or overwrite a secret."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / ".env"
template = (root / ".env.example").read_text(encoding="utf-8")
content = template.replace(
    "POSTGRES_PASSWORD=\n", f"POSTGRES_PASSWORD={secrets.token_hex(32)}\n"
)
try:
    with target.open("x", encoding="utf-8", newline="\n") as output:
        output.write(content)
    target.chmod(0o600)
    print("Created .env with a random local database password. Keep this file private.")
except FileExistsError:
    print(".env already exists; preserved without changes.")
