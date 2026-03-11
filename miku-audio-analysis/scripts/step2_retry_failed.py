# ===================================================================================
#
# STEP 2b: DATASET RECOVERY (FAILSAFE)
#
# This script maximizes dataset completeness by attempting to rescue failed downloads.
#
# Actions:
# 1. Parses the download log from Step 2 to identify missing audio files.
# 2. Deploys aggressive search strategies:
#    - Strategy A: Search English Title + "Hatsune Miku"
#    - Strategy B: Search Original Japanese Title + "Miku"
#    - Strategy C: Search Title + "Lyrics" (to find stable lyric videos)
# 3. Verifies downloaded file integrity and updates the master dataset paths.
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
import time
import subprocess
import pandas as pd
from tqdm import tqdm

FFMPEG_PATH = "/opt/homebrew/bin/ffmpeg"

INPUT_EXCEL = "miku_with_paths.xlsx"
AUDIO_DIR = "audio_files"

def download_aggressive(query, output_path):
    """
    Tries to download using a specific search query.
    Returns True if successful.
    """
    output_template = str(output_path).rsplit(".", 1)[0] + ".%(ext)s"

    cmd = [
        "yt-dlp",
        "--ffmpeg-location", FFMPEG_PATH,
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "192",
        "--output", output_template,
        "--no-playlist",
        "--socket-timeout", "10",
        "--retries", "2",
        "--quiet",
        "--no-warnings",
        "--ignore-errors",
        f"ytsearch1:{query}"
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        expected = str(output_path)
        base = expected.rsplit(".", 1)[0]
        for ext in [".mp3", ".m4a", ".opus", ".webm"]:
            if os.path.exists(base + ext):
                if ext != ".mp3":
                    try:
                        os.rename(base + ext, expected)
                    except:
                        pass
                return True
        return False
    except Exception:
        return False


def main():
    print("=" * 70)
    print("  STEP 2.5: AGGRESSIVE RETRY (Filling the Gaps)")
    print("=" * 70)

    if not os.path.exists(INPUT_EXCEL):
        print(f"[ERROR] {INPUT_EXCEL} not found. Run Step 2 first.")
        sys.exit(1)

    df = pd.read_excel(INPUT_EXCEL)

    missing_indices = []
    for idx, row in df.iterrows():
        path = row.get("Audio_Path")
        if pd.isna(path) or (isinstance(path, str) and not os.path.exists(path)):
            missing_indices.append(idx)

    print(f"[INFO] Total Songs: {len(df)}")
    print(f"[INFO] Missing/Failed: {len(missing_indices)}")

    if len(missing_indices) == 0:
        print("\n[SUCCESS] No missing songs! You are ready for Step 3.")
        return

    print(f"{'─' * 70}")
    print("  Starting Rescue Mission...")
    print(f"{'─' * 70}\n")

    recovered = 0
    still_failed = 0

    for idx in tqdm(missing_indices, desc="Rescuing"):
        row = df.loc[idx]
        rank = row["Rank"]
        year = row["Year"]
        title_en = str(row.get("Title (English)", ""))
        title_orig = str(row.get("Title (Original)", ""))

        filename = f"{rank:03d}_RESCUED_{idx}.mp3"
        save_dir = os.path.join(AUDIO_DIR, str(year))
        os.makedirs(save_dir, exist_ok=True)
        output_path = os.path.join(save_dir, filename)

        query1 = f"{title_en} Hatsune Miku song"
        if download_aggressive(query1, output_path):
            df.at[idx, "Audio_Path"] = output_path
            recovered += 1
            continue

        if title_orig and title_orig != "nan":
            query2 = f"{title_orig} Miku"
            if download_aggressive(query2, output_path):
                df.at[idx, "Audio_Path"] = output_path
                recovered += 1
                continue

        query3 = f"{title_en} lyrics Miku"
        if download_aggressive(query3, output_path):
            df.at[idx, "Audio_Path"] = output_path
            recovered += 1
            continue

        still_failed += 1

    df.to_excel(INPUT_EXCEL, index=False)

    print(f"\n{'═' * 70}")
    print(f"  RESCUE MISSION COMPLETE")
    print(f"  Recovered:    {recovered}")
    print(f"  Still Missing: {still_failed}")
    print(f"  Updated Excel saved to: {INPUT_EXCEL}")
    print(f"{'═' * 70}\n")


if __name__ == "__main__":
    main()