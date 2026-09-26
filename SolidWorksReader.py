# Copyright (c) 2017 Thomas Karl Pietrowski
# Copyright (c) 2026 CuraSolidWorksPlugin contributors
# CuraSolidWorksPlugin is released under the terms of the LGPLv3 or higher.

import math
import os
import shutil
import tempfile
import threading
import winreg

from UM.Application import Application
from UM.i18n import i18nCatalog
from UM.Logger import Logger
from UM.Math.Quaternion import Quaternion
from UM.Math.Vector import Vector
from UM.Mesh.MeshReader import MeshReader
from UM.Message import Message
from UM.MimeTypeDatabase import MimeTypeDatabase, MimeType, MimeTypeNotFoundError
from UM.PluginRegistry import PluginRegistry
from UM.Scene.Iterator.DepthFirstIterator import DepthFirstIterator
from UM.Scene.SceneNode import SceneNode

from cura.Scene.CuraSceneNode import CuraSceneNode
from cura.Scene.ZOffsetDecorator import ZOffsetDecorator

from .ComAutomation import COMError, initializeComForThread
from .SolidWorksReaderUI import SolidWorksReaderUI
from .SolidWorksSession import SolidWorksSession, SolidWorksError, PROG_ID, QUALITY_FINE, describeComError

catalog = i18nCatalog("cura")

FORMAT_PREFERENCE = "cura_solidworks/transfer_format"
FORMAT_3MF = "3mf"
FORMAT_STL = "stl"

# The Cura plugins that read what SolidWorks exports.
_FORMAT_READERS = {FORMAT_3MF: "3MFReader", FORMAT_STL: "STLReader"}

_MIME_TYPES = [MimeType(name = "application/x-sldworks-part", comment = "SolidWorks part file", suffixes = ["sldprt"]),
               MimeType(name = "application/x-sldworks-assembly", comment = "SolidWorks assembly file", suffixes = ["sldasm"])]


def isSolidWorksInstalled() -> bool:
    try:
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, PROG_ID))
        return True
    except OSError:
        return False


class SolidWorksReader(MeshReader):
    # Conversions run one at a time: they share SolidWorks and its (global) export settings.
    _conversion_lock = threading.Lock()

    def __init__(self) -> None:
        super().__init__()
        self._supported_extensions = [".sldprt", ".sldasm"]
        for mime_type in _MIME_TYPES:
            MimeTypeDatabase.addMimeType(mime_type)

        Application.getInstance().getPreferences().addPreference(FORMAT_PREFERENCE, FORMAT_3MF)

        self._ui = SolidWorksReaderUI()
        self._quality_for_file = {}  # Chosen in preRead, used by _read. Several files can be loading at once.

    @staticmethod
    def _fileKey(file_name: str) -> str:
        return os.path.normcase(os.path.realpath(file_name))

    def preRead(self, file_name, *args, **kwargs):
        quality = self._ui.askQuality(os.path.basename(file_name))
        if quality is None:
            return MeshReader.PreReadResult.cancelled
        self._quality_for_file[self._fileKey(file_name)] = quality
        return MeshReader.PreReadResult.accepted

    def _read(self, file_name):
        quality = self._quality_for_file.pop(self._fileKey(file_name), None) or self._ui.rememberedQuality() or QUALITY_FINE
        with self._conversion_lock:
            initializeComForThread()
            temp_dir = tempfile.mkdtemp(prefix = "cura_solidworks_")
            try:
                nodes = self._convert(file_name, temp_dir, quality)
            except SolidWorksError as e:
                Logger.log("e", "Converting %s failed: %s", file_name, e)
                self._showError(str(e))
                return None
            except COMError as e:
                Logger.logException("e", "Converting %s failed.", file_name)
                self._showError(describeComError(e, file_name))
                return None
            except Exception as e:
                Logger.logException("e", "Converting %s failed.", file_name)
                self._showError(catalog.i18nc("@info:status", "Unexpected error while converting the file with SolidWorks: {}").format(e))
                return None
            finally:
                shutil.rmtree(temp_dir, ignore_errors = True)

        if not nodes:
            return None
        self._postProcess(nodes, file_name)
        return nodes

    def _preferredFormats(self):
        preferred = Application.getInstance().getPreferences().getValue(FORMAT_PREFERENCE)
        formats = [FORMAT_3MF, FORMAT_STL] if preferred == FORMAT_3MF else [FORMAT_STL, FORMAT_3MF]
        return [f for f in formats if PluginRegistry.getInstance().isActivePlugin(_FORMAT_READERS[f])]

    def _convert(self, file_name, temp_dir, quality):
        formats = self._preferredFormats()
        if not formats:
            raise SolidWorksError(catalog.i18nc("@info:status", "Neither the 3MF nor the STL reader plugin is enabled in Cura, so the converted file can't be loaded."))

        base_name = os.path.splitext(os.path.basename(file_name))[0]
        last_error = None
        with SolidWorksSession(Logger.log) as session:
            document = session.openDocument(file_name)
            try:
                for file_format in formats:
                    if file_format == FORMAT_3MF and not session.supports3mf():
                        continue
                    target = os.path.join(temp_dir, "{}.{}".format(base_name, file_format))
                    try:
                        session.export(document, target, quality)
                    except SolidWorksError as e:
                        Logger.log("w", "%s export failed, trying the next format: %s", file_format, e)
                        last_error = e
                        continue
                    Logger.log("i", "%s saved %s as %s (%d bytes).", session.friendly_name, file_name, file_format.upper(), os.path.getsize(target))
                    nodes = self._readExport(target)
                    if nodes:
                        return nodes
                    last_error = SolidWorksError(catalog.i18nc("@info:status", "Cura could not read the {} file that SolidWorks produced.").format(file_format.upper()))
            finally:
                session.closeDocument(document)
        raise last_error or SolidWorksError(catalog.i18nc("@info:status", "SolidWorks could not convert the file."))

    @staticmethod
    def _readExport(path):
        reader = Application.getInstance().getMeshFileHandler().getReaderForFile(path)
        if reader is None:
            return None
        try:
            result = reader.read(path)
        finally:
            # The reader starts watching the temporary file for changes; the original file is what matters.
            Application.getInstance().getController().getScene().removeWatchedFile(path)
        if result is None:
            return None
        nodes = result if isinstance(result, list) else [result]
        return [node for node in nodes if node is not None]

    @staticmethod
    def _postProcess(nodes, file_name):
        # SolidWorks keeps its own "Y is up" axes in STL and 3MF exports, while both formats (and so Cura's readers)
        # assume Z is up. Tip the model back so that it stands in Cura the way it does in SolidWorks.
        rotation = Quaternion.fromAngleAxis(math.radians(90), Vector.Unit_X)
        name = os.path.basename(file_name)
        try:
            mime_type = MimeTypeDatabase.getMimeTypeForFile(file_name)
        except MimeTypeNotFoundError:
            mime_type = None

        for index, node in enumerate(nodes):
            if isinstance(node, CuraSceneNode):
                # Cura adds these nodes to the scene as they are, transformation included (3MF).
                node.rotate(rotation, SceneNode.TransformSpace.Parent)
                # The 3MF reader pins objects that reach below Z=0 at that depth, which is right for Cura projects
                # but not for SolidWorks coordinates, where the origin can be anywhere. Let them drop onto the plate.
                for descendant in DepthFirstIterator(node):
                    descendant.removeDecorator(ZOffsetDecorator)
            elif node.getMeshData() is not None:
                # Of a plain SceneNode (STL) Cura only takes over the mesh data, so the rotation goes into the vertices.
                node.setMeshData(node.getMeshData().getTransformed(rotation.toMatrix()))

            node.setName(name if len(nodes) == 1 else "{} ({})".format(name, index + 1))
            if mime_type is not None:
                node.source_mime_type = mime_type
            # Point the meshes at the SolidWorks file, so "Reload" and the file-changed prompt use it (not the
            # temporary export, which is gone by now).
            for descendant in DepthFirstIterator(node):
                mesh_data = descendant.getMeshData()
                if mesh_data is not None:
                    descendant.setMeshData(mesh_data.set(file_name = file_name))

    @staticmethod
    def _showError(text):
        Message(text,
                lifetime = 0,
                title = catalog.i18nc("@info:title", "SolidWorks Integration"),
                message_type = Message.MessageType.ERROR).show()
