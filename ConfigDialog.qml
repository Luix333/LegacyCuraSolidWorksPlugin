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

    title: catalog.i18nc("@title:window", "SolidWorks Integration Settings")

    minimumWidth: UM.Theme.getSize("modal_window_minimum").width
    minimumHeight: grid.implicitHeight + UM.Theme.getSize("default_margin").height * 6 + UM.Theme.getSize("button").height
    width: minimumWidth
    height: minimumHeight

    readonly property var qualityChoices: [
        { text: catalog.i18nc("@item:inlistbox", "Ask every time"), code: "always_ask" },
        { text: catalog.i18nc("@item:inlistbox", "Fine"), code: "always_use_fine" },
        { text: catalog.i18nc("@item:inlistbox", "Coarse"), code: "always_use_coarse" },
        { text: catalog.i18nc("@item:inlistbox", "As set in SolidWorks (Options > Export > STL)"), code: "always_use_solidworks" }
    ]
    readonly property var formatChoices: [
        { text: catalog.i18nc("@item:inlistbox", "3MF: keeps bodies and assembly parts as separate objects"), code: "3mf" },
        { text: catalog.i18nc("@item:inlistbox", "STL: one mesh for the whole file"), code: "stl" }
    ]

    function indexOf(choices, code)
    {
        for (var i = 0; i < choices.length; ++i)
        {
            if (choices[i].code == code)
            {
                return i;
            }
        }
        return 0;
    }

    onVisibleChanged:
    {
        if (visible)
        {
            qualityBox.currentIndex = indexOf(qualityChoices, UM.Preferences.getValue("cura_solidworks/choice_on_exporting_stl_quality"));
            formatBox.currentIndex = indexOf(formatChoices, UM.Preferences.getValue("cura_solidworks/transfer_format"));
        }
    }

    GridLayout
    {
        id: grid
        UM.I18nCatalog { id: catalog; name: "cura" }
        anchors.fill: parent
        columns: 2
        columnSpacing: UM.Theme.getSize("default_margin").width
        rowSpacing: UM.Theme.getSize("default_margin").height

        UM.Label { text: catalog.i18nc("@label", "Mesh resolution") }
        Cura.ComboBox
        {
            id: qualityBox
            Layout.fillWidth: true
            Layout.preferredHeight: UM.Theme.getSize("setting_control").height
            textRole: "text"
            model: base.qualityChoices
        }

        UM.Label { text: catalog.i18nc("@label", "Transfer format") }
        Cura.ComboBox
        {
            id: formatBox
            Layout.fillWidth: true
            Layout.preferredHeight: UM.Theme.getSize("setting_control").height
            textRole: "text"
            model: base.formatChoices
        }

        UM.Label
        {
            Layout.columnSpan: 2
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            color: UM.Theme.getColor("text_medium")
            text: catalog.i18nc("@label", "SolidWorks 2016 and older can only save STL; the other format is also used as a fallback when the preferred one fails.")
        }
    }

    onAccepted:
    {
        UM.Preferences.setValue("cura_solidworks/choice_on_exporting_stl_quality", qualityChoices[qualityBox.currentIndex].code);
        UM.Preferences.setValue("cura_solidworks/transfer_format", formatChoices[formatBox.currentIndex].code);
    }

    buttonSpacing: UM.Theme.getSize("default_margin").width

    rightButtons: [
        Cura.TertiaryButton
        {
            text: catalog.i18nc("@action:button", "Cancel")
            onClicked: base.reject()
        },
        Cura.PrimaryButton
        {
            text: catalog.i18nc("@action:button", "Save")
            onClicked: base.accept()
        }
    ]
}
