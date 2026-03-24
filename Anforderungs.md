# Anforderungsdokument Save Sync

## Ziel
Das bestehende Projekt synchronisiert aktuell nur ein einzelnes Spiel Ã¼ber ein statisches `config.ini`-Setup. Es soll zu einer Desktop-Anwendung mit grafischer OberflÃ¤che erweitert werden, sodass mehrere Spiele dynamisch verwaltet und synchronisiert werden kÃ¶nnen.

Die Anwendung soll weiterhin lokale SpielstÃ¤nde mit Google Drive synchronisieren, aber die Verwaltung der Spiele, Pfade und Cloud-Ziele Ã¼ber eine UI ermÃ¶glichen. AuÃŸerdem soll die Konfiguration leicht mit anderen Personen austauschbar sein.

## Zielbild
- Desktop-Anwendung statt reinem Startskript
- UI mit Qt Quick / QML
- Python-Backend mit klarer Trennung zwischen UI, Konfiguration und Sync-Logik
- UnterstÃ¼tzung fÃ¼r mehrere Spieleprofile
- Import und Export von Spieleprofilen als JSON
- Verbesserte OAuth-Behandlung fÃ¼r Google Drive

## Technische Leitplanken
- UI-Technologie: `Qt QML`
- Python-Qt-Binding: `PySide6`
- Cloud-Provider in der ersten Ausbaustufe: `Google Drive`
- Zielplattform vorrangig: `Windows`
- Bestehende Logik fÃ¼r Hash-Vergleich, Download vor Spielstart und Upload nach Spielende bleibt fachlich erhalten

## Fachliche Anforderungen

### 1. Spieleverwaltung Ã¼ber UI
Die Anwendung muss mehrere Spieleprofile verwalten kÃ¶nnen. Jedes Profil beschreibt ein Spiel und alle Daten, die fÃ¼r die Synchronisation benÃ¶tigt werden.

Ein Profil muss mindestens folgende Felder enthalten:
- Anzeigename des Spiels
- Pfad zur Spiel-Executable
- Pfad zum Save-Ordner
- Prozessname oder Liste von Prozessnamen zur Erkennung, ob das Spiel lÃ¤uft
- Dateiname auf Google Drive
- Google-Drive-Ordner-ID als Zielordner

Wichtig für Save-Daten:
- ein Spielprofil verweist immer auf einen Save-Ordner
- auch wenn ein Spiel praktisch nur eine Datei nutzt, wird deren Elternordner als Save-Ordner konfiguriert
- alle relevanten Dateien im Ordner müssen in die Synchronisationslogik einbezogen werden

Die UI muss folgende Funktionen anbieten:
- neues Spielprofil anlegen
- bestehendes Spielprofil bearbeiten
- Spielprofil lÃ¶schen
- Spielprofil auswÃ¤hlen
- Spiel Ã¼ber ein Dropdown auswÃ¤hlen
- ausgewÃ¤hltes Spiel Ã¼ber einen Start-Button starten
- Synchronisierung fÃ¼r das gewÃ¤hlte Spiel starten

### 2. Dynamische statt statischer Konfiguration
Die bisherige starre `config.ini` soll nicht mehr das zentrale Modell sein. Stattdessen soll die Anwendung intern mit einer strukturierten Konfiguration fÃ¼r mehrere Spiele arbeiten.

Erwartetes Ziel:
- zentrale App-Konfiguration in einem strukturierten Format
- Spiele als Liste von Profilen
- Speicherung lokal auf dem Rechner des Nutzers

### 3. JSON-Import und JSON-Export
Spieleprofile sollen leicht mit Freunden austauschbar sein.

Daher muss die Anwendung:
- Spieleprofile als JSON exportieren kÃ¶nnen
- Spieleprofile aus JSON importieren kÃ¶nnen
- beim Import prÃ¼fen, ob Pflichtfelder vorhanden sind
- ungÃ¼ltige oder unvollstÃ¤ndige JSON-Dateien mit verstÃ¤ndlichen Fehlermeldungen ablehnen

Wichtig:
- OAuth-Credentials, Tokens oder sonstige geheime Daten dÃ¼rfen nicht exportiert werden
- Export und Import sollen sich auf Spieleprofile und deren Sync-Einstellungen beschrÃ¤nken

### 4. Google-Drive-Ziel frei definierbar
Der Nutzer muss den Speicherort in Google Drive selbst festlegen kÃ¶nnen.

Dazu muss pro Spielprofil konfigurierbar sein:
- in welchen Google-Drive-Ordner synchronisiert wird
- unter welchem Dateinamen das ZIP-Archiv des Save-Ordners in der Cloud gespeichert wird

Die bisher bereits bekannte Ordner-ID-Logik soll erhalten bleiben, aber nicht mehr hart oder indirekt fest im Code hÃ¤ngen.

### 5. Verbesserte OAuth-Behandlung
Die Google-Authentifizierung muss robuster werden.

GewÃ¼nschtes Verhalten:
- vorhandene Credentials werden geladen, wenn sie existieren
- wenn das Access-Token abgelaufen ist, soll zuerst versucht werden, es sauber zu erneuern
- falls ein Refresh nicht mÃ¶glich ist oder fehlschlÃ¤gt, soll eine neue Anmeldung angefordert werden
- neue oder erneuerte Credentials sollen wieder lokal gespeichert werden

Die Anwendung muss FehlerfÃ¤lle sauber behandeln:
- keine gÃ¼ltigen Credentials vorhanden
- Token abgelaufen
- Refresh fehlgeschlagen
- Zugriff entzogen
- `client_secrets.json` fehlt

### 6. Synchronisationsablauf
Der bestehende Grundablauf bleibt erhalten und soll in die neue Architektur Ã¼bernommen werden:

1. Vor Spielstart Cloud-Datei prÃ¼fen
2. Falls Cloud-Stand neuer ist, lokal sichern und herunterladen
3. Spiel starten
4. Warten bis das Spiel beendet wurde
5. Nach Spielende lokalen Save erneut prÃ¼fen
6. Nur bei Ã„nderung hochladen

Für jeden Save-Ordner gilt:
- es muss über alle Dateien im Ordner iteriert werden
- für jede Datei muss ein Hash berechnet und mit dem Cloud-Stand verglichen werden
- sobald mindestens eine Datei unterschiedlich ist, muss die normale Sync-Logik für das betroffene Spiel greifen
- der Vergleich darf nicht nur auf eine einzelne Datei reduziert werden
- neue, fehlende oder gelöschte Dateien im Save-Ordner müssen als Änderung erkannt werden
- in Google Drive wird der Save-Ordner als ZIP-Archiv gespeichert und zum Vergleich wieder entpackt

ZusÃ¤tzlich soll die UI den Status sichtbar machen, zum Beispiel:
- bereit
- Anmeldung erforderlich
- Download lÃ¤uft
- Spiel lÃ¤uft
- Upload lÃ¤uft
- abgeschlossen
- Fehler

## UI-Anforderungen
- Startansicht mit Liste der vorhandenen Spieleprofile
- zusÃ¤tzlich eine zentrale Auswahl des aktiven Spiels Ã¼ber ein Dropdown
- ein klar sichtbarer Start-Button, der das im Dropdown gewÃ¤hlte Spiel startet
- Formularansicht zum Erstellen und Bearbeiten eines Profils
- sichtbare Felder fÃ¼r alle relevanten Pfade und Google-Drive-Einstellungen
- Möglichkeit zur Ordnerauswahl für den Save-Ordner und Dateiauswahl für die Spiel-Executable
- Statusanzeige fÃ¼r Sync und Authentifizierung
- die UI läuft ausschließlich im Darkmode
- klare Fehlermeldungen bei ungÃ¼ltigen Eingaben oder fehlenden Dateien

## Nicht-Ziele fÃ¼r die erste Ausbaustufe
- UnterstÃ¼tzung mehrerer Cloud-Anbieter
- Benutzerkonten innerhalb der App
- automatischer Abgleich mehrerer GerÃ¤te ohne manuelles Profil-Setup
- Mitexport von Tokens oder geheimen Auth-Daten

## Datenmodell fÃ¼r Spielprofile
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
- `save_folder_path` darf entweder auf eine einzelne Datei oder auf einen kompletten Save-Ordner zeigen

## Beispiel fÃ¼r ein austauschbares JSON-Profil
```json
{
  "profiles": [
    {
      "id": "my-game-1",
      "display_name": "Mein Spiel",
      "game_exe_path": "C:/Games/MyGame/Game.exe",
      "save_folder_path": "C:/Users/User/Documents/MyGame/SaveGames",
      "game_process_names": ["Game.exe"],
      "drive_filename": "mygame_save.zip",
      "drive_folder_id": "1AbCdEfGhIjKlMnOp",
      "cloud_provider": "google_drive"
    }
  ]
}
```

## Abnahmekriterien
- Es kÃ¶nnen mehrere Spieleprofile Ã¼ber die UI angelegt und gespeichert werden.
- Spiele kÃ¶nnen Ã¼ber ein Dropdown ausgewÃ¤hlt werden.
- Das im Dropdown gewÃ¤hlte Spiel kann Ã¼ber einen Start-Button gestartet werden.
- Die Anwendung läuft standardmäßig und ausschließlich im Darkmode.
- Ein Nutzer kann ein Profil auswÃ¤hlen und eine Synchronisierung auslÃ¶sen.
- Die Anwendung kann ein Profil als JSON exportieren.
- Die Anwendung kann ein gÃ¼ltiges JSON-Profil importieren.
- UngÃ¼ltige JSON-Dateien werden mit verstÃ¤ndlicher Meldung abgelehnt.
- Die Google-Drive-Ordner-ID kann pro Spiel individuell gesetzt werden.
- Ein abgelaufenes Token fÃ¼hrt nicht sofort zum Fehler, sondern zuerst zu einem Refresh-Versuch.
- Wenn der Refresh nicht funktioniert, wird eine neue Anmeldung angefordert.
- Nach Spielende wird nur dann hochgeladen, wenn sich der lokale Spielstand geÃ¤ndert hat.
- Save-Ordner mit mehreren Dateien werden vollst?ndig gepr?ft und nicht nur ?ber eine Einzeldatei behandelt.
- Sobald sich mindestens eine Datei in einem Save-Ordner unterscheidet, wird eine Synchronisierung ausgel?st.
- Neue, fehlende oder gel?schte Dateien in einem Save-Ordner werden als ?nderung erkannt.

## Offene Architekturidee fÃ¼r die spÃ¤tere Umsetzung
- QML fÃ¼r OberflÃ¤che
- Python-Backend fÃ¼r GeschÃ¤ftslogik
- getrennte Module fÃ¼r:
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
- [x] Darkmode als festes UI-Design für die QML-Oberfläche umsetzen
- [x] JSON-Export für Spieleprofile implementieren
- [x] JSON-Import mit Validierung implementieren
- [x] Google-Drive-Ordner-ID pro Profil konfigurierbar machen
- [x] OAuth-Handling für Token-Refresh und Re-Login robuster machen
- [x] Statusanzeige für Auth, Download, Spielstatus und Upload in der UI darstellen
- [x] Fehlerbehandlung für fehlende Dateien, ungültige Konfiguration und Drive-Probleme ergänzen
- [x] Synchronisationsablauf aus dem bestehenden Skript in die neue Architektur überführen
- [x] Save-Ordner mit mehreren Dateien in der Backend-Logik unterstützen
- [x] Über alle Dateien im konfigurierten Save-Ordner iterieren und pro Datei Hashes berechnen
- [x] Dateiänderungen, fehlende Dateien und neue Dateien im Save-Ordner als Sync-Trigger behandeln
- [x] Cloud-Abgleich für ordnerbasierte Saves über ZIP-Archive implementieren
- [x] Tests für Mehrdatei-Saves und ordnerbasierte Synchronisation ergänzen
- [ ] Zusätzliche Abnahmetests für UI-Workflows, reale OAuth-Fehlerfälle und Google-Drive-Smoke-Tests durchführen

