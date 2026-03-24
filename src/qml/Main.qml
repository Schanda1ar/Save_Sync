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
    color: "#f4efe7"

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

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#f7f1e7" }
            GradientStop { position: 1.0; color: "#dfebf4" }
        }

        RowLayout {
            anchors.fill: parent
            anchors.margins: 24
            spacing: 24

            Rectangle {
                Layout.preferredWidth: 320
                Layout.fillHeight: true
                radius: 24
                color: "#1f2f3d"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 16

                    Label {
                        text: "Spielauswahl"
                        color: "#f4efe7"
                        font.pixelSize: 28
                        font.bold: true
                    }

                    Label {
                        text: "Profil wählen"
                        color: "#c9d9e6"
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
                        color: "#304657"

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 8

                            Label {
                                text: "Status"
                                color: "#f4efe7"
                                font.bold: true
                            }

                            Label {
                                Layout.fillWidth: true
                                text: controller.statusMessage
                                color: "#dce7f0"
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
                color: "#fffaf2"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 12

                    Label {
                        text: "Profil bearbeiten"
                        color: "#1c2730"
                        font.pixelSize: 26
                        font.bold: true
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 3
                        columnSpacing: 12
                        rowSpacing: 10

                        Label { text: "Profil-ID" }
                        TextField {
                            id: idField
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            placeholderText: "Wird automatisch erzeugt"
                        }

                        Label { text: "Anzeigename" }
                        TextField {
                            id: nameField
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            placeholderText: "z. B. Elden Ring"
                        }

                        Label { text: "Spiel-Executable" }
                        TextField {
                            id: exeField
                            Layout.fillWidth: true
                            placeholderText: "Pfad zur EXE"
                        }
                        Button {
                            text: "Datei wählen"
                            onClicked: exeDialog.open()
                        }

                        Label { text: "Save-Datei" }
                        TextField {
                            id: saveField
                            Layout.fillWidth: true
                            placeholderText: "Pfad zur Save-Datei"
                        }
                        Button {
                            text: "Datei wählen"
                            onClicked: saveDialog.open()
                        }

                        Label { text: "Prozessnamen" }
                        TextField {
                            id: processField
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            placeholderText: "Game.exe, Launcher.exe"
                        }

                        Label { text: "Drive-Dateiname" }
                        TextField {
                            id: driveFileField
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            placeholderText: "save.sav"
                        }

                        Label { text: "Drive-Ordner-ID" }
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
