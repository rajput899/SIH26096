"""Capture two explicitly reusable PIB source excerpts; no database writes."""
import hashlib
import json
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        if tag in ("p", "li", "div", "br", "h1", "h2"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        if tag in ("p", "li", "div"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


out = Path("outputs/submission-sources")
out.mkdir(exist_ok=True)
urls = {
    "constitution": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=1489909",
    "biography": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2017835",
    "rights": "https://www.pib.gov.in/content/3604_2_CopyrightPolicy.aspx?lang=1&reg=3",
}
manifest = {}
for name, url in urls.items():
    capture = out / (name + ".html")
    raw = capture.read_bytes() if capture.exists() else urllib.request.urlopen(url, timeout=25).read()
    if not capture.exists():
        capture.write_bytes(raw)
    parser = Text()
    parser.feed(raw.decode("utf-8"))
    lines = [" ".join(x.split()) for x in "".join(parser.parts).splitlines() if x.strip()]
    (out / (name + "-page.txt")).write_text("\n".join(lines), encoding="utf-8")
    manifest[name] = {"url": url, "sha256": hashlib.sha256(raw).hexdigest()}
    print(name, len(raw), manifest[name]["sha256"])
    if name != "rights":
        selected = next(line for line in lines if
                        (name == "constitution" and line.startswith("42.")) or
                        (name == "biography" and "was born on 14 April 1891" in line))
        (out / (name + "-excerpt.txt")).write_text(selected + "\n", encoding="utf-8")
        print(selected)
(out / "locators.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
