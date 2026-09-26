# Test-only Cura plugin: executes commands appended to probe_cmds.txt, reports into probe_out.txt.
# Never install it in a Cura you use: the "eval" command runs arbitrary Python. See ../README.md.
import os
import time
import traceback

from PyQt6.QtCore import QObject, QTimer, QUrl, QMetaObject, Qt
from PyQt6.QtGui import QGuiApplication

from UM.Extension import Extension
from UM.Logger import Logger
from UM.PluginRegistry import PluginRegistry
from UM.Scene.Iterator.DepthFirstIterator import DepthFirstIterator

HERE = os.path.dirname(os.path.abspath(__file__))
CMDS = os.path.join(HERE, "probe_cmds.txt")
OUT = os.path.join(HERE, "probe_out.txt")


def out(text):
    with open(OUT, "a", encoding="utf-8") as f:
        f.write("%.1f %s\n" % (time.time(), text))


class Probe(QObject, Extension):
    def __init__(self):
        QObject.__init__(self)
        Extension.__init__(self)
        self._done = 0
        self._timer = QTimer()
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._poll)
        from cura.CuraApplication import CuraApplication
        self._app = CuraApplication.getInstance()
        self._timer.start()
        self._app.fileCompleted.connect(lambda f: out("fileCompleted " + f))
        out("probe loaded")

    def _poll(self):
        if not os.path.exists(CMDS):
            return
        with open(CMDS, encoding="utf-8") as f:
            lines = [l.rstrip("\n") for l in f]
        for line in lines[self._done:]:
            self._done += 1
            if not line.strip():
                continue
            out("> " + line)
            try:
                self._run(line)
            except Exception:
                out("ERROR " + traceback.format_exc())

    def _reader(self):
        return self._app.getMeshFileHandler().getReaderForFile("x.sldprt")

    def _run(self, line):
        cmd, _, arg = line.partition(" ")
        if cmd == "open":
            self._app.readLocalFile(QUrl.fromLocalFile(arg))
        elif cmd == "dump":
            root = self._app.getController().getScene().getRoot()
            for node in DepthFirstIterator(root):
                if node is root or not (node.getMeshData() or node.getChildren()):
                    continue
                if node.callDecoration("isSliceable") is None and node.callDecoration("isGroup") is None and not node.getMeshData():
                    continue
                bb = node.getBoundingBox()
                md = node.getMeshData()
                depth = 0
                p = node.getParent()
                while p is not None and p is not root:
                    depth += 1
                    p = p.getParent()
                out("NODE %s%r type=%s sliceable=%s group=%s size=%s bottom=%s pos=%s file=%s verts=%s mime=%s" % (
                    "  " * depth, node.getName(), type(node).__name__, node.callDecoration("isSliceable"), node.callDecoration("isGroup"),
                    None if bb is None else (round(bb.width, 2), round(bb.height, 2), round(bb.depth, 2)),
                    None if bb is None else round(bb.bottom, 2), node.getWorldPosition(),
                    md.getFileName() if md else None, md.getVertexCount() if md else None,
                    node.source_mime_type.name if node.source_mime_type else None))
            out("DUMP END")
        elif cmd == "clear":
            self._app.deleteAll()
        elif cmd == "reload":
            self._app.reloadAll()
        elif cmd == "grab":
            windows = [w for w in QGuiApplication.topLevelWindows() if w.isVisible() and hasattr(w, "grabWindow")]
            for i, w in enumerate(windows):
                path = "%s_%d.png" % (arg, i)
                w.grabWindow().save(path)
                out("grabbed %r %dx%d -> %s" % (w.title(), w.width(), w.height(), path))
        elif cmd == "windows":
            for w in QGuiApplication.topLevelWindows():
                out("WINDOW %r visible=%s %dx%d" % (w.title(), w.isVisible(), w.width(), w.height()))
        elif cmd == "dialog":
            # dialog <accept|reject|close> [quality_index] [remember]
            parts = arg.split()
            dialog = self._reader()._ui._dialog
            if dialog is None or not dialog.isVisible():
                out("no visible quality dialog")
                return
            out("dialog fileName=%r" % dialog.property("fileName"))
            if len(parts) > 1:
                dialog.findChild(QObject, "qualityBox").setProperty("currentIndex", int(parts[1]))
            if len(parts) > 2:
                dialog.findChild(QObject, "rememberBox").setProperty("checked", parts[2] == "1")
            if parts[0] == "close":
                dialog.close()
            else:
                QMetaObject.invokeMethod(dialog, parts[0])
        elif cmd == "pref":
            key, _, value = arg.partition(" ")
            self._app.getPreferences().setValue(key, value)
            out("pref %s = %r" % (key, self._app.getPreferences().getValue(key)))
        elif cmd == "getpref":
            out("pref %s = %r" % (arg, self._app.getPreferences().getValue(arg)))
        elif cmd == "menu":
            for ext in self._app.getExtensions():
                if arg in ext.getMenuItemList():
                    ext.activateMenuItem(arg)
                    out("activated menu %r of %s" % (arg, ext.getPluginId()))
                    return
            out("menu item not found; extensions: %s" % [(e.getPluginId(), e.getMenuItemList()) for e in self._app.getExtensions()])
        elif cmd == "plugins":
            reg = PluginRegistry.getInstance()
            out("active=%s outdated=%s" % (reg.isActivePlugin(arg), arg in reg._outdated_plugins))
            out("reader=%r" % self._reader())
        elif cmd == "eval":
            out("EVAL %r" % (eval(arg, {"app": self._app, "reader": self._reader()}),))
        elif cmd == "quit":
            self._app.closeApplication()
        else:
            out("unknown command")


def getMetaData():
    return {}


def register(app):
    return {"extension": Probe()}
