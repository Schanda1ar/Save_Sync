# Save Sync

Save Sync ist eine Desktop-Anwendung für Windows, die Spielstände vor dem Start mit Google Drive abgleicht und nach dem Beenden wieder hochlädt. Die UI basiert auf `PySide6` und `QML`, das Backend liegt unter `src/backend`.

## Voraussetzungen

- Python `3.14`
- `uv`
- Eine Google-Drive-OAuth-Client-Datei als `client_secrets.json` im Projektordner

## Installation

```powershell
uv sync --group dev
uv run python main.py
```

Beim ersten Start werden lokale App-Daten unter `~/Documents/SaveSync` angelegt. Dort speichert die App:

- `profiles.json` für Profile
- `mycreds.txt` für Google-OAuth-Credentials

## Google Drive Setup

Lege `client_secrets.json` beim Start per `python main.py` im Repository-Root ab. Wenn du eine `.exe` mit `pyinstaller Savesync.spec` erzeugst, muss `client_secrets.json` im gleichen Ordner wie die `Savesync.exe` liegen. Beim ersten Cloud-Zugriff öffnet die App den Google-Login im Browser. Abgelaufene Tokens werden zuerst per Refresh erneuert; falls das fehlschlägt, wird erneut ein Login angefordert.

## Profil anlegen

Ein Profil enthält:

- `Anzeigename`: frei wählbarer Name im UI
- `Spiel-Executable`: Pfad zur `.exe`
- `Save-Ordner`: Ordner, in dem die Speicherdaten liegen
- `Prozessnamen`: kommagetrennte Prozessnamen, z. B. `Game.exe, Launcher.exe`
- `Drive-Archivname`: Basisname des Archivs in Google Drive, z. B. `eldenring_save`; `.zip` wird automatisch ergänzt
- `Drive-Ordner-ID`: optionaler Zielordner in Google Drive

Die Profil-ID wird automatisch erzeugt und ist im UI schreibgeschützt.

## Ablauf

1. Profil im Dropdown auswählen.
2. Über `Spiel starten` den Sync starten.
3. Vor dem Spielstart wird der Save-Ordner mit dem Archiv in Google Drive verglichen.
4. Falls der Cloud-Stand abweicht, wird der lokale Stand gesichert und aus der Cloud wiederhergestellt.
5. Nach dem Spielende wird der komplette Save-Ordner erneut geprüft und bei Änderungen als ZIP hochgeladen.

Neue, gelöschte oder geänderte Dateien im Save-Ordner zählen immer als Änderung.

## Bedienung der UI

- Das UI läuft ausschließlich im Darkmode.
- Hover-Hinweise erklären die wichtigsten Eingabefelder direkt in der Oberfläche.
- Für den Save-Pfad wird nur ein Ordner ausgewählt, keine einzelne Datei.
- Der im Formular sichtbare `Drive-Archivname` wird ohne `.zip` eingegeben; intern speichert die App weiterhin eine `.zip`-Datei in Google Drive.

## JSON-Import und Export

Profile können über die UI als JSON exportiert und wieder importiert werden. Exportiert werden nur Profile und Sync-Einstellungen, keine OAuth-Tokens oder Secrets.

Beispiel:

```json
{
  "profiles": [
    {
      "id": "my-game-1",
      "display_name": "Mein Spiel",
      "game_exe_path": "C:/Games/MyGame/Game.exe",
      "save_folder_path": "C:/Users/User/Documents/MyGame/SaveGames",
      "game_process_names": ["Game.exe"],
      "drive_filename": "mygame_save",
      "drive_folder_id": "1AbCdEfGhIjKlMnOp",
      "cloud_provider": "google_drive"
    }
  ]
}
```

Beim Import und Speichern normalisiert die App `drive_filename` automatisch zu einem ZIP-Archivnamen für Google Drive.

## Entwicklung

```powershell
uv run --group dev python -m pytest
pyinstaller Savesync.spec
```

Weitere Projektregeln stehen in `AGENTS.md`, die fachlichen Anforderungen in `Anforderungs.md`.
