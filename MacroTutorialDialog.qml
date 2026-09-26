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

    title: catalog.i18nc("@title:window", "How to add the \"Export to Cura\" button to SolidWorks")

    minimumWidth: Math.round(1000 * screenScaleFactor)
    minimumHeight: Math.round(620 * screenScaleFactor)
    width: minimumWidth
    height: minimumHeight

    property int currentStep: 0
    readonly property bool lastStep: currentStep == steps.count - 1

    onVisibleChanged:
    {
        if (visible)
        {
            currentStep = 0;
        }
    }

    RowLayout
    {
        UM.I18nCatalog { id: catalog; name: "cura" }

        // Steps of the tutorial; lives here because UM.Dialog's own children must be Items.
        ListModel
        {
            id: steps
            ListElement
            {
                title: "Open SolidWorks"
                description: "Start SolidWorks and open any part or assembly."
                gif: "1_start_solidworks.gif"
            }
            ListElement
            {
                title: "Open the Customize dialog"
                description: "Choose Tools > Customize, or right-click a toolbar and choose Customize."
                gif: "2_open_customize_dialog.gif"
            }
            ListElement
            {
                title: "Go to Commands > Macro"
                description: "Switch to the Commands tab and pick the Macro category."
                gif: "3_switch_to_macro.gif"
            }
            ListElement
            {
                title: "Add a New Macro Button"
                description: "Drag the New Macro Button icon onto a toolbar. In the dialog that opens, choose Export_to_Cura.swb as the macro (the animation still shows the old .swp file) and cura-icon_20x20.bmp as the icon; the Open macro folder button on the left shows both files. If SolidWorks asks for a method, choose main."
                gif: "4_add_new_macro_button.gif"
            }
            ListElement
            {
                title: "Done!"
                description: "The new button opens the active part or assembly in Cura, including changes you haven't saved yet. A document that was never saved has to be saved once first, because Cura opens it through its file. When Cura is already running, the file opens in that window if \"Use a single instance of Cura\" is on in Cura's preferences."
                gif: "5_done.gif"
            }
        }

        anchors.fill: parent
        spacing: UM.Theme.getSize("default_margin").width * 2

        ColumnLayout
        {
            Layout.preferredWidth: Math.round(base.width / 5)
            Layout.maximumWidth: Math.round(base.width / 5)
            Layout.fillHeight: true
            spacing: UM.Theme.getSize("default_margin").height

            UM.Label
            {
                text: catalog.i18nc("@label", "Steps")
                font: UM.Theme.getFont("large_bold")
            }

            Repeater
            {
                model: steps

                UM.Label
                {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    text: (index + 1) + ". " + catalog.i18nc("@label", model.title)
                    font: index == base.currentStep ? UM.Theme.getFont("default_bold") : UM.Theme.getFont("default")

                    MouseArea
                    {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: base.currentStep = index
                    }
                }
            }

            Item { Layout.fillHeight: true }

            Cura.SecondaryButton
            {
                Layout.fillWidth: true
                text: catalog.i18nc("@action:button", "Open macro folder")
                onClicked: manager.openMacroAndIconDirectory()
            }
        }

        ColumnLayout
        {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: UM.Theme.getSize("default_margin").height

            UM.Label
            {
                text: catalog.i18nc("@label", "Instructions")
                font: UM.Theme.getFont("large_bold")
            }

            UM.Label
            {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: catalog.i18nc("@label", steps.get(base.currentStep).description)
            }

            AnimatedImage
            {
                id: animation
                Layout.fillWidth: true
                Layout.fillHeight: true
                fillMode: Image.PreserveAspectFit
                source: "macro/tutorial/" + steps.get(base.currentStep).gif
                playing: true
            }

            RowLayout
            {
                Layout.fillWidth: true
                spacing: UM.Theme.getSize("default_margin").width

                Cura.SecondaryButton
                {
                    text: animation.playing ? catalog.i18nc("@action:button", "Pause") : catalog.i18nc("@action:button", "Play")
                    onClicked: animation.playing = !animation.playing
                }

                Slider
                {
                    Layout.fillWidth: true
                    from: 0
                    to: Math.max(animation.frameCount - 1, 0)
                    stepSize: 1
                    value: animation.currentFrame
                    onMoved:
                    {
                        animation.playing = false;
                        animation.currentFrame = value;
                    }
                }
            }
        }
    }

    buttonSpacing: UM.Theme.getSize("default_margin").width

    rightButtons: [
        Cura.TertiaryButton
        {
            text: catalog.i18nc("@action:button", "Previous Step")
            enabled: base.currentStep > 0
            onClicked: base.currentStep -= 1
        },
        Cura.PrimaryButton
        {
            text: base.lastStep ? catalog.i18nc("@action:button", "Done") : catalog.i18nc("@action:button", "Next Step")
            onClicked:
            {
                if (base.lastStep)
                {
                    base.accept();
                }
                else
                {
                    base.currentStep += 1;
                }
            }
        }
    ]
}
