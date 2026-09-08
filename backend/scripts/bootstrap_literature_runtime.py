"""Fetch a project-local CPU runtime and public Qwen weights from official sources.

No installer, PATH modification, or credential changes. Large files stay in
the ignored .runtime directory. Download hashes and exact versions are recorded.
"""
import hashlib
import json
import zipfile
from pathlib import Path
from urllib.parse import quote
import requests

ROOT = Path(__file__).resolve().parents[2] / ".runtime" / "literature"
ROOT.mkdir(parents=True, exist_ok=True)
SESSION = requests.Session()


def get_json(url):
    response = SESSION.get(url, timeout=45)
    response.raise_for_status()
    return response.json()


def download(url, destination, expected=None):
    if destination.exists() and expected and hashlib.sha256(destination.read_bytes()).hexdigest() == expected:
        return expected
    digest = hashlib.sha256()
    total, reported = 0, 0
    with SESSION.get(url, stream=True, timeout=(15, 120)) as response:
        response.raise_for_status()
        with destination.open("wb") as stream:
            for block in response.iter_content(1024 * 1024):
                stream.write(block)
                digest.update(block)
                total += len(block)
                if total - reported >= 100 * 1024 * 1024:
                    print(f"Downloaded {total // (1024*1024)} MB: {destination.name}", flush=True)
                    reported = total
    checksum = digest.hexdigest()
    if expected and checksum != expected:
        raise ValueError(f"Checksum mismatch: {destination.name}")
    return checksum


releases = get_json("https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=10")
release = next(item for item in releases if any(asset["name"].endswith("bin-win-cpu-x64.zip") for asset in item["assets"]))
asset = next(item for item in release["assets"] if item["name"].endswith("bin-win-cpu-x64.zip"))
print(f"Official CPU runtime: {asset['name']} ({asset['size']//1048576} MB)", flush=True)
expected = (asset.get("digest") or "").removeprefix("sha256:") or None
archive = ROOT / asset["name"]
runtime_hash = download(asset["browser_download_url"], archive, expected)
runtime_dir = ROOT / "llama"
runtime_dir.mkdir(exist_ok=True)
with zipfile.ZipFile(archive) as zipped:
    for item in zipped.infolist():
        target = (runtime_dir / item.filename).resolve()
        if not target.is_relative_to(runtime_dir.resolve()):
            raise ValueError("Unsafe archive path")
    zipped.extractall(runtime_dir)

repo = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"
metadata = get_json(f"https://huggingface.co/api/models/{repo}")
revision = metadata["sha"]
files = get_json(f"https://huggingface.co/api/models/{repo}/tree/{revision}")
model = next(item for item in files if item["path"].lower().endswith("q4_k_m.gguf"))
model_path = ROOT / Path(model["path"]).name
print(f"Official model: {model['path']} ({model['size']//1048576} MB)", flush=True)
model_hash = download(f"https://huggingface.co/{repo}/resolve/{revision}/{quote(model['path'])}", model_path, model["lfs"]["oid"])
manifest = {"runtime_release": release["tag_name"], "runtime_url": asset["browser_download_url"], "runtime_sha256": runtime_hash,
    "model_repository": repo, "model_revision": revision, "model_path": str(model_path), "model_sha256": model_hash,
    "model_license": metadata.get("cardData", {}).get("license"), "server": str(next(runtime_dir.rglob("llama-server.exe")))}
(ROOT / "runtime.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(json.dumps(manifest, indent=2), flush=True)
