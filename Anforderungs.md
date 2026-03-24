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
- Pfad zur Spiel-Executable
- Pfad zur Save-Datei oder zum Save-Speicherort
- Prozessname oder Liste von Prozessnamen zur Erkennung, ob das Spiel läuft
- Dateiname auf Google Drive
- Google-Drive-Ordner-ID als Zielordner

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
- unter welchem Dateinamen die Save-Datei in der Cloud gespeichert wird

Die bisher bereits bekannte Ordner-ID-Logik soll erhalten bleiben, aber nicht mehr hart oder indirekt fest im Code hängen.

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

### 6. Synchronisationsablauf
Der bestehende Grundablauf bleibt erhalten und soll in die neue Architektur übernommen werden:

1. Vor Spielstart Cloud-Datei prüfen
2. Falls Cloud-Stand neuer ist, lokal sichern und herunterladen
3. Spiel starten
4. Warten bis das Spiel beendet wurde
5. Nach Spielende lokalen Save erneut prüfen
6. Nur bei Änderung hochladen

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
- Möglichkeit zur Dateiauswahl für lokale Pfade
- Statusanzeige für Sync und Authentifizierung
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
- `save_file_path`
- `game_process_names`
- `drive_filename`
- `drive_folder_id`
- `cloud_provider`

Vorgabe:
- `cloud_provider` ist in Version 1 fest auf `google_drive`

## Beispiel für ein austauschbares JSON-Profil
```json
{
  "profiles": [
    {
      "id": "my-game-1",
      "display_name": "Mein Spiel",
      "game_exe_path": "C:/Games/MyGame/Game.exe",
      "save_file_path": "C:/Users/User/Documents/MyGame/save.sav",
      "game_process_names": ["Game.exe"],
      "drive_filename": "save.sav",
      "drive_folder_id": "1AbCdEfGhIjKlMnOp",
      "cloud_provider": "google_drive"
    }
  ]
}
```

## Abnahmekriterien
- Es können mehrere Spieleprofile über die UI angelegt und gespeichert werden.
- Spiele können über ein Dropdown ausgewählt werden.
- Das im Dropdown gewählte Spiel kann über einen Start-Button gestartet werden.
- Ein Nutzer kann ein Profil auswählen und eine Synchronisierung auslösen.
- Die Anwendung kann ein Profil als JSON exportieren.
- Die Anwendung kann ein gültiges JSON-Profil importieren.
- Ungültige JSON-Dateien werden mit verständlicher Meldung abgelehnt.
- Die Google-Drive-Ordner-ID kann pro Spiel individuell gesetzt werden.
- Ein abgelaufenes Token führt nicht sofort zum Fehler, sondern zuerst zu einem Refresh-Versuch.
- Wenn der Refresh nicht funktioniert, wird eine neue Anmeldung angefordert.
- Nach Spielende wird nur dann hochgeladen, wenn sich der lokale Spielstand geändert hat.

## Offene Architekturidee für die spätere Umsetzung
- QML für Oberfläche
- Python-Backend für Geschäftslogik
- getrennte Module für:
  - Profile und Konfiguration
  - JSON-Import/Export
  - OAuth und Google Drive
  - Synchronisationslogik

## Aufgabenliste
- [ ] Bestehende Einzelspiel-Logik analysieren und in wiederverwendbare Services zerlegen
- [ ] QML-basierte Desktop-Oberfläche aufsetzen
- [ ] Datenmodell für mehrere Spieleprofile definieren
- [ ] Lokale Konfigurationsspeicherung für mehrere Profile implementieren
- [ ] UI zum Anlegen, Bearbeiten, Löschen und Auswählen von Profilen erstellen
- [ ] Dropdown zur Auswahl des aktiven Spiels in der Hauptansicht umsetzen
- [ ] Start-Button für das ausgewählte Spiel in der Hauptansicht umsetzen
- [ ] Datei- und Pfadauswahl in der UI integrieren
- [ ] JSON-Export für Spieleprofile implementieren
- [ ] JSON-Import mit Validierung implementieren
- [ ] Google-Drive-Ordner-ID pro Profil konfigurierbar machen
- [ ] OAuth-Handling für Token-Refresh und Re-Login robuster machen
- [ ] Statusanzeige für Auth, Download, Spielstatus und Upload in der UI darstellen
- [ ] Fehlerbehandlung für fehlende Dateien, ungültige Konfiguration und Drive-Probleme ergänzen
- [ ] Synchronisationsablauf aus dem bestehenden Skript in die neue Architektur überführen
- [ ] Abnahmetests für Multi-Profil-Verwaltung, JSON-Austausch und OAuth-Fehlerfälle durchführen
