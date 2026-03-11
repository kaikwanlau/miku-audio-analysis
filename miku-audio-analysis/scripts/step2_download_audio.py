# ===================================================================================
#
# STEP 2: AUDIO ACQUISITION
#
# This script handles the batch acquisition of audio samples required for feature extraction.
#
# Actions:
# 1. Reads the metadata dataset generated in Step 1.
# 2. Iterates through song entries and utilizes `yt-dlp` to fetch audio from Niconico or YouTube.
# 3. Standardizes audio format to MP3 (192kbps) to ensure consistent spectral analysis.
# 4. Implements search fallback logic if direct URLs are invalid.
# 5. Logs download success/failure rates for dataset completeness verification.
#
# Note:
# Audio files downloaded by this script are for local analysis only and are NOT
# included in the public repository due to copyright restrictions.
#
# Citation:
# @misc{lau_2026_yd6ys-m6e87,
#   author       = {Lau, kaikwan},
#   title        = {{Are Vocaloid Songs Getting denser? A Longitudinal
#                    Audio Analysis of 1,900 Hatsune Miku Songs (2007--
#                    2025)}},
#   month        = mar,
#   year         = 2026,
#   publisher    = {Knowledge Commons},
#   doi          = {10.17613/yd6ys-m6e87},
#   url          = {https://doi.org/10.17613/yd6ys-m6e87}
# }
#
# ===================================================================================

import os
import sys
import json
import time
import subprocess
import pandas as pd
from pathlib import Path
from tqdm import tqdm

FFMPEG_PATH = "/opt/homebrew/bin/ffmpeg"

INPUT_EXCEL = "miku_with_urls.xlsx"
AUDIO_DIR = "audio_files"
DOWNLOAD_LOG = "download_log.json"
OUTPUT_EXCEL = "miku_with_paths.xlsx"

AUDIO_FORMAT = "mp3"
AUDIO_QUALITY = "192"
SLEEP_MIN = 2
SLEEP_MAX = 5
MAX_RETRIES = 2
USE_SEARCH_FALLBACK = True

def check_ytdlp():
    """Verify yt-dlp is installed and FFmpeg exists at the specific path."""
    global FFMPEG_PATH

    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"\n[ERROR] 'yt-dlp' is not installed.")
        print("  Install with: pip install yt-dlp")
        sys.exit(1)

    if os.path.exists(FFMPEG_PATH) and os.access(FFMPEG_PATH, os.X_OK):
        print(f"[OK] Found FFmpeg at: {FFMPEG_PATH}")
    else:
        alt_path = "/usr/local/bin/ffmpeg"
        if os.path.exists(alt_path) and os.access(alt_path, os.X_OK):
             FFMPEG_PATH = alt_path
             print(f"[OK] Found FFmpeg at: {FFMPEG_PATH}")
        else:
            print(f"\n[ERROR] Could not find FFmpeg at {FFMPEG_PATH}")
            print(f"  We checked: {FFMPEG_PATH}")
            print("  Please verify the path using 'which ffmpeg' in Terminal.")
            sys.exit(1)


def download_audio(url, output_path, is_search=False):
    output_template = str(output_path).rsplit(".", 1)[0] + ".%(ext)s"

    cmd = [
        "yt-dlp",
        "--ffmpeg-location", FFMPEG_PATH,
        "--extract-audio",
        "--audio-format", AUDIO_FORMAT,
        "--audio-quality", AUDIO_QUALITY,
        "--output", output_template,
        "--no-playlist",
        "--no-overwrites",
        "--socket-timeout", "30",
        "--retries", "3",
        "--quiet",
        "--no-warnings",
    ]

    if is_search:
        cmd.append(f"ytsearch1:{url}")
    else:
        cmd.append(url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        expected = str(output_path)
        if os.path.exists(expected):
            return True

        base = str(output_path).rsplit(".", 1)[0]
        for ext in [".mp3", ".m4a", ".opus", ".ogg", ".wav", ".webm"]:
            if os.path.exists(base + ext):
                os.rename(base + ext, expected)
                return True

        return result.returncode == 0
    except Exception:
        return False


def sanitize_filename(name):
    """Remove characters that are invalid in filenames."""
    name = str(name)
    for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\n', '\r']:
        name = name.replace(char, '_')
    if len(name) > 100:
        name = name[:100]
    return name.strip().strip('.')

def main():
    print("=" * 70)
    print("  STEP 2: Batch Audio Downloader")
    print("=" * 70)

    check_ytdlp()

    if not os.path.exists(INPUT_EXCEL):
        print(f"\n[ERROR] File not found: {INPUT_EXCEL}")
        print("  Run step1_vocadb_fetch.py first.")
        sys.exit(1)

    df = pd.read_excel(INPUT_EXCEL)
    print(f"\n[INFO] Loaded {len(df)} songs")

    os.makedirs(AUDIO_DIR, exist_ok=True)
    years = sorted(df["Year"].unique())
    for year in years:
        os.makedirs(os.path.join(AUDIO_DIR, str(year)), exist_ok=True)

    log = {}
    if os.path.exists(DOWNLOAD_LOG):
        with open(DOWNLOAD_LOG, "r", encoding="utf-8") as f:
            log = json.load(f)
        print(f"[INFO] Resuming — {sum(1 for v in log.values() if v.get('success'))} already downloaded")

    if "Audio_Path" not in df.columns:
        df["Audio_Path"] = None

    success = 0
    failed = 0
    skipped = 0

    print(f"\n{'─' * 70}")
    print("  Downloading audio files...")
    print(f"{'─' * 70}\n")

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Downloading"):
        year = int(row["Year"])
        rank = int(row["Rank"])
        title_en = str(row.get("Title (English)", "unknown"))
        title_orig = row.get("Title (Original)", "")
        artist = row.get("Artist", "")
        download_url = row.get("Download_URL")

        log_key = f"{year}_{rank}"
        safe_title = sanitize_filename(title_en)
        filename = f"{rank:03d}_{safe_title}.{AUDIO_FORMAT}"
        output_path = os.path.join(AUDIO_DIR, str(year), filename)

        if log_key in log and log[log_key].get("success"):
            if os.path.exists(log[log_key].get("path", "")):
                df.at[idx, "Audio_Path"] = log[log_key]["path"]
                skipped += 1
                continue

        if os.path.exists(output_path):
            df.at[idx, "Audio_Path"] = output_path
            log[log_key] = {"success": True, "path": output_path, "source": "exists"}
            skipped += 1
            continue

        source = None
        is_search = False

        if pd.notna(download_url) and str(download_url).startswith("http"):
            source = str(download_url)
        elif USE_SEARCH_FALLBACK:
            artist_clean = str(artist).split("feat.")[0].strip() if pd.notna(artist) else ""
            if pd.notna(title_orig) and str(title_orig).strip():
                source = f"{title_orig} {artist_clean}".strip()
            else:
                source = f"{title_en} {artist_clean}".strip()
            is_search = True

        if not source:
            log[log_key] = {"success": False, "reason": "no_url"}
            failed += 1
            continue

        downloaded = False
        for attempt in range(MAX_RETRIES + 1):
            if download_audio(source, output_path, is_search=is_search):
                downloaded = True
                break
            if attempt < MAX_RETRIES:
                time.sleep(2)

        if downloaded and os.path.exists(output_path):
            df.at[idx, "Audio_Path"] = output_path
            log[log_key] = {"success": True, "path": output_path, "source": "url" if not is_search else "search"}
            success += 1
        else:
            log[log_key] = {"success": False, "reason": "failed"}
            failed += 1

        import random
        time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))

        if idx % 20 == 0:
            with open(DOWNLOAD_LOG, "w", encoding="utf-8") as f:
                json.dump(log, f, ensure_ascii=False, indent=1)

    with open(DOWNLOAD_LOG, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=1)
    df.to_excel(OUTPUT_EXCEL, index=False)

    print(f"\n{'═' * 70}")
    print(f"  STEP 2 COMPLETE")
    print(f"  New: {success} | Skipped: {skipped} | Failed: {failed}")
    print(f"  Output: {OUTPUT_EXCEL}")
    print(f"{'═' * 70}\n")

if __name__ == "__main__":
    main()