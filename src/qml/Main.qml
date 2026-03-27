import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ApplicationWindow {
    id: window
    width: 1180
    height: 860
    minimumWidth: 1040
    minimumHeight: 760
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
        // Keep the combo box aligned with the selected backend profile after imports, deletes, or reloads.
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
        // Copy the current backend profile into the editable form fields.
        selectedData = controller.selectedProfileData
        idField.text = selectedData.id || ""
        nameField.text = selectedData.display_name || ""
        exeField.text = selectedData.game_exe_path || ""
        saveField.text = selectedData.save_folder_path || ""
        processField.text = selectedData.game_process_names || ""
        driveFileField.text = selectedData.drive_filename || ""
        driveFolderField.text = selectedData.drive_folder_id || ""
    }

    function selectedRecoveryBackupPath() {
        var backups = controller.recoveryBackups
        if (!backups || recoveryBackupCombo.currentIndex < 0 || recoveryBackupCombo.currentIndex >= backups.length) {
            return ""
        }
        return backups[recoveryBackupCombo.currentIndex].path || ""
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
        function onRecoveryBackupsChanged() {
            recoveryBackupCombo.currentIndex = controller.recoveryBackups.length > 0 ? 0 : -1
        }
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

    MessageDialog {
        id: unsavedChangesDialog
        title: "Ungespeicherte Änderungen"
        text: "Die Änderungen an diesem Profil wurden noch nicht gespeichert."
        informativeText: "Speichere das Profil zuerst, bevor du eine Synchronisierung oder einen Spielstart auslöst."
        buttons: MessageDialog.Ok
    }

    MessageDialog {
        id: recoveryConfirmDialog
        title: "Backup wiederherstellen"
        text: "Der ausgewählte Backup-Stand ersetzt den aktuellen lokalen Save-Ordner."
        informativeText: "Danach wird derselbe Stand nach Google Drive hochgeladen. Das aktuelle Drive-Archiv wird vorher als Sicherheitskopie gesichert."
        buttons: MessageDialog.Ok | MessageDialog.Cancel
        onAccepted: controller.recoverSelectedProfileFromBackup(window.selectedRecoveryBackupPath())
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: pageStart }
            GradientStop { position: 1.0; color: pageEnd }
        }

        RowLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 18

            Rectangle {
                Layout.preferredWidth: 320
                Layout.fillHeight: true
                radius: 24
                color: sidebarBg

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12

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
                    anchors.margins: 18
                    spacing: 10

                    Label {
                        text: "Profil bearbeiten"
                        color: titleText
                        font.pixelSize: 26
                        font.bold: true
                    }

                    ScrollView {
                        id: formScrollView
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        ScrollBar.vertical.policy: ScrollBar.AsNeeded

                        ColumnLayout {
                            width: formScrollView.availableWidth
                            spacing: 10

                        GridLayout {
                            Layout.fillWidth: true
                            columns: 3
                            columnSpacing: 10
                            rowSpacing: 8

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

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6

                        Label {
                            text: "Recovery-Backup"
                            color: bodyText
                        }

                        ComboBox {
                            id: recoveryBackupCombo
                            Layout.fillWidth: true
                            model: controller.recoveryBackups
                            textRole: "label"
                            enabled: !controller.busy && controller.recoveryBackups.length > 0
                            currentIndex: controller.recoveryBackups.length > 0 ? 0 : -1
                        }

                        Label {
                            Layout.fillWidth: true
                            color: mutedText
                            wrapMode: Text.WordWrap
                            text: controller.recoveryBackups.length > 0
                                  ? "Stellt einen vorhandenen SaveSync-Backup-Ordner lokal wieder her und lädt ihn manuell nach Drive hoch."
                                  : "Keine SaveSync-Backups für dieses Profil gefunden."
                        }
                    }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignRight
                        spacing: 8

                        Button {
                            id: syncButton
                            Layout.alignment: Qt.AlignRight
                            Layout.preferredWidth: 110
                            Layout.maximumWidth: 110
                            text: controller.busy ? "Läuft..." : "Sync"
                            enabled: !controller.busy
                            implicitHeight: 34
                            onClicked: {
                                if (controller.hasUnsavedProfileChanges(
                                        nameField.text,
                                        exeField.text,
                                        saveField.text,
                                        processField.text,
                                        driveFileField.text,
                                        driveFolderField.text
                                    )) {
                                    unsavedChangesDialog.open()
                                    return
                                }
                                controller.syncSelectedProfile()
                            }
                            background: Rectangle {
                                radius: 10
                                color: syncButton.hovered ? buttonHoverBg : buttonBg
                                border.color: controlBorder
                                border.width: 1
                            }
                            contentItem: Text {
                                text: syncButton.text
                                color: buttonText
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                font.bold: true
                                font.pixelSize: 14
                            }
                        }

                        Button {
                            id: recoveryButton
                            Layout.alignment: Qt.AlignRight
                            Layout.preferredWidth: 160
                            Layout.maximumWidth: 160
                            text: controller.busy ? "Läuft..." : "Backup"
                            enabled: !controller.busy && controller.recoveryBackups.length > 0
                            implicitHeight: 34
                            onClicked: {
                                if (controller.hasUnsavedProfileChanges(
                                        nameField.text,
                                        exeField.text,
                                        saveField.text,
                                        processField.text,
                                        driveFileField.text,
                                        driveFolderField.text
                                    )) {
                                    unsavedChangesDialog.open()
                                    return
                                }
                                recoveryConfirmDialog.open()
                            }
                            background: Rectangle {
                                radius: 10
                                color: recoveryButton.hovered ? buttonHoverBg : buttonBg
                                border.color: controlBorder
                                border.width: 1
                            }
                            contentItem: Text {
                                text: recoveryButton.text
                                color: buttonText
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                font.bold: true
                                font.pixelSize: 14
                            }
                        }

                        Button {
                            id: startButton
                            Layout.alignment: Qt.AlignRight
                            Layout.preferredWidth: 130
                            Layout.maximumWidth: 130
                            text: controller.busy ? "Läuft..." : "Spielstart"
                            enabled: !controller.busy
                            implicitHeight: 34
                            onClicked: {
                                if (controller.hasUnsavedProfileChanges(
                                        nameField.text,
                                        exeField.text,
                                        saveField.text,
                                        processField.text,
                                        driveFileField.text,
                                        driveFolderField.text
                                    )) {
                                    unsavedChangesDialog.open()
                                    return
                                }
                                controller.startSelectedGame()
                            }
                            background: Rectangle {
                                radius: 10
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
                                font.pixelSize: 14
                            }
                        }
                    }
                }
            }
        }
    }
}
