# Copyright (c) 2026 CuraSolidWorksPlugin contributors
# CuraSolidWorksPlugin is released under the terms of the LGPLv3 or higher.

"""Build dist/CuraSolidWorksPlugin-<version>.curapackage, which installs by dragging it onto Cura's window.

    python tools/build_package.py

Packs the files git knows about (tracked, or new and not ignored), minus development-only folders.
"""

import json
import os
import subprocess
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE_ID = "CuraSolidWorksPlugin"  # Also the plugin's folder name, which Cura uses as its plugin ID.
EXCLUDED_PREFIXES = ("tests/", "tools/", "dist/", ".git")
REPOSITORY = "https://github.com/Luix333/LegacyCuraSolidWorksPlugin"


def pluginFiles():
    listing = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                             cwd = ROOT, check = True, capture_output = True, text = True).stdout.splitlines()
    return sorted(path for path in listing
                  if not path.startswith(EXCLUDED_PREFIXES) and os.path.isfile(os.path.join(ROOT, path)))


def main():
    with open(os.path.join(ROOT, "plugin.json"), encoding = "utf-8") as f:
        plugin = json.load(f)
    sdk = plugin["supported_sdk_versions"][0]
    package = {
        "package_id": PACKAGE_ID,
        "package_type": "plugin",
        "display_name": plugin["name"],
        "description": plugin["description"],
        "package_version": plugin["version"],
        "sdk_version": int(sdk.split(".")[0]),
        "sdk_version_semver": sdk,
        "website": REPOSITORY,
        "author": {"author_id": "Luix333", "display_name": "Luix333 (fork of Ultimaker's legacy plugin)", "website": REPOSITORY},
    }

    os.makedirs(os.path.join(ROOT, "dist"), exist_ok = True)
    target = os.path.join(ROOT, "dist", "{}-{}.curapackage".format(PACKAGE_ID, plugin["version"]))
    files = pluginFiles()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("package.json", json.dumps(package, indent = 4))
        archive.write(os.path.join(ROOT, "LICENSE"), "LICENSE")
        for path in files:
            archive.write(os.path.join(ROOT, path), "files/plugins/{}/{}".format(PACKAGE_ID, path))
    print("{} ({} files, {} bytes)".format(target, len(files), os.path.getsize(target)))


if __name__ == "__main__":
    main()
