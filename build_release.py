import os
import shutil
import subprocess
from pathlib import Path
from zipfile import ZipFile

# ===== CONFIG =====
PROJECT_ROOT = Path(__file__).parent
DIST_NAME = "kcw_pos_companion"
ENTRY_FILE = "app.py"  # <-- change if needed

OUTPUT_DIR = Path(r"G:\Shared drives\KCW-Data\kcw_analytics\04_outputs\91_kcw_pos_companion")
BUILD_DIR = PROJECT_ROOT / "dist"
RELEASE_DIR = PROJECT_ROOT / DIST_NAME

# ===== CLEAN =====
if RELEASE_DIR.exists():
    shutil.rmtree(RELEASE_DIR)

# ===== BUILD EXE =====
print("Building EXE...")
subprocess.run([
    "pyinstaller",
    "--onefile",
    "--noconsole",
    ENTRY_FILE
], check=True)

# ===== PREP RELEASE FOLDER =====
print("Preparing release folder...")
RELEASE_DIR.mkdir(parents=True, exist_ok=True)

# Copy EXE
exe_name = ENTRY_FILE.replace(".py", ".exe")
shutil.copy(BUILD_DIR / exe_name, RELEASE_DIR / exe_name)

# Copy .env
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    shutil.copy(env_file, RELEASE_DIR / ".env")
else:
    print("WARNING: .env not found")

# ===== ZIP =====
zip_path = PROJECT_ROOT / f"{DIST_NAME}.zip"

print("Zipping...")
with ZipFile(zip_path, 'w') as zipf:
    for file in RELEASE_DIR.rglob("*"):
        zipf.write(file, file.relative_to(RELEASE_DIR.parent))

# ===== COPY TO SHARED DRIVE =====
print("Copying to shared drive...")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
shutil.copy(zip_path, OUTPUT_DIR / zip_path.name)

print("Done:", OUTPUT_DIR / zip_path.name)