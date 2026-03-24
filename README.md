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
- `Spielstart`: entweder ein lokaler Pfad zur `.exe` oder nur die numerische Steam-Spiel-ID
- `Save-Ordner`: Ordner, in dem die Speicherdaten liegen
- `Prozessnamen`: kommagetrennte Prozessnamen, z. B. `Game.exe, Launcher.exe`
- `Drive-Archivname`: Basisname des Archivs in Google Drive, z. B. `eldenring_save`; `.zip` wird automatisch ergänzt
- `Drive-Ordner-ID`: optionaler Zielordner in Google Drive

Die Profil-ID wird automatisch erzeugt und ist im UI schreibgeschützt.
Für Steam-Spiele wird intern automatisch `steam://rungameid/<id>` verwendet; im Formular wird nur die ID eingegeben.

## Ablauf

1. Profil im Dropdown auswählen.
2. Über `Spiel starten` den Sync starten.
3. Vor dem Spielstart wird der Save-Ordner mit dem Archiv in Google Drive verglichen.
4. Falls der Cloud-Stand abweicht, wird der lokale Stand gesichert und aus der Cloud wiederhergestellt.
5. Nach dem Spielende wird der komplette Save-Ordner erneut geprüft und bei Änderungen als ZIP hochgeladen.

Wenn in Google Drive noch kein passendes ZIP vorhanden ist, wird beim ersten erfolgreichen Lauf ein Initial-Upload angelegt, auch wenn sich der lokale Save zwischen Start und Ende nicht verändert hat.

Neue, gelöschte oder geänderte Dateien im Save-Ordner zählen immer als Änderung.

## Bedienung der UI

- Das UI läuft ausschließlich im Darkmode.
- Hover-Hinweise erklären die wichtigsten Eingabefelder direkt in der Oberfläche.
- Für den Save-Pfad wird nur ein Ordner ausgewählt, keine einzelne Datei.
- Für Steam-Spiele wird nur die numerische Spiel-ID eingetragen; für lokale Spiele kann weiterhin eine EXE ausgewählt werden.
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

`game_exe_path` kann im JSON entweder ein lokaler EXE-Pfad oder eine numerische Steam-ID sein.

## Entwicklung

```powershell
uv run --group dev python -m pytest
pyinstaller Savesync.spec
```

Die Windows-Builds verwenden das Projekt-Icon aus `src/icon/icon.ico` als EXE- und Fenster-Icon.

## Abnahmetest / Smoke-Test

Automatisierte Modell-, UI-, Sync- und OAuth-Fehlerfälle sind per `pytest` abgedeckt. Zusätzlich bleibt ein manueller Google-Drive-Smoke-Test mit echtem OAuth-Login und einem echten Testordner in Drive sinnvoll.

Voraussetzungen:

- `client_secrets.json` liegt im Projektordner bzw. neben der `.exe`
- ein leerer Testordner in Google Drive ist vorhanden
- ein Testprofil zeigt auf einen lokalen Save-Ordner mit mindestens einer Datei
- optional: ein zweites Profil oder ein geänderter `drive_folder_id` zum Verifizieren eines Ordnerwechsels

Empfohlene Smoke-Test-Szenarien:

1. Erst-Upload in leeren Drive-Ordner
   Erwartung: Nach `Spiel starten` erscheint ein neues `.zip`-Archiv im konfigurierten Drive-Ordner.
2. Zweiter Lauf ohne Save-Änderung
   Erwartung: Kein unnötiger neuer Upload; das bestehende Archiv bleibt konsistent.
3. Lauf mit geänderten Save-Dateien
   Erwartung: Das vorhandene ZIP wird nach Spielende aktualisiert.
4. Geänderter `drive_folder_id`
   Erwartung: Das Archiv wird mit den aktuellen Profilmetadaten im richtigen Zielordner aktualisiert.
5. Fehlende `client_secrets.json`
   Erwartung: Verständliche Fehlermeldung statt stillem Abbruch.
6. Ungültige oder widerrufene Credentials
   Erwartung: Zuerst Refresh-Versuch, danach bei Bedarf erneuter Login.

Weitere Projektregeln stehen in `AGENTS.md`, die fachlichen Anforderungen in `Anforderungs.md`.
