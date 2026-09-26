# Copyright (c) 2026 CuraSolidWorksPlugin contributors
# CuraSolidWorksPlugin is released under the terms of the LGPLv3 or higher.

"""Run the plugin's SolidWorks conversion outside of Cura, with any Python 3.9+ on Windows.

    python tests/convert_standalone.py PART.SLDPRT [--format stl|3mf] [--quality fine|coarse|solidworks] [--out DIR]

Prints the mesh statistics of the result. With --check-preferences it also reads SolidWorks' export preferences
before and after the conversion and fails if the conversion didn't put them back.
"""

import argparse
import math
import os
import re
import struct
import sys
import tempfile
import time
import types
import zipfile

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Import the plugin's modules as a package without running its __init__.py, which needs Uranium.
_package = types.ModuleType("solidworks_plugin")
_package.__path__ = [PLUGIN_DIR]
sys.modules["solidworks_plugin"] = _package

from solidworks_plugin.ComAutomation import ComObject, findProcessIds  # noqa: E402
from solidworks_plugin.SolidWorksSession import SolidWorksSession, SolidWorksError  # noqa: E402

PREFERENCES = [("GetUserPreferenceToggle", 69, "STL binary"),
               ("GetUserPreferenceToggle", 70, "STL show info on save"),
               ("GetUserPreferenceToggle", 72, "STL components into one file"),
               ("GetUserPreferenceToggle", 191, "STL preview"),
               ("GetUserPreferenceToggle", 643, "3MF show info on save"),
               ("GetUserPreferenceIntegerValue", 78, "STL quality"),
               ("GetUserPreferenceIntegerValue", 211, "STL units"),
               ("GetUserPreferenceDoubleValue", 2, "STL deviation"),
               ("GetUserPreferenceDoubleValue", 3, "STL angle tolerance")]


def log(level, message, *args):
    print("[{}] {}".format(level, message % args if args else message))


def readPreferences():
    app = ComObject.create("SldWorks.Application")
    process_id = app.call("GetProcessID")
    started = process_id not in running_before
    try:
        return {name: app.call(method, preference) for method, preference, name in PREFERENCES}
    finally:
        if started:
            app.call("ExitApp")
        app.release()
        while started and process_id in findProcessIds("sldworks.exe"):
            time.sleep(0.25)


def meshStatistics(path):
    if path.lower().endswith(".stl"):
        with open(path, "rb") as f:
            data = f.read()
        count = struct.unpack_from("<I", data, 80)[0]
        points = [struct.unpack_from("<3f", data, 84 + i * 50 + 12 + v * 12) for i in range(count) for v in range(3)]
    else:
        with zipfile.ZipFile(path) as archive:
            model = archive.read("3D/3dmodel.model").decode("utf-8")
        count = len(re.findall(r"<triangle ", model))
        points = [tuple(float(v) for v in m) for m in re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', model)]
    low = [min(p[k] for p in points) for k in range(3)]
    high = [max(p[k] for p in points) for k in range(3)]
    return count, [round(h - l, 3) for l, h in zip(low, high)]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--format", default = "stl", choices = ["stl", "3mf"])
    parser.add_argument("--quality", default = "fine", choices = ["fine", "coarse", "solidworks"])
    parser.add_argument("--out", default = tempfile.gettempdir())
    parser.add_argument("--check-preferences", action = "store_true")
    parser.add_argument("--expect-extent", help = "comma separated x,y,z size in mm the export must have")
    arguments = parser.parse_args()

    running_before = findProcessIds("sldworks.exe")
    before = readPreferences() if arguments.check_preferences else None

    target = os.path.join(arguments.out, os.path.splitext(os.path.basename(arguments.file))[0] + "." + arguments.format)
    if os.path.exists(target):
        os.remove(target)
    try:
        with SolidWorksSession(log) as session:
            document = session.openDocument(arguments.file)
            try:
                session.export(document, target, arguments.quality)
            finally:
                session.closeDocument(document)
    except SolidWorksError as e:
        print("FAILED:", e)
        sys.exit(1)

    triangles, size = meshStatistics(target)
    print("OK {} -> {} ({} bytes, {} triangles, extent {} mm)".format(arguments.file, target, os.path.getsize(target), triangles, size))
    if arguments.expect_extent:
        expected = [float(v) for v in arguments.expect_extent.split(",")]
        if any(abs(a - b) > 0.05 for a, b in zip(size, expected)):
            print("WRONG EXTENT: expected", expected)
            sys.exit(3)
    print("SolidWorks processes before: {}, after: {}".format(sorted(running_before), sorted(findProcessIds("sldworks.exe"))))

    if before is not None:
        after = readPreferences()
        changed = {name: (before[name], after[name]) for name in before
                   if not (math.isclose(before[name], after[name], rel_tol = 1e-9) if isinstance(before[name], float) else before[name] == after[name])}
        print("preferences:", before)
        if changed:
            print("PREFERENCES NOT RESTORED:", changed)
            sys.exit(2)
        print("preferences restored OK")
