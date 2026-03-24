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
    color: darkMode ? "#0f1722" : "#f4efe7"

    property bool darkMode: controller.darkMode
    property color pageStart: darkMode ? "#0f1722" : "#f7f1e7"
    property color pageEnd: darkMode ? "#1b2635" : "#dfebf4"
    property color sidebarBg: darkMode ? "#121a24" : "#1f2f3d"
    property color sidebarPanelBg: darkMode ? "#1a2432" : "#304657"
    property color contentBg: darkMode ? "#1a2230" : "#fffaf2"
    property color titleText: darkMode ? "#f3f6fa" : "#1c2730"
    property color bodyText: darkMode ? "#eef3f8" : "#1c2730"
    property color mutedText: darkMode ? "#c8d0da" : "#6a7685"
    property color controlBg: darkMode ? "#18202d" : "#ffffff"
    property color controlBorder: darkMode ? "#506279" : "#b9c5d0"
    property color buttonBg: darkMode ? "#273547" : "#e9eff5"
    property color buttonHoverBg: darkMode ? "#314357" : "#dce8f4"
    property color dangerBg: darkMode ? "#5a3131" : "#f4dede"
    property color dangerHoverBg: darkMode ? "#6f3b3b" : "#f0caca"
    property color buttonText: darkMode ? "#f3f6fa" : "#1c2730"

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
        saveField.text = selectedData.save_file_path || ""
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
        title: "Spiel-Executable auswählen"
        onAccepted: exeField.text = controller.fileUrlToPath(selectedFile.toString())
    }

    FileDialog {
        id: saveDialog
        title: "Save-Datei auswählen"
        onAccepted: saveField.text = controller.fileUrlToPath(selectedFile.toString())
    }

    FolderDialog {
        id: saveFolderDialog
        title: "Save-Ordner ausw?hlen"
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

                    Button {
                        id: toggleThemeButton
                        Layout.fillWidth: true
                        Layout.preferredHeight: 36
                        text: darkMode ? "Lightmode" : "Darkmode"
                        onClicked: controller.toggleTheme()
                        background: Rectangle {
                            radius: 12
                            color: toggleThemeButton.hovered ? buttonHoverBg : buttonBg
                            border.color: controlBorder
                            border.width: 1
                        }
                        contentItem: Text {
                            text: toggleThemeButton.text
                            color: buttonText
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.bold: true
                            elide: Text.ElideRight
                        }
                    }

                    ComboBox {
                        id: profileCombo
                        Layout.fillWidth: true
                        model: controller.profileOptions
                        textRole: "display_name"
                        onActivated: controller.selectProfileIndex(currentIndex)
                    }

                    Button {
                        Layout.fillWidth: true
                        text: controller.busy ? "Läuft..." : "Spiel starten"
                        enabled: !controller.busy
                        onClicked: controller.startSelectedGame()
                    }

                    Button {
                        Layout.fillWidth: true
                        text: "Neues Profil"
                        onClicked: {
                            controller.clearSelection()
                            window.reloadForm()
                        }
                    }

                    Button {
                        Layout.fillWidth: true
                        text: "Import JSON"
                        onClicked: importDialog.open()
                    }

                    Button {
                        Layout.fillWidth: true
                        text: "Export JSON"
                        onClicked: exportDialog.open()
                    }

                    Button {
                        Layout.fillWidth: true
                        text: "Profil löschen"
                        onClicked: controller.deleteSelectedProfile()
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 18
                        color: sidebarPanelBg

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 8

                            Label {
                                text: "Status"
                                color: titleText
                                font.bold: true
                            }

                            Label {
                                Layout.fillWidth: true
                                text: controller.statusMessage
                                color: mutedText
                                wrapMode: Text.WordWrap
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
                            placeholderText: "Wird automatisch erzeugt"
                        }

                        Label { text: "Anzeigename"; color: bodyText }
                        TextField {
                            id: nameField
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            placeholderText: "z. B. Elden Ring"
                        }

                        Label { text: "Spiel-Executable"; color: bodyText }
                        TextField {
                            id: exeField
                            Layout.fillWidth: true
                            placeholderText: "Pfad zur EXE"
                        }
                        Button {
                            text: "Datei wählen"
                            onClicked: exeDialog.open()
                        }

                        Label { text: "Save-Datei oder Ordner"; color: bodyText }
                        TextField {
                            id: saveField
                            Layout.fillWidth: true
                            placeholderText: "Pfad zur Save-Datei oder zum Save-Ordner"
                        }
                        RowLayout {
                            spacing: 8

                            Button {
                                text: "Datei"
                                onClicked: saveDialog.open()
                            }

                            Button {
                                text: "Ordner"
                                onClicked: saveFolderDialog.open()
                            }
                        }

                        Label { text: "Prozessnamen"; color: bodyText }
                        TextField {
                            id: processField
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            placeholderText: "Game.exe, Launcher.exe"
                        }

                        Label { text: "Drive-Dateiname"; color: bodyText }
                        TextField {
                            id: driveFileField
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            placeholderText: "save.sav"
                        }

                        Label { text: "Drive-Ordner-ID"; color: bodyText }
                        TextField {
                            id: driveFolderField
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            placeholderText: "Optional"
                        }
                    }

                    Item { Layout.fillHeight: true }

                    Button {
                        Layout.alignment: Qt.AlignRight
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
                    }
                }
            }
        }
    }
}
