"""Read package metadata for dependency review; does not install packages."""
import json
from pathlib import Path
from urllib.request import urlopen

records = []
for name in ["react", "react-dom", "vite", "typescript", "@types/react", "@types/react-dom", "i18next", "react-i18next", "@playwright/test"]:
    url = "https://registry.npmjs.org/" + name + "/latest"
    with urlopen(url, timeout=30) as response:
        info = json.load(response)
    record = {"name": name, "version": info["version"], "license": info.get("license"), "source": url}
    records.append(record)
    print(record["name"], record["version"], record["license"])
Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/npm-metadata.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
