# Copyright (c) 2016 Thomas Karl Pietrowski
# Copyright (c) 2026 CuraSolidWorksPlugin contributors
# CuraSolidWorksPlugin is released under the terms of the LGPLv3 or higher.

from UM.Logger import Logger
from UM.Platform import Platform

from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("cura")


def getMetaData():
    return {
        "mesh_reader":
        [
            {
                "extension": "SLDPRT",
                "description": i18n_catalog.i18nc("@item:inlistbox", "SolidWorks part file")
            },
            {
                "extension": "SLDASM",
                "description": i18n_catalog.i18nc("@item:inlistbox", "SolidWorks assembly file")
            }
        ]
    }


def register(app):
    if not Platform.isWindows():
        Logger.log("i", "SolidWorks only runs on Windows; the SolidWorks Integration plugin has nothing to do here.")
        return {}

    # Imported here, on the main thread, and only on Windows: this pulls in the bundled comtypes (see ComAutomation).
    from . import SolidWorksReader
    from .DialogHandler import DialogHandler

    plugin_data = {"extension": DialogHandler()}
    if SolidWorksReader.isSolidWorksInstalled():
        plugin_data["mesh_reader"] = SolidWorksReader.SolidWorksReader()
    else:
        Logger.log("w", "SolidWorks is not installed (no %s COM class), so SolidWorks files can't be opened.", SolidWorksReader.PROG_ID)
    return plugin_data
