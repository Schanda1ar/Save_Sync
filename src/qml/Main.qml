import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ApplicationWindow {
    id: window
    width: 1040
    height: 760
    visible: true
    title: "Save Sync"
    color: "#0f1722"

    property bool darkMode: true
    property color pageStart: "#0f1722"
    property color pageEnd: "#1b2635"
    property color sidebarBg: "#121a24"
    property color sidebarPanelBg: "#1a2432"
    property color contentBg: "#1a2230"
    property color titleText: "#f5f7fb"
    property color bodyText: "#eef3f8"
    property color mutedText: "#c8d0da"
    property color controlBg: "#d7dde5"
    property color controlBorder: "#91a0b2"
    property color buttonBg: "#cfd6df"
    property color buttonHoverBg: "#dce2e9"
    property color dangerBg: "#b98686"
    property color dangerHoverBg: "#c99595"
    property color buttonText: "#111827"
    property color controlText: "#111827"
    property var selectedData: controller.selectedProfileData

    function syncComboSelection() {
        if (controller.profileOptions.length === 0) {
            profileCombo.currentIndex = -1
            return
        }
        var selectedId = controller.selectedProfileId
        if (!selectedId) {
            profileCombo.currentIndex = -1
            return
        }
        for (var i = 0; i < controller.profileOptions.length; i++) {
            if (controller.profileOptions[i].id === selectedId) {
                profileCombo.currentIndex = i
                return
            }
        }
        profileCombo.currentIndex = 0
    }

    function reloadForm() {
        selectedData = controller.selectedProfileData
        idField.text = selectedData.id || ""
        nameField.text = selectedData.display_name || ""
        exeField.text = selectedData.game_exe_path || ""
        saveField.text = selectedData.save_folder_path || ""
        processField.text = selectedData.game_process_names || ""
        driveFileField.text = selectedData.drive_filename || ""
        driveFolderField.text = selectedData.drive_folder_id || ""
    }

    Component.onCompleted: {
        reloadForm()
        syncComboSelection()
    }

    Connections {
        target: controller
        function onSelectedProfileDataChanged() { window.reloadForm() }
        function onProfilesChanged() { window.syncComboSelection() }
        function onSelectedProfileIdChanged() { window.syncComboSelection() }
    }

    ToolTip {
        id: hoverTip
        delay: 300
        timeout: 5000
    }

    FileDialog {
        id: importDialog
        title: "Profile importieren"
        nameFilters: ["JSON files (*.json)"]
        onAccepted: controller.importProfiles(selectedFile.toString())
    }

    FileDialog {
        id: exportDialog
        title: "Profile exportieren"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "json"
        nameFilters: ["JSON files (*.json)"]
        onAccepted: controller.exportProfiles(selectedFile.toString())
    }

    FileDialog {
        id: exeDialog
        title: "Spiel-EXE auswählen"
        onAccepted: exeField.text = controller.fileUrlToPath(selectedFile.toString())
    }

    FolderDialog {
        id: saveFolderDialog
        title: "Save-Ordner auswählen"
        onAccepted: saveField.text = controller.fileUrlToPath(selectedFolder.toString())
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: pageStart }
            GradientStop { position: 1.0; color: pageEnd }
        }

        RowLayout {
            anchors.fill: parent
            anchors.margins: 24
            spacing: 24

            Rectangle {
                Layout.preferredWidth: 320
                Layout.fillHeight: true
                radius: 24
                color: sidebarBg

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 16

                    Label {
                        text: "Spielauswahl"
                        color: titleText
                        font.pixelSize: 28
                        font.bold: true
                    }

                    Label {
                        text: "Profil wählen"
                        color: mutedText
                    }

                    ComboBox {
                        id: profileCombo
                        Layout.fillWidth: true
                        model: controller.profileOptions
                        textRole: "display_name"
                        hoverEnabled: true
                        onActivated: controller.selectProfileIndex(currentIndex)
                        palette.button: controlBg
                        palette.base: controlBg
                        palette.text: controlText
                        palette.buttonText: controlText

                        ToolTip.visible: hovered
                        ToolTip.text: "Wählt das aktive Spielprofil aus, das gestartet und synchronisiert wird."
                    }

                    Button {
                        id: saveProfileButton
                        Layout.fillWidth: true
                        text: "Profil speichern"
                        onClicked: controller.saveProfile(
                            idField.text,
                            nameField.text,
                            exeField.text,
                            saveField.text,
                            processField.text,
                            driveFileField.text,
                            driveFolderField.text
                        )
                        background: Rectangle {
                            radius: 12
                            color: saveProfileButton.hovered ? buttonHoverBg : buttonBg
                            border.color: controlBorder
                            border.width: 1
                        }
                        contentItem: Text {
                            text: saveProfileButton.text
                            color: buttonText
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.bold: true
                        }
                    }

                    Button {
                        id: newProfileButton
                        Layout.fillWidth: true
                        text: "Neues Profil"
                        onClicked: {
                            controller.clearSelection()
                            window.reloadForm()
                        }
                        background: Rectangle {
                            radius: 12
                            color: newProfileButton.hovered ? buttonHoverBg : buttonBg
                            border.color: controlBorder
                            border.width: 1
                        }
                        contentItem: Text {
                            text: newProfileButton.text
                            color: buttonText
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.bold: true
                        }
                    }

                    Button {
                        id: duplicateProfileButton
                        Layout.fillWidth: true
                        text: "Profil kopieren"
                        onClicked: controller.duplicateSelectedProfile()
                        background: Rectangle {
                            radius: 12
                            color: duplicateProfileButton.hovered ? buttonHoverBg : buttonBg
                            border.color: controlBorder
                            border.width: 1
                        }
                        contentItem: Text {
                            text: duplicateProfileButton.text
                            color: buttonText
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.bold: true
                        }
                    }

                    Button {
                        id: importButton
                        Layout.fillWidth: true
                        text: "Import JSON"
                        onClicked: importDialog.open()
                        background: Rectangle {
                            radius: 12
                            color: importButton.hovered ? buttonHoverBg : buttonBg
                            border.color: controlBorder
                            border.width: 1
                        }
                        contentItem: Text {
                            text: importButton.text
                            color: buttonText
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.bold: true
                        }
                    }

                    Button {
                        id: exportButton
                        Layout.fillWidth: true
                        text: "Export JSON"
                        onClicked: exportDialog.open()
                        background: Rectangle {
                            radius: 12
                            color: exportButton.hovered ? buttonHoverBg : buttonBg
                            border.color: controlBorder
                            border.width: 1
                        }
                        contentItem: Text {
                            text: exportButton.text
                            color: buttonText
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.bold: true
                        }
                    }

                    Button {
                        id: deleteButton
                        Layout.fillWidth: true
                        text: "Profil löschen"
                        onClicked: controller.deleteSelectedProfile()
                        background: Rectangle {
                            radius: 12
                            color: deleteButton.hovered ? dangerHoverBg : dangerBg
                            border.color: controlBorder
                            border.width: 1
                        }
                        contentItem: Text {
                            text: deleteButton.text
                            color: "#1f1111"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.bold: true
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 18
                        color: sidebarPanelBg
                        clip: true

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 8

                            Label {
                                text: "Status"
                                color: titleText
                                font.bold: true
                            }

                            Flickable {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                contentWidth: width
                                contentHeight: statusText.implicitHeight
                                boundsBehavior: Flickable.StopAtBounds
                                interactive: contentHeight > height

                                Text {
                                    id: statusText
                                    x: 2
                                    width: parent.width - 4
                                    text: controller.statusMessage
                                    color: mutedText
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 24
                color: contentBg

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 12

                    Label {
                        text: "Profil bearbeiten"
                        color: titleText
                        font.pixelSize: 26
                        font.bold: true
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 3
                        columnSpacing: 12
                        rowSpacing: 10

                        Label { text: "Profil-ID"; color: bodyText }
                        TextField {
                            id: idField
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            readOnly: true
                            hoverEnabled: true
                            placeholderText: "Wird automatisch erzeugt"
                            color: controlText
                            placeholderTextColor: "#586270"
                            background: Rectangle {
                                radius: 10
                                color: controlBg
                                border.color: controlBorder
                                border.width: 1
                            }

                            ToolTip.visible: hovered
                            ToolTip.text: "Die Profil-ID wird automatisch erstellt und dient als interne eindeutige Kennung."
                        }

                        Label { text: "Anzeigename"; color: bodyText }
                        TextField {
                            id: nameField
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            hoverEnabled: true
                            placeholderText: "z. B. Elden Ring"
                            color: controlText
                            placeholderTextColor: "#586270"
                            background: Rectangle {
                                radius: 10
                                color: controlBg
                                border.color: controlBorder
                                border.width: 1
                            }

                            ToolTip.visible: hovered
                            ToolTip.text: "Name des Spiels, wie es in der Auswahlliste und im Profil angezeigt wird."
                        }

                        Label { text: "Spielstart"; color: bodyText }
                        TextField {
                            id: exeField
                            Layout.fillWidth: true
                            hoverEnabled: true
                            placeholderText: "EXE-Pfad oder Steam-ID"
                            color: controlText
                            placeholderTextColor: "#586270"
                            background: Rectangle {
                                radius: 10
                                color: controlBg
                                border.color: controlBorder
                                border.width: 1
                            }

                            ToolTip.visible: hovered
                            ToolTip.text: "Lokalen EXE-Pfad eintragen oder bei Steam-Spielen nur die numerische Spiel-ID eingeben."
                        }
                        Button {
                            id: exePickButton
                            text: "EXE wählen"
                            onClicked: exeDialog.open()
                            background: Rectangle {
                                radius: 10
                                color: exePickButton.hovered ? buttonHoverBg : buttonBg
                                border.color: controlBorder
                                border.width: 1
                            }
                            contentItem: Text {
                                text: exePickButton.text
                                color: buttonText
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }

                        Label { text: "Save-Ordner"; color: bodyText }
                        TextField {
                            id: saveField
                            Layout.fillWidth: true
                            hoverEnabled: true
                            placeholderText: "Pfad zum Save-Ordner"
                            color: controlText
                            placeholderTextColor: "#586270"
                            background: Rectangle {
                                radius: 10
                                color: controlBg
                                border.color: controlBorder
                                border.width: 1
                            }

                            ToolTip.visible: hovered
                            ToolTip.text: "Ordner mit allen Save-Dateien des Spiels."
                        }
                        Button {
                            id: saveFolderButton
                            text: "Ordner wählen"
                            onClicked: saveFolderDialog.open()
                            background: Rectangle {
                                radius: 10
                                color: saveFolderButton.hovered ? buttonHoverBg : buttonBg
                                border.color: controlBorder
                                border.width: 1
                            }
                            contentItem: Text {
                                text: saveFolderButton.text
                                color: buttonText
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }

                        Label { text: "Prozessnamen"; color: bodyText }
                        TextField {
                            id: processField
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            hoverEnabled: true
                            placeholderText: "Game.exe, Launcher.exe"
                            color: controlText
                            placeholderTextColor: "#586270"
                            background: Rectangle {
                                radius: 10
                                color: controlBg
                                border.color: controlBorder
                                border.width: 1
                            }

                            ToolTip.visible: hovered
                            ToolTip.text: "Kommagetrennte Prozessnamen, über die erkannt wird, ob das Spiel noch läuft."
                        }

                        Label { text: "Drive-Archivname"; color: bodyText }
                        TextField {
                            id: driveFileField
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            hoverEnabled: true
                            placeholderText: "savegame"
                            color: controlText
                            placeholderTextColor: "#586270"
                            background: Rectangle {
                                radius: 10
                                color: controlBg
                                border.color: controlBorder
                                border.width: 1
                            }

                            ToolTip.visible: hovered
                            ToolTip.text: "Name des Archivs in Google Drive."
                        }

                        Label { text: "Drive-Ordner-ID"; color: bodyText }
                        TextField {
                            id: driveFolderField
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            hoverEnabled: true
                            placeholderText: "Optional"
                            color: controlText
                            placeholderTextColor: "#586270"
                            background: Rectangle {
                                radius: 10
                                color: controlBg
                                border.color: controlBorder
                                border.width: 1
                            }

                            ToolTip.visible: hovered
                            ToolTip.text: "Optionaler Zielordner in Google Drive. Leer bedeutet, dass der Standardort verwendet wird."
                        }
                    }

                    Item { Layout.fillHeight: true }

                    Button {
                        id: startButton
                        Layout.alignment: Qt.AlignRight
                        Layout.minimumWidth: 260
                        text: controller.busy ? "Läuft..." : "Spiel starten"
                        enabled: !controller.busy
                        implicitHeight: 68
                        onClicked: controller.startSelectedGame()
                        background: Rectangle {
                            radius: 12
                            color: startButton.hovered ? buttonHoverBg : buttonBg
                            border.color: controlBorder
                            border.width: 1
                        }
                        contentItem: Text {
                            text: startButton.text
                            color: buttonText
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.bold: true
                            font.pixelSize: 18
                        }
                    }
                }
            }
        }
    }
}
