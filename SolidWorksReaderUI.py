# Copyright (c) 2017 Ultimaker B.V.
# Copyright (c) 2026 CuraSolidWorksPlugin contributors
# CuraSolidWorksPlugin is released under the terms of the LGPLv3 or higher.

import os
import threading

from PyQt6.QtCore import QCoreApplication, QObject, QThread, pyqtSignal, pyqtSlot

from UM.Application import Application
from UM.Logger import Logger

from .SolidWorksSession import QUALITY_FINE, QUALITY_COARSE, QUALITY_SOLIDWORKS

QUALITY_PREFERENCE = "cura_solidworks/choice_on_exporting_stl_quality"
ALWAYS_ASK = "always_ask"
_REMEMBERED_QUALITIES = {"always_use_fine": QUALITY_FINE,
                         "always_use_coarse": QUALITY_COARSE,
                         "always_use_solidworks": QUALITY_SOLIDWORKS}


class SolidWorksReaderUI(QObject):
    """Asks which mesh resolution to convert with, unless the user told us to remember it.

    askQuality() is called from the job thread that loads the file and blocks it until the dialog, which has to live
    on the GUI thread, is closed.
    """

    _showDialogRequested = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        Application.getInstance().getPreferences().addPreference(QUALITY_PREFERENCE, ALWAYS_ASK)

        self._dialog = None
        self._dialog_lock = threading.Lock()  # One dialog at a time when several files are opened together.
        self._dialog_closed = threading.Event()
        self._answer = None
        self._waiting = False  # Whether a dialog is out; the first of OK/Cancel/Escape/closing the window counts.
        self._showDialogRequested.connect(self._showDialog)

    def rememberedQuality(self):
        """The quality to use without asking, or None if the user wants to be asked."""

        choice = Application.getInstance().getPreferences().getValue(QUALITY_PREFERENCE)
        return _REMEMBERED_QUALITIES.get(choice)

    def askQuality(self, file_name: str):
        """The quality for converting ``file_name``, or None if the user cancelled."""

        if self.rememberedQuality():
            return self.rememberedQuality()
        if QThread.currentThread() == QCoreApplication.instance().thread():
            Logger.log("w", "Can't wait for the SolidWorks quality dialog on the GUI thread, using fine quality.")
            return QUALITY_FINE

        with self._dialog_lock:
            remembered = self.rememberedQuality()  # The previous dialog may just have been told to remember.
            if remembered:
                return remembered
            self._answer = None
            self._waiting = True
            self._dialog_closed.clear()
            self._showDialogRequested.emit(file_name)
            self._dialog_closed.wait()
            return self._answer

    def _showDialog(self, file_name: str) -> None:
        if self._dialog is None:
            plugin_path = os.path.dirname(os.path.abspath(__file__))
            self._dialog = Application.getInstance().createQmlComponent(os.path.join(plugin_path, "ExportSTLUI.qml"), {"manager": self})
        if self._dialog is None:
            Logger.log("e", "Could not create the SolidWorks quality dialog, using fine quality.")
            self._finish(QUALITY_FINE)
            return
        self._dialog.setProperty("fileName", file_name)
        self._dialog.show()

    def _finish(self, answer) -> None:
        if not self._waiting:
            return
        self._waiting = False
        self._answer = answer
        if self._dialog is not None:
            self._dialog.hide()  # Not close(): that would come back to us as the window's closing signal.
        self._dialog_closed.set()

    @pyqtSlot(str, bool)
    def accept(self, quality: str, remember: bool) -> None:
        if not self._waiting:
            return
        if remember:
            choice = next((key for key, value in _REMEMBERED_QUALITIES.items() if value == quality), ALWAYS_ASK)
            Application.getInstance().getPreferences().setValue(QUALITY_PREFERENCE, choice)
        self._finish(quality)

    @pyqtSlot()
    def cancel(self) -> None:
        self._finish(None)
