# ===================================================================================
#
# STEP 1: METADATA ACQUISITION
#
# This script initiates the data collection pipeline for the paper:
# "Are Vocaloid Songs Getting Faster? A Longitudinal Audio Analysis of 1,900 Hatsune Miku Songs"
#
# Actions:
# 1. Connects to the VocaDB API to query the top 100 ranked songs per year (2007–2025).
# 2. Filters strictly for "Original" song types and "Hatsune Miku" (Artist ID: 1).
# 3. Extracts critical metadata: Song Titles (English/Japanese), Publish Date, and Rating Score.
# 4. Retreives external URL references (Niconico, YouTube) for subsequent audio acquisition.
# 5. Caches results locally to respect API rate limits and exports to Excel/CSV.
#
# Citation:
# If you use this code or dataset, please cite the following paper:
#
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
import json
import re
import requests
import pandas as pd
from tqdm import tqdm
from urllib.parse import quote

EXCEL_PATH = "miku_advanced_data.xlsx"
OUTPUT_EXCEL = "miku_with_urls.xlsx"
CACHE_FILE = "vocadb_cache.json"
VOCADB_API = "https://vocadb.net/api"
REQUEST_DELAY = 1.0          # seconds between API calls (be respectful)
USER_AGENT = "MikuSpeedResearch/1.0 (academic research project)"

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})


def search_vocadb(title_orig, title_en, artist_name):
    """
    Search VocaDB for a song by title. Try original title first,
    then English title. Returns the best matching song dict or None.
    """
    artist_clean = ""
    if pd.notna(artist_name):
        artist_clean = re.split(r'\s+feat\.?\s+', str(artist_name), flags=re.IGNORECASE)[0].strip()

    queries = []
    if pd.notna(title_orig) and str(title_orig).strip():
        queries.append(str(title_orig).strip())
    if pd.notna(title_en) and str(title_en).strip():
        queries.append(str(title_en).strip())

    for query in queries:
        try:
            params = {
                "query": query,
                "fields": "PVs,Names,MainPicture",
                "lang": "English",
                "maxResults": 10,
                "sort": "FavoritedTimes",
                "nameMatchMode": "Auto",
            }
            if artist_clean:
                params["artistName"] = artist_clean

            r = session.get(f"{VOCADB_API}/songs", params=params, timeout=15)
            r.raise_for_status()
            data = r.json()

            if data.get("items"):
                best = find_best_match(data["items"], title_orig, title_en, artist_clean)
                if best:
                    return best
            if artist_clean:
                params.pop("artistName", None)
                r = session.get(f"{VOCADB_API}/songs", params=params, timeout=15)
                r.raise_for_status()
                data = r.json()
                if data.get("items"):
                    best = find_best_match(data["items"], title_orig, title_en, artist_clean)
                    if best:
                        return best

        except requests.RequestException as e:
            print(f"    [WARN] API error for '{query}': {e}")
            continue

    return None


def find_best_match(items, title_orig, title_en, artist_clean):
    """Score and rank VocaDB search results to find the best match."""
    scored = []
    for item in items:
        score = 0
        name = item.get("name", "").lower()
        default_name = item.get("defaultName", "").lower()

        if pd.notna(title_orig):
            t_orig = str(title_orig).strip().lower()
            if t_orig == name or t_orig == default_name:
                score += 100
            elif t_orig in name or t_orig in default_name:
                score += 50

        if pd.notna(title_en):
            t_en = str(title_en).strip().lower()
            if t_en == name or t_en == default_name:
                score += 80
            elif t_en in name or t_en in default_name:
                score += 40

        song_type = item.get("songType", "")
        if song_type == "Original":
            score += 20
        elif song_type in ("Cover", "Remix", "Mashup"):
            score -= 30

        pvs = item.get("pvs", [])
        if pvs:
            score += 10

        artist_str = item.get("artistString", "").lower()
        if artist_clean and artist_clean.lower() in artist_str:
            score += 30

        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    if scored and scored[0][0] >= 30:
        return scored[0][1]
    return None


def extract_pvs(song_data):
    """Extract Niconico and YouTube URLs from VocaDB song PVs."""
    niconico_url = None
    youtube_url = None

    pvs = song_data.get("pvs", [])
    for pv in pvs:
        service = pv.get("service", "").lower()
        pv_type = pv.get("pvType", "")
        url = pv.get("url", "")

        # Prefer Original PVs over Reprints
        if service == "niconicodouga" and url:
            if niconico_url is None or pv_type == "Original":
                niconico_url = url
        elif service == "youtube" and url:
            if youtube_url is None or pv_type == "Original":
                youtube_url = url

    return niconico_url, youtube_url


def get_song_details(song_id):
    """Fetch full song details including BPM from VocaDB."""
    try:
        r = session.get(
            f"{VOCADB_API}/songs/{song_id}",
            params={"fields": "PVs,Names,Artists", "lang": "English"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None

def main():
    print("=" * 70)
    print("  STEP 1: VocaDB Metadata & URL Fetcher")
    print("=" * 70)

    if not os.path.exists(EXCEL_PATH):
        print(f"\n[ERROR] File not found: {EXCEL_PATH}")
        sys.exit(1)

    df = pd.read_excel(EXCEL_PATH)
    print(f"\n[INFO] Loaded {len(df)} songs from {EXCEL_PATH}")

    for col in ["VocaDB_ID", "VocaDB_BPM", "Niconico_URL", "YouTube_URL", "Download_URL"]:
        if col not in df.columns:
            df[col] = None

    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
        print(f"[INFO] Loaded {len(cache)} cached results")

    found = 0
    urls_found = 0
    bpm_found = 0

    print(f"\n{'─' * 70}")
    print("  Querying VocaDB API (this takes ~30-60 min for 1,900 songs)...")
    print(f"{'─' * 70}\n")

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Fetching"):
        year = row["Year"]
        rank = row["Rank"]
        title_en = row.get("Title (English)", "")
        title_orig = row.get("Title (Original)", "")
        artist = row.get("Artist", "")

        cache_key = f"{year}_{rank}"

        if cache_key in cache:
            cached = cache[cache_key]
            df.at[idx, "VocaDB_ID"] = cached.get("id")
            df.at[idx, "VocaDB_BPM"] = cached.get("bpm")
            df.at[idx, "Niconico_URL"] = cached.get("niconico")
            df.at[idx, "YouTube_URL"] = cached.get("youtube")
            df.at[idx, "Download_URL"] = cached.get("download_url")
            if cached.get("id"):
                found += 1
            if cached.get("download_url"):
                urls_found += 1
            if cached.get("bpm"):
                bpm_found += 1
            continue

        time.sleep(REQUEST_DELAY)
        result = search_vocadb(title_orig, title_en, artist)

        entry = {"id": None, "bpm": None, "niconico": None, "youtube": None, "download_url": None}

        if result:
            song_id = result.get("id")
            entry["id"] = song_id
            found += 1

            time.sleep(REQUEST_DELAY * 0.5)
            details = get_song_details(song_id)

            if details:
                bpm_val = details.get("maxMilliBpm")
                if bpm_val and bpm_val > 0:
                    entry["bpm"] = round(bpm_val / 1000, 1)
                    bpm_found += 1
                elif details.get("minMilliBpm") and details["minMilliBpm"] > 0:
                    entry["bpm"] = round(details["minMilliBpm"] / 1000, 1)
                    bpm_found += 1

                nico, yt = extract_pvs(details)
            else:
                nico, yt = extract_pvs(result)

            entry["niconico"] = nico
            entry["youtube"] = yt

            if nico:
                entry["download_url"] = nico
                urls_found += 1
            elif yt:
                entry["download_url"] = yt
                urls_found += 1

        df.at[idx, "VocaDB_ID"] = entry["id"]
        df.at[idx, "VocaDB_BPM"] = entry["bpm"]
        df.at[idx, "Niconico_URL"] = entry["niconico"]
        df.at[idx, "YouTube_URL"] = entry["youtube"]
        df.at[idx, "Download_URL"] = entry["download_url"]

        cache[cache_key] = entry
        if idx % 50 == 0:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=1)

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)

    for idx, row in df.iterrows():
        if pd.isna(row["BPM"]) and pd.notna(row.get("VocaDB_BPM")):
            df.at[idx, "BPM"] = row["VocaDB_BPM"]

    df.to_excel(OUTPUT_EXCEL, index=False)

    print(f"\n{'═' * 70}")
    print(f"  STEP 1 COMPLETE")
    print(f"{'═' * 70}")
    print(f"  Songs matched on VocaDB:    {found}/{len(df)} ({found/len(df)*100:.1f}%)")
    print(f"  Download URLs found:        {urls_found}/{len(df)} ({urls_found/len(df)*100:.1f}%)")
    print(f"  BPM from VocaDB:            {bpm_found}/{len(df)} ({bpm_found/len(df)*100:.1f}%)")
    print(f"\n  Output saved to: {OUTPUT_EXCEL}")
    print(f"  Cache saved to:  {CACHE_FILE}")
    print(f"\n  Next step: python step2_download_audio.py")
    print(f"{'═' * 70}\n")


if __name__ == "__main__":
    main()