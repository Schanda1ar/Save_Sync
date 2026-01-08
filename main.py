import subprocess
import psutil
import time
import hashlib
import os
import json
from pathlib import Path
from configparser import ConfigParser
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# -------------------------------
# CONFIG.INI EINLESEN
# -------------------------------
if getattr(__import__('sys'), 'frozen', False):
    BASE_DIR = Path(__import__('sys').executable).parent
else:
    BASE_DIR = Path(__file__).parent

CONFIG_PATH = BASE_DIR / "config.ini"
if not CONFIG_PATH.exists():
    raise FileNotFoundError(f"config.ini nicht gefunden: {CONFIG_PATH}")

config = ConfigParser()
config.read(CONFIG_PATH)

SAVE_FILE = Path(config["paths"]["save_file"])          # Lokale Speicherdatei
GAME_EXE = Path(config["paths"]["game_exe"])            # Spiel-Executable
DRIVE_FILENAME = config["paths"]["drive_filename"]      # Name auf Google Drive
DRIVE_FOLDER_ID = config["paths"].get("drive_folder_id", "").strip()  # Optionaler Ordner
GAME_PROCESS_NAMES = [name.strip() for name in config["paths"]["game_process_names"].split(",")]

# -------------------------------
# CREDENTIALS-PFAD
# -------------------------------
DOCS_PATH = Path.home() / "Documents" / "SaveSync"
DOCS_PATH.mkdir(parents=True, exist_ok=True)
CREDENTIALS_PATH = DOCS_PATH / "mycreds.txt"

# Meta-Datei für Hash-Speicherung
META_FILE = SAVE_FILE.with_suffix(".meta.json")

# -------------------------------
# HILFSFUNKTIONEN
# -------------------------------
def calc_hash(path: Path):
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def save_meta(meta_info, path):
    with open(path, "w") as f:
        json.dump(meta_info, f)

def load_meta(path):
    if not path.exists():
        return None
    with open(path, "r") as f:
        return json.load(f)

# -------------------------------
# GOOGLE DRIVE AUTHENTIFIZIERUNG
# -------------------------------
gauth = GoogleAuth()
gauth.LoadClientConfigFile(str(BASE_DIR / "client_secrets.json"))

# Erzwinge immer neue Zustimmung und Offline-Token
gauth.settings['get_refresh_token'] = True
gauth.settings['access_type'] = 'offline'
gauth.settings['prompt'] = 'consent'


if CREDENTIALS_PATH.exists():
    gauth.LoadCredentialsFile(str(CREDENTIALS_PATH))

if gauth.credentials is None:
    print("🔑 Anmeldung im Browser erforderlich ...")
    gauth.LocalWebserverAuth()
    gauth.SaveCredentialsFile(str(CREDENTIALS_PATH))
elif gauth.access_token_expired:
    gauth.Refresh()
    gauth.SaveCredentialsFile(str(CREDENTIALS_PATH))
else:
    gauth.Authorize()

drive = GoogleDrive(gauth)

# -------------------------------
# DOWNLOAD-FUNKTION
# -------------------------------
def download_if_needed():
    # Query erstellen
    if DRIVE_FOLDER_ID:
        query = f"'{DRIVE_FOLDER_ID}' in parents and title='{DRIVE_FILENAME}' and trashed=false"
    else:
        query = f"title='{DRIVE_FILENAME}' and trashed=false"

    file_list = drive.ListFile({'q': query}).GetList()
    cloud_hash = None

    if file_list:
        # Temporäre Datei herunterladen zum Hashvergleich
        file_list[0].GetContentFile("tmp_drive_save.sav")
        cloud_hash = calc_hash(Path("tmp_drive_save.sav"))
        os.remove("tmp_drive_save.sav")

    local_hash = calc_hash(SAVE_FILE)

    if cloud_hash and cloud_hash != local_hash:
        print("⬇️ Cloud-Save ist neuer. Download wird ausgeführt...")
        backup_path = SAVE_FILE.with_name(f"{SAVE_FILE.stem}_backup_{int(time.time())}{SAVE_FILE.suffix}")
        if SAVE_FILE.exists():
            os.rename(SAVE_FILE, backup_path)
            print(f"💾 Backup erstellt: {backup_path.name}")
        file_list[0].GetContentFile(str(SAVE_FILE))
        local_hash = calc_hash(SAVE_FILE)  # Update Hash nach Download
    else:
        print("✅ Lokale Datei ist aktuell, kein Download nötig.")

    return local_hash, cloud_hash, file_list

# -------------------------------
# UPLOAD-FUNKTION
# -------------------------------
def upload_if_needed(initial_local_hash, final_local_hash, cloud_hash, file_list):
    if final_local_hash == initial_local_hash:
        print("⚠️ Lokale Datei wurde während des Spiels nicht geändert. Upload wird übersprungen.")
        return
    if cloud_hash and final_local_hash == cloud_hash:
        print("⚠️ Lokale Datei ist gleich wie Cloud. Upload wird übersprungen.")
        return

    print("⬆️ Lokale Datei geändert und neuer als Cloud → Upload wird ausgeführt.")
    if file_list:
        drive_file = file_list[0]
    else:
        file_info = {'title': DRIVE_FILENAME}
        if DRIVE_FOLDER_ID:
            file_info['parents'] = [{'id': DRIVE_FOLDER_ID}]
        drive_file = drive.CreateFile(file_info)

    drive_file.SetContentFile(str(SAVE_FILE))
    drive_file.Upload()
    save_meta({"hash": final_local_hash}, META_FILE)
    print("✅ Upload abgeschlossen.")

# -------------------------------
# LAUNCHER-LOGIK
# -------------------------------
if __name__ == "__main__":
    print("=== SYNC VOR SPIELSTART ===")
    initial_local_hash, cloud_hash, file_list = download_if_needed()

    
    process = subprocess.Popen([str(GAME_EXE)], shell=True)

    print("\n🎮 Warten auf Spiel fertig gestartet...")
    time.sleep(20)
    print("\n🎮 Spiel wird gestartet...")

    def any_game_process_running():
        return any(p.name() in GAME_PROCESS_NAMES for p in psutil.process_iter())

    while any_game_process_running():
        time.sleep(2)
    print("🎮 Spiel beendet.")

    print("\n=== SYNC NACH SPIELENDE ===")
    final_local_hash = calc_hash(SAVE_FILE)
    upload_if_needed(initial_local_hash, final_local_hash, cloud_hash, file_list)
    print("✅ Synchronisierung abgeschlossen.")
