// Copyright (c) 2017 Ultimaker B.V.
// Copyright (c) 2026 CuraSolidWorksPlugin contributors
// CuraSolidWorksPlugin is released under the terms of the LGPLv3 or higher.

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.3

import UM 1.5 as UM
import Cura 1.0 as Cura

UM.Dialog
{
    id: base

    property string fileName: ""

    title: catalog.i18nc("@title:window", "Open SolidWorks File")

    minimumWidth: UM.Theme.getSize("modal_window_minimum").width * 0.75
    minimumHeight: content.implicitHeight + UM.Theme.getSize("default_margin").height * 6 + UM.Theme.getSize("button").height
    width: minimumWidth
    height: minimumHeight

    onVisibleChanged:
    {
        if (visible)
        {
            qualityBox.currentIndex = 0;
            rememberBox.checked = false;
        }
    }

    ColumnLayout
    {
        id: content
        UM.I18nCatalog { id: catalog; name: "cura" }
        anchors.fill: parent
        spacing: UM.Theme.getSize("default_margin").height

        UM.Label
        {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: catalog.i18nc("@label", "SolidWorks will convert <b>%1</b> into a mesh for Cura. Which mesh resolution should it use?").arg(base.fileName)
        }

        Cura.ComboBox
        {
            id: qualityBox
            objectName: "qualityBox"
            Layout.fillWidth: true
            Layout.preferredHeight: UM.Theme.getSize("setting_control").height
            textRole: "text"
            model: [
                { text: catalog.i18nc("@item:inlistbox", "Fine"), code: "fine" },
                { text: catalog.i18nc("@item:inlistbox", "Coarse"), code: "coarse" },
                { text: catalog.i18nc("@item:inlistbox", "As set in SolidWorks (Options > Export > STL)"), code: "solidworks" }
            ]
        }

        UM.CheckBox
        {
            id: rememberBox
            objectName: "rememberBox"
            text: catalog.i18nc("@option:check", "Remember my choice (change it later under Extensions > SolidWorks Integration > Configure)")
        }
    }

    onAccepted: manager.accept(qualityBox.model[qualityBox.currentIndex].code, rememberBox.checked)
    onRejected: manager.cancel()
    onClosing: manager.cancel()

    buttonSpacing: UM.Theme.getSize("default_margin").width

    rightButtons: [
        Cura.TertiaryButton
        {
            text: catalog.i18nc("@action:button", "Cancel")
            onClicked: base.reject()
        },
        Cura.PrimaryButton
        {
            text: catalog.i18nc("@action:button", "Open")
            onClicked: base.accept()
        }
    ]
}
