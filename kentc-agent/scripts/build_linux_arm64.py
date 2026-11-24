"""Build the relocatable Linux ARM64 distribution with Conda and pip."""

import argparse
import os
import platform
import subprocess
import tempfile
import tomllib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
FILES = ("README.md", "scripts/bootstrap_server.py", "scripts/bootstrap_ui.html")
ASSETS = (
    "src", "config", "web", "skills", "personas", "queries",
    "examples/ter-case", "examples/rm-case",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    if (platform.system(), platform.machine()) != ("Linux", "aarch64") or platform.libc_ver()[0] != "glibc":
        parser.exit(1, "Build on glibc-based Linux ARM64 (aarch64).\n")

    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    name = f"kentc-agent-{version}-linux-arm64"
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="kentc-build-") as staging:
        stage = Path(staging)
        prefix = stage / "env"
        python = prefix / "bin/python"
        constraints = stage / "constraints.txt"
        lock = tomllib.loads((ROOT / "uv.lock").read_text())
        with constraints.open("w") as out:
            for package in lock["package"]:
                if "registry" not in package["source"]:
                    continue
                markers = package.get("resolution-markers", [])
                marker = "; " + " or ".join(f"({m})" for m in markers) if markers else ""
                print(f"{package['name']}=={package['version']}{marker}", file=out)

        def run(*command: str | Path) -> None:
            subprocess.run(command, cwd=ROOT, check=True)

        run("conda", "create", "--yes", "--override-channels", "-c", "conda-forge", "-p", prefix,
            "python=3.13", "pip", "libstdcxx")
        run(python, "-m", "pip", "install", "--constraint", constraints,
            "--only-binary=:all:", "--no-binary=red-black-tree-mod", ".[dev]")
        run(python, "-m", "pip", "check")
        runtime = stage / "runtime.tar.gz"
        run("conda-pack", "-p", prefix, "-o", runtime)

        with tempfile.TemporaryDirectory(dir=output) as publishing:
            zip_path = Path(publishing) / f"{name}.zip"
            with ZipFile(zip_path, "w", ZIP_DEFLATED) as bundle:
                bundle.write(runtime, f"{name}/runtime.tar.gz", ZIP_STORED)
                bundle.write(ROOT / "scripts/run_bundle.sh", f"{name}/run.sh")
                for entry in FILES:
                    bundle.write(ROOT / entry, f"{name}/{entry}")
                for asset in ASSETS:
                    for directory, dirs, files in os.walk(ROOT / asset):
                        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d != "__pycache__")
                        for file in sorted(files):
                            path = Path(directory) / file
                            if not file.startswith(".") and not path.is_symlink():
                                bundle.write(path, f"{name}/{path.relative_to(ROOT)}")
            zip_path.replace(output / zip_path.name)
    print(output / zip_path.name)


if __name__ == "__main__":
    main()
