# Copyright (c) 2026 CuraSolidWorksPlugin contributors
# CuraSolidWorksPlugin is released under the terms of the LGPLv3 or higher.

"""Talks to SolidWorks over COM to turn a part or assembly into a mesh file.

This module doesn't depend on Uranium, so it can be exercised with a plain Python interpreter and a SolidWorks
installation (see tests/convert_standalone.py).

SolidWorks hands every COM client the instance that is already running, if there is one. A session therefore first
works out whether it started SolidWorks itself, and only then takes liberties with it: an instance we started is kept
invisible and is closed again afterwards, while the user's own instance keeps its window, its open documents and its
export settings exactly as they were.
"""

import ctypes
import os
import time

from .ComAutomation import ComObject, COMError, findProcessIds
from .SolidWorksConstants import SolidWorksEnums, SolidWorkVersions

_TOGGLE = SolidWorksEnums.swUserPreferenceToggle_e
_INTEGER = SolidWorksEnums.swUserPreferenceIntegerValue_e
_DOUBLE = SolidWorksEnums.swUserPreferenceDoubleValue_e
_QUALITY = SolidWorksEnums.swSTLQuality_e

PROG_ID = "SldWorks.Application"
EXECUTABLE_NAME = "sldworks.exe"
_EXIT_TIMEOUT = 30  # Seconds to wait for a SolidWorks that we started to shut down.

DOCUMENT_TYPES = {".sldprt": SolidWorksEnums.swDocumentTypes_e.swDocPART,
                  ".sldasm": SolidWorksEnums.swDocumentTypes_e.swDocASSEMBLY}

# Mesh quality choices, as offered in the plugin's dialogs.
QUALITY_FINE = "fine"
QUALITY_COARSE = "coarse"
QUALITY_SOLIDWORKS = "solidworks"  # Whatever is configured in SolidWorks' own export options.
_QUALITY_VALUES = {QUALITY_FINE: _QUALITY.swSTLQuality_Fine,
                   QUALITY_COARSE: _QUALITY.swSTLQuality_Coarse}


class SolidWorksError(Exception):
    """A failure with a message that is fit to show to the user."""


# HRESULTs that mean the SolidWorks process went away mid-call (it crashed, or was closed).
_RPC_GONE = {-2147023174,  # RPC_S_SERVER_UNAVAILABLE
             -2147023170,  # RPC_S_CALL_FAILED
             -2147417848,  # RPC_E_DISCONNECTED
             -2147417851}  # RPC_E_SERVERFAULT


def describeComError(error: COMError, file_name: str) -> str:
    if error.hresult in _RPC_GONE:
        return ("SolidWorks stopped while converting {} (it may have crashed). "
                "Check that the file opens in SolidWorks itself.").format(os.path.basename(file_name))
    return "SolidWorks reported an error while converting {}: {}".format(os.path.basename(file_name), error)


def looksLikeSolidWorksFile(path: str) -> bool:
    """Cheap sanity check of the file header, so that we don't make SolidWorks open something that isn't a SolidWorks
    file (a garbage .SLDPRT crashes it). Newer SolidWorks files have 00 00 00 04 at offset 4 (true for all 64 parts
    and assemblies from SolidWorks 2017 to 2023 this was checked against); older ones are OLE compound files."""

    with open(path, "rb") as f:
        header = f.read(8)
    return header[4:8] == b"\x00\x00\x00\x04" or header == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


class SolidWorksDocument:
    def __init__(self, model: ComObject, path: str, document_type: int, opened_by_us: bool) -> None:
        self.model = model
        self.path = path
        self.document_type = document_type
        self.opened_by_us = opened_by_us
        self.title = model.call("GetTitle")
        self.previously_active_title = None  # The user's active document, to switch back to once we're done.

    @property
    def is_assembly(self) -> bool:
        return self.document_type == SolidWorksEnums.swDocumentTypes_e.swDocASSEMBLY


class SolidWorksSession:
    def __init__(self, log = None) -> None:
        self._log = log or (lambda level, message, *args: None)
        self._app = None  # type: ComObject
        self._started_by_us = False
        self._process_id = None
        self.revision = (0, 0, 0)

    # Context manager, so that SolidWorks is always put back the way it was, even when a conversion fails.
    def __enter__(self) -> "SolidWorksSession":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.disconnect()

    @property
    def friendly_name(self) -> str:
        return SolidWorkVersions.friendlyName(self.revision[0])

    def supports3mf(self) -> bool:
        return self.revision[0] >= SolidWorkVersions.first_3mf_revision

    def connect(self) -> None:
        already_running = findProcessIds(EXECUTABLE_NAME)
        try:
            self._app = ComObject.create(PROG_ID)
        except (OSError, ValueError) as e:
            raise SolidWorksError("Could not start SolidWorks ({}). Is it installed and licensed?".format(e))

        try:
            process_id = self._app.call("GetProcessID")
        except Exception:
            process_id = None
        # Without a process ID, assume the instance is the user's: leaving an invisible SolidWorks behind is better
        # than closing somebody's work.
        self._started_by_us = process_id is not None and process_id not in already_running
        self._process_id = process_id

        revision = str(self._app.call("RevisionNumber"))
        numbers = []
        for part in revision.split("."):
            try:
                numbers.append(int(part))
            except ValueError:
                break
        self.revision = tuple((numbers + [0, 0, 0])[:3])
        self._log("i", "Connected to %s (revision %s, process %s, %s).", self.friendly_name, revision, process_id,
                  "started for this conversion" if self._started_by_us else "already running")

        if self._started_by_us:
            # Keep it in the background: no window, not even when documents get activated.
            self._app.set("UserControl", False)
            self._app.set("Visible", False)
            frame = self._app.call("Frame")
            if frame is not None:
                frame.set("KeepInvisible", True)
                frame.release()

    def disconnect(self) -> None:
        if self._app is None:
            return
        exited = False
        try:
            if self._started_by_us:
                self._log("d", "Closing the SolidWorks instance that was started for this conversion.")
                self._app.call("ExitApp")
                exited = True
        except Exception as e:
            self._log("w", "Could not close SolidWorks: %s", e)
        finally:
            self._app.release()
            self._app = None

        # ExitApp returns straight away and SolidWorks takes a few seconds to go. Wait for it, so that the next
        # conversion can't get handed the instance that is shutting down (and so its licence is free again).
        deadline = time.monotonic() + _EXIT_TIMEOUT
        while exited and self._process_id in findProcessIds(EXECUTABLE_NAME):
            if time.monotonic() > deadline:
                self._log("w", "SolidWorks (process %s) is still running %d s after being asked to exit.", self._process_id, _EXIT_TIMEOUT)
                break
            time.sleep(0.25)

    def openDocument(self, path: str) -> SolidWorksDocument:
        path = os.path.abspath(path)
        extension = os.path.splitext(path)[1].lower()
        if extension not in DOCUMENT_TYPES:
            raise SolidWorksError("Not a SolidWorks part or assembly: {}".format(path))
        document_type = DOCUMENT_TYPES[extension]

        try:
            plausible = os.path.getsize(path) > 0 and looksLikeSolidWorksFile(path)
        except OSError as e:
            raise SolidWorksError("Can't read {}: {}".format(path, e))
        if not plausible:
            if not self._started_by_us:
                raise SolidWorksError("{} doesn't look like a SolidWorks file. It was not opened in your running "
                                      "SolidWorks, where a broken file could crash it.".format(os.path.basename(path)))
            self._log("w", "%s doesn't look like a SolidWorks file; trying anyway.", path)

        # A document the user already has open is used as it is (including unsaved changes) and left open afterwards.
        model = self._app.call("GetOpenDocumentByName", path)
        if model is not None:
            self._log("d", "%s is already open in SolidWorks, using that document.", path)
            return SolidWorksDocument(model, path, document_type, opened_by_us = False)

        specification = self._app.call("GetOpenDocSpec", path)
        specification.set("DocumentType", document_type)
        specification.set("Silent", True)  # Never show dialogs, which nobody could click in an invisible SolidWorks.
        specification.set("ReadOnly", True)

        # No DocumentVisible(False) here: exporting activates the document, which shows it anyway, and activating a
        # document opened invisibly makes a hidden SolidWorks show its main window for good.
        model = self._app.call("OpenDoc7", specification)

        error = specification.get("Error") or 0
        warning = specification.get("Warning") or 0
        specification.release()
        if warning:
            self._log("w", "SolidWorks reported warnings while opening %s (swFileLoadWarning_e %s).", path, warning)
        if model is None:
            raise SolidWorksError("SolidWorks could not open {}: {}.".format(
                os.path.basename(path), SolidWorksEnums.describeBits(error, SolidWorksEnums.file_load_errors)))
        if error:
            self._log("w", "SolidWorks reported errors while opening %s (swFileLoadError_e %s).", path, error)
        return SolidWorksDocument(model, path, document_type, opened_by_us = True)

    def closeDocument(self, document: SolidWorksDocument) -> None:
        if document.opened_by_us:
            try:
                self._app.call("CloseDoc", document.path)
            except Exception as e:
                self._log("w", "Could not close %s in SolidWorks: %s", document.path, e)
        if document.previously_active_title and document.previously_active_title != self._activeTitle():
            try:
                self._activate(document.previously_active_title)
            except Exception as e:
                self._log("w", "Could not switch SolidWorks back to %s: %s", document.previously_active_title, e)
        document.model.release()

    def _activeTitle(self):
        active = self._app.get("ActiveDoc")
        if active is None:
            return None
        try:
            return active.call("GetTitle")
        finally:
            active.release()

    def _activate(self, title: str) -> None:
        errors = ctypes.c_long(0)
        model = self._app.call("ActivateDoc3", title, False, SolidWorksEnums.swRebuildOnActivation_e.swDontRebuildActiveDoc, ctypes.byref(errors))
        if model is None:
            raise SolidWorksError("SolidWorks could not activate {} (swActivateDocError_e {}).".format(title, errors.value))
        model.release()

    def export(self, document: SolidWorksDocument, target_path: str, quality: str = QUALITY_FINE) -> None:
        """Save ``document`` as STL or 3MF (by the extension of ``target_path``), in millimetres.

        The export options this needs are global SolidWorks preferences, so they are changed only for the duration of
        the save and then restored.
        """

        file_format = os.path.splitext(target_path)[1].lower()
        restore_steps = []

        def setToggle(preference, value):
            restore_steps.append(("SetUserPreferenceToggle", preference, self._app.call("GetUserPreferenceToggle", preference)))
            self._app.call("SetUserPreferenceToggle", preference, value)

        def setInteger(preference, value):
            restore_steps.append(("SetUserPreferenceIntegerValue", preference, self._app.call("GetUserPreferenceIntegerValue", preference)))
            self._app.call("SetUserPreferenceIntegerValue", preference, value)

        def setQuality(quality_value):
            previous = self._app.call("GetUserPreferenceIntegerValue", _INTEGER.swSTLQuality)
            if previous == _QUALITY.swSTLQuality_Custom:
                # "Custom" can't be set directly; it comes back by restoring the tolerances it consists of.
                for preference in (_DOUBLE.swSTLDeviation, _DOUBLE.swSTLAngleTolerance):
                    restore_steps.append(("SetUserPreferenceDoubleValue", preference, self._app.call("GetUserPreferenceDoubleValue", preference)))
            else:
                restore_steps.append(("SetUserPreferenceIntegerValue", _INTEGER.swSTLQuality, previous))
            self._app.call("SetUserPreferenceIntegerValue", _INTEGER.swSTLQuality, quality_value)

        try:
            # These options also drive the 3MF tessellation.
            if quality in _QUALITY_VALUES:
                setQuality(_QUALITY_VALUES[quality])
            if file_format == ".stl":
                setToggle(_TOGGLE.swSTLBinaryFormat, True)
                setToggle(_TOGGLE.swSTLShowInfoOnSave, False)
                setToggle(_TOGGLE.swSTLPreview, False)
                setInteger(_INTEGER.swExportStlUnits, SolidWorksEnums.swLengthUnit_e.swMM)
                if document.is_assembly:
                    setToggle(_TOGGLE.swSTLComponentsIntoOneFile, True)
            elif file_format == ".3mf":
                if not self.supports3mf():
                    raise SolidWorksError("{} can't save 3MF files.".format(self.friendly_name))
                setToggle(_TOGGLE.sw3MFShowInfoOnSave, False)
            else:
                raise SolidWorksError("Unsupported export format: {}".format(file_format))

            # Mesh exports write out SolidWorks' *active* document, whichever document SaveAs3 is called on. A document
            # that was opened in the background therefore has to be activated first, or the export silently contains
            # the geometry of whatever the user was looking at.
            active_title = self._activeTitle()
            if active_title != document.title:
                if document.previously_active_title is None:
                    document.previously_active_title = active_title
                self._activate(document.title)

            options = SolidWorksEnums.swSaveAsOptions_e.swSaveAsOptions_Silent | SolidWorksEnums.swSaveAsOptions_e.swSaveAsOptions_Copy
            error = document.model.call("SaveAs3", target_path, SolidWorksEnums.swSaveAsVersion_e.swSaveAsCurrentVersion, options)
        finally:
            for method, preference, value in reversed(restore_steps):
                try:
                    self._app.call(method, preference, value)
                except Exception as e:
                    self._log("e", "Could not restore SolidWorks preference %s (%s) to %s: %s", preference, method, value, e)

        if error or not os.path.isfile(target_path) or os.path.getsize(target_path) == 0:
            raise SolidWorksError("SolidWorks could not save {} as {}: {}.".format(
                os.path.basename(document.path), file_format[1:].upper(),
                SolidWorksEnums.describeBits(error or 1, SolidWorksEnums.file_save_errors)))
