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

Lege `client_secrets.json` im Repository-Root ab. Beim ersten Cloud-Zugriff öffnet die App den Google-Login im Browser. Abgelaufene Tokens werden zuerst per Refresh erneuert; falls das fehlschlägt, wird erneut ein Login angefordert.

## Profil anlegen

Ein Profil enthält:

- `Anzeigename`: frei wählbarer Name im UI
- `Spiel-Executable`: Pfad zur `.exe`
- `Save-Ordner`: Ordner, in dem die Speicherdaten liegen
- `Prozessnamen`: kommagetrennte Prozessnamen, z. B. `Game.exe, Launcher.exe`
- `Drive-Archivname`: Basisname des Archivs in Google Drive, z. B. `eldenring_save` . `.zip` wird automatisch ergänzt
- `Drive-Ordner-ID`: optionaler Zielordner in Google Drive

Die Profil-ID wird automatisch erzeugt und ist nicht manuell editierbar.

## Ablauf

1. Profil im Dropdown auswählen.
2. Über `Spiel starten` den Sync starten.
3. Vor dem Spielstart wird der Save-Ordner mit der ZIP-Datei in Google Drive verglichen.
4. Falls der Cloud-Stand abweicht, wird der lokale Stand gesichert und aus der Cloud wiederhergestellt.
5. Nach dem Spielende wird der komplette Save-Ordner erneut geprüft und bei Änderungen als ZIP hochgeladen.

Neue, gelöschte oder geänderte Dateien im Save-Ordner zählen immer als Änderung.

## JSON-Import und Export

Profile können über die UI als JSON exportiert und wieder importiert werden. Exportiert werden nur Profile und Sync-Einstellungen, keine OAuth-Tokens oder Secrets.

## Entwicklung

```powershell
uv run --group dev python -m pytest
pyinstaller Savesync.spec
```

Weitere Projektregeln stehen in `AGENTS.md`, die fachlichen Anforderungen in `Anforderungs.md`.
