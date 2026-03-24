# Anforderungsdokument Save Sync

## Ziel
Das bestehende Projekt synchronisiert aktuell nur ein einzelnes Spiel über ein statisches `config.ini`-Setup. Es soll zu einer Desktop-Anwendung mit grafischer Oberfläche erweitert werden, sodass mehrere Spiele dynamisch verwaltet und synchronisiert werden können.

Die Anwendung soll weiterhin lokale Spielstände mit Google Drive synchronisieren, aber die Verwaltung der Spiele, Pfade und Cloud-Ziele über eine UI ermöglichen. Außerdem soll die Konfiguration leicht mit anderen Personen austauschbar sein.

## Zielbild
- Desktop-Anwendung statt reinem Startskript
- UI mit Qt Quick / QML
- Python-Backend mit klarer Trennung zwischen UI, Konfiguration und Sync-Logik
- Unterstützung für mehrere Spieleprofile
- Import und Export von Spieleprofilen als JSON
- Verbesserte OAuth-Behandlung für Google Drive

## Technische Leitplanken
- UI-Technologie: `Qt QML`
- Python-Qt-Binding: `PySide6`
- Cloud-Provider in der ersten Ausbaustufe: `Google Drive`
- Zielplattform vorrangig: `Windows`
- Bestehende Logik für Hash-Vergleich, Download vor Spielstart und Upload nach Spielende bleibt fachlich erhalten

## Fachliche Anforderungen

### 1. Spieleverwaltung über UI
Die Anwendung muss mehrere Spieleprofile verwalten können. Jedes Profil beschreibt ein Spiel und alle Daten, die für die Synchronisation benötigt werden.

Ein Profil muss mindestens folgende Felder enthalten:
- Anzeigename des Spiels
- Startziel des Spiels, entweder als Pfad zur lokalen Spiel-Executable oder als Steam-Spiel-ID
- Pfad zum Save-Ordner
- Prozessname oder Liste von Prozessnamen zur Erkennung, ob das Spiel läuft
- Name des Cloud-Archivs auf Google Drive
- Google-Drive-Ordner-ID als Zielordner

Wichtig für Save-Daten:
- ein Spielprofil verweist immer auf einen Save-Ordner
- alle relevanten Dateien im Ordner müssen in die Synchronisationslogik einbezogen werden

Die UI muss folgende Funktionen anbieten:
- neues Spielprofil anlegen
- bestehendes Spielprofil bearbeiten
- Spielprofil löschen
- Spielprofil auswählen
- Spiel über ein Dropdown auswählen
- ausgewähltes Spiel über einen Start-Button starten
- Synchronisierung für das gewählte Spiel starten

### 2. Dynamische statt statischer Konfiguration
Die bisherige starre `config.ini` soll nicht mehr das zentrale Modell sein. Stattdessen soll die Anwendung intern mit einer strukturierten Konfiguration für mehrere Spiele arbeiten.

Erwartetes Ziel:
- zentrale App-Konfiguration in einem strukturierten Format
- Spiele als Liste von Profilen
- Speicherung lokal auf dem Rechner des Nutzers

### 3. JSON-Import und JSON-Export
Spieleprofile sollen leicht mit Freunden austauschbar sein.

Daher muss die Anwendung:
- Spieleprofile als JSON exportieren können
- Spieleprofile aus JSON importieren können
- beim Import prüfen, ob Pflichtfelder vorhanden sind
- ungültige oder unvollständige JSON-Dateien mit verständlichen Fehlermeldungen ablehnen

Wichtig:
- OAuth-Credentials, Tokens oder sonstige geheime Daten dürfen nicht exportiert werden
- Export und Import sollen sich auf Spieleprofile und deren Sync-Einstellungen beschränken

### 4. Google-Drive-Ziel frei definierbar
Der Nutzer muss den Speicherort in Google Drive selbst festlegen können.

Dazu muss pro Spielprofil konfigurierbar sein:
- in welchen Google-Drive-Ordner synchronisiert wird
- unter welchem Archivnamen der Save-Ordner in der Cloud gespeichert wird

Für den Archivnamen gilt:
- im UI wird nur der Basisname eingegeben
- `.zip` wird automatisch ergänzt
- intern wird in Google Drive immer ein ZIP-Archiv verwendet

### 5. Verbesserte OAuth-Behandlung
Die Google-Authentifizierung muss robuster werden.

Gewünschtes Verhalten:
- vorhandene Credentials werden geladen, wenn sie existieren
- wenn das Access-Token abgelaufen ist, soll zuerst versucht werden, es sauber zu erneuern
- falls ein Refresh nicht möglich ist oder fehlschlägt, soll eine neue Anmeldung angefordert werden
- neue oder erneuerte Credentials sollen wieder lokal gespeichert werden

Die Anwendung muss Fehlerfälle sauber behandeln:
- keine gültigen Credentials vorhanden
- Token abgelaufen
- Refresh fehlgeschlagen
- Zugriff entzogen
- `client_secrets.json` fehlt

Pfadvorgabe für `client_secrets.json`:
- beim Start aus dem Quellcode liegt die Datei im Projektverzeichnis
- beim Start einer erzeugten `.exe` liegt die Datei im gleichen Ordner wie die `.exe`

### 6. Synchronisationsablauf
Der bestehende Grundablauf bleibt erhalten und soll in die neue Architektur übernommen werden:

1. Vor Spielstart Cloud-Datei prüfen
2. Falls Cloud-Stand neuer ist, lokal sichern und herunterladen
3. Spiel starten
4. Warten bis das Spiel beendet wurde
5. Nach Spielende lokalen Save erneut prüfen
6. Nur bei Änderung hochladen

Für jeden Save-Ordner gilt:
- es muss über alle Dateien im Ordner iteriert werden
- für jede Datei muss ein Hash berechnet und mit dem Cloud-Stand verglichen werden
- sobald mindestens eine Datei unterschiedlich ist, muss die normale Sync-Logik für das betroffene Spiel greifen
- der Vergleich darf nicht nur auf eine einzelne Datei reduziert werden
- neue, fehlende oder gelöschte Dateien im Save-Ordner müssen als Änderung erkannt werden
- in Google Drive wird der Save-Ordner als ZIP-Archiv gespeichert und zum Vergleich wieder entpackt
- wenn für ein Profil noch kein passendes ZIP in Google Drive vorhanden ist, muss beim ersten erfolgreichen Lauf ein Initial-Upload erfolgen

Zusätzlich soll die UI den Status sichtbar machen, zum Beispiel:
- bereit
- Anmeldung erforderlich
- Download läuft
- Spiel läuft
- Upload läuft
- abgeschlossen
- Fehler

## UI-Anforderungen
- Startansicht mit Liste der vorhandenen Spieleprofile
- zusätzlich eine zentrale Auswahl des aktiven Spiels über ein Dropdown
- ein klar sichtbarer Start-Button, der das im Dropdown gewählte Spiel startet
- Formularansicht zum Erstellen und Bearbeiten eines Profils
- sichtbare Felder für alle relevanten Pfade und Google-Drive-Einstellungen
- Möglichkeit zur Ordnerauswahl für den Save-Ordner und Dateiauswahl für lokale Spiel-Executables
- Profil-ID wird automatisch erstellt und ist im UI nicht editierbar
- Hover-Hinweise für die wichtigsten Eingabefelder und Auswahl-Elemente
- Statusanzeige für Sync und Authentifizierung
- die UI läuft ausschließlich im Darkmode
- klare Fehlermeldungen bei ungültigen Eingaben oder fehlenden Dateien

## Nicht-Ziele für die erste Ausbaustufe
- Unterstützung mehrerer Cloud-Anbieter
- Benutzerkonten innerhalb der App
- automatischer Abgleich mehrerer Geräte ohne manuelles Profil-Setup
- Mitexport von Tokens oder geheimen Auth-Daten

## Datenmodell für Spielprofile
Ein Spieleprofil soll mindestens folgende Daten enthalten:

- `id`
- `display_name`
- `game_exe_path`
- `save_folder_path`
- `game_process_names`
- `drive_filename`
- `drive_folder_id`
- `cloud_provider`

Vorgabe:
- `cloud_provider` ist in Version 1 fest auf `google_drive`
- `save_folder_path` verweist immer auf einen kompletten Save-Ordner
- `game_exe_path` speichert entweder einen lokalen EXE-Pfad oder eine numerische Steam-Spiel-ID
- `drive_filename` wird intern als ZIP-Dateiname gespeichert; die UI darf den Basisnamen ohne `.zip` anzeigen

## Beispiel für ein austauschbares JSON-Profil
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

Hinweis:
- Beim Import und Speichern wird `drive_filename` automatisch zu einem ZIP-Archivnamen normalisiert.

## Abnahmekriterien
- Es können mehrere Spieleprofile über die UI angelegt und gespeichert werden.
- Spiele können über ein Dropdown ausgewählt werden.
- Das im Dropdown gewählte Spiel kann über einen Start-Button gestartet werden.
- Die Anwendung läuft standardmäßig und ausschließlich im Darkmode.
- Die Profil-ID ist nicht manuell editierbar.
- Hover-Hinweise unterstützen die Eingabefelder im Formular.
- Ein Nutzer kann ein Profil auswählen und eine Synchronisierung auslösen.
- Die Anwendung kann ein Profil als JSON exportieren.
- Die Anwendung kann ein gültiges JSON-Profil importieren.
- Ungültige JSON-Dateien werden mit verständlicher Meldung abgelehnt.
- Die Google-Drive-Ordner-ID kann pro Spiel individuell gesetzt werden.
- Der Archivname kann im UI ohne `.zip` eingegeben werden.
- Intern wird der Archivname immer als `.zip` in Google Drive verwendet.
- Ein abgelaufenes Token führt nicht sofort zum Fehler, sondern zuerst zu einem Refresh-Versuch.
- Wenn der Refresh nicht funktioniert, wird eine neue Anmeldung angefordert.
- Ein Profil kann alternativ zu einem lokalen EXE-Pfad auch über eine Steam-Spiel-ID gestartet werden.
- Nach Spielende wird nur dann hochgeladen, wenn sich der lokale Spielstand geändert hat.
- Save-Ordner mit mehreren Dateien werden vollständig geprüft und nicht nur über eine Einzeldatei behandelt.
- Sobald sich mindestens eine Datei in einem Save-Ordner unterscheidet, wird eine Synchronisierung ausgelöst.
- Neue, fehlende oder gelöschte Dateien in einem Save-Ordner werden als Änderung erkannt.
- Wenn noch kein passendes Cloud-Archiv vorhanden ist, wird beim ersten erfolgreichen Lauf ein Initial-Upload erstellt.

## Offene Architekturidee für die spätere Umsetzung
- QML für Oberfläche
- Python-Backend für Geschäftslogik
- getrennte Module für:
  - Profile und Konfiguration
  - JSON-Import/Export
  - OAuth und Google Drive
  - Synchronisationslogik

## Aufgabenliste
- [x] Bestehende Einzelspiel-Logik analysieren und in wiederverwendbare Services zerlegen
- [x] QML-basierte Desktop-Oberfläche aufsetzen
- [x] Datenmodell für mehrere Spieleprofile definieren
- [x] Lokale Konfigurationsspeicherung für mehrere Profile implementieren
- [x] UI zum Anlegen, Bearbeiten, Löschen und Auswählen von Profilen erstellen
- [x] Dropdown zur Auswahl des aktiven Spiels in der Hauptansicht umsetzen
- [x] Start-Button für das ausgewählte Spiel in der Hauptansicht umsetzen
- [x] Ordnerauswahl für Save-Ordner und Dateiauswahl für Spielpfade in der UI integrieren
- [x] Profil-ID automatisch erzeugen und im UI schreibschützen
- [x] Hover-Hinweise für die zentralen UI-Felder ergänzen
- [x] Darkmode als festes UI-Design für die QML-Oberfläche umsetzen
- [x] JSON-Export für Spieleprofile implementieren
- [x] JSON-Import mit Validierung implementieren
- [x] Google-Drive-Ordner-ID pro Profil konfigurierbar machen
- [x] Archivnamen ohne `.zip` im UI akzeptieren und intern normalisieren
- [x] OAuth-Handling für Token-Refresh und Re-Login robuster machen
- [x] Statusanzeige für Auth, Download, Spielstatus und Upload in der UI darstellen
- [x] Fehlerbehandlung für fehlende Dateien, ungültige Konfiguration und Drive-Probleme ergänzen
- [x] Synchronisationsablauf aus dem bestehenden Skript in die neue Architektur überführen
- [x] Save-Ordner mit mehreren Dateien in der Backend-Logik unterstützen
- [x] Über alle Dateien im konfigurierten Save-Ordner iterieren und pro Datei Hashes berechnen
- [x] Dateiänderungen, fehlende Dateien und neue Dateien im Save-Ordner als Sync-Trigger behandeln
- [x] Cloud-Abgleich für ordnerbasierte Saves über ZIP-Archive implementieren
- [x] Tests für Mehrdatei-Saves, Normalisierung des Archivnamens und ordnerbasierte Synchronisation ergänzen
- [x] Zusätzliche Abnahmetests für UI-Workflows und reale OAuth-Fehlerfälle automatisiert ergänzen
- [ ] Manuellen Google-Drive-Smoke-Test mit echtem OAuth-Login und Testordner einmal vollständig durchführen
