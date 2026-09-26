# Copyright (c) 2017 Ultimaker B.V.
# Copyright (c) 2026 CuraSolidWorksPlugin contributors
# CuraSolidWorksPlugin is released under the terms of the LGPLv3 or higher.

import os

from PyQt6.QtCore import QObject, QUrl, pyqtSlot
from PyQt6.QtGui import QDesktopServices

from UM.Application import Application
from UM.Extension import Extension
from UM.i18n import i18nCatalog
from UM.Logger import Logger

i18n_catalog = i18nCatalog("cura")

_PLUGIN_PATH = os.path.dirname(os.path.abspath(__file__))


class DialogHandler(QObject, Extension):
    """The plugin's entries in the Extensions menu."""

    def __init__(self, parent = None) -> None:
        QObject.__init__(self, parent)
        Extension.__init__(self)
        self._dialogs = {}
        self.setMenuName(i18n_catalog.i18nc("@item:inmenu", "SolidWorks Integration"))
        self.addMenuItem(i18n_catalog.i18nc("@item:inmenu", "Configure"), lambda: self._openDialog("ConfigDialog.qml"))
        self.addMenuItem(i18n_catalog.i18nc("@item:inmenu", "How to install the SolidWorks macro"), lambda: self._openDialog("MacroTutorialDialog.qml"))

    def _openDialog(self, qml_file: str) -> None:
        dialog = self._dialogs.get(qml_file)
        if dialog is None:
            dialog = Application.getInstance().createQmlComponent(os.path.join(_PLUGIN_PATH, qml_file), {"manager": self})
            if dialog is None:
                Logger.log("e", "Could not create %s.", qml_file)
                return
            self._dialogs[qml_file] = dialog
        dialog.show()

    @pyqtSlot()
    def openMacroAndIconDirectory(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.join(_PLUGIN_PATH, "macro")))
