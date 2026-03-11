# ===================================================================================
#
# UTILITY: VocaDB METADATA FETCHER (STANDALONE)
#
# This script serves as a lightweight alternative to the main Step 1 pipeline.
# It queries the VocaDB API to retrieve song metadata without the subsequent
# URL-fetching logic found in the main pipeline.
#
# Actions:
# 1. Queries VocaDB for the top 100 songs per year (2007–2025) for "Hatsune Miku".
# 2. Extracts core metadata: Title, Artist, Duration, BPM (if available), and Rating.
# 3. Exports the raw dataset to Excel for quick inspection or preliminary analysis.
#
# Usage:
# Run this script if you only need the metadata spreadsheet and do not intend
# to download audio files immediately.
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

import requests
import pandas as pd
import time
from datetime import datetime

START_YEAR = 2007
END_YEAR = 2025
SONGS_PER_YEAR = 100
OUTPUT_FILE = "miku_advanced_data.xlsx"

BASE_URL = "https://vocadb.net/api/songs"

print(f"Starting Advanced Data Collection ({START_YEAR}-{END_YEAR})...")
print(f"Target: Top {SONGS_PER_YEAR} songs per year.")
print("Note: This will perform ~2000 API calls. Please be patient (approx. 5-10 mins).")
print("-" * 60)

all_data = []

for year in range(START_YEAR, END_YEAR + 1):
    print(f"Processing Year: {year}...")

    params = {
        'start': 0,
        'maxResults': SONGS_PER_YEAR,
        'sort': 'RatingScore',
        'songTypes': 'Original',
        'artistId': 1,
        'afterDate': f"{year}-01-01",
        'beforeDate': f"{year}-12-31",
        'fields': 'AdditionalNames',
        'lang': 'English'
    }

    try:
        response = requests.get(BASE_URL, params=params)
        songs = response.json()['items']

        for i, song in enumerate(songs):

            english_title = song.get('name')
            original_title = song.get('defaultName')

            try:
                details_url = f"{BASE_URL}/{song['id']}"
                details_resp = requests.get(details_url, params={'fields': 'Bpm'})
                details_data = details_resp.json()

                bpm = details_data.get('minMidiNotify', {}).get('bpm')
                if not bpm:
                    bpm = None
            except:
                bpm = None

            all_data.append({
                'Year': year,
                'Rank': i + 1,
                'Title (English)': english_title,
                'Title (Original)': original_title,
                'Artist': song['artistString'],
                'Duration (Seconds)': song['lengthSeconds'],
                'BPM': bpm,
                'Publish Date': song['publishDate'].split('T')[0],
                'Score': song['ratingScore']
            })

            if (i + 1) % 10 == 0:
                print(f"  > {year}: Collected {i + 1}/{SONGS_PER_YEAR} songs...")

            time.sleep(0.1)

    except Exception as e:
        print(f"  > Error fetching {year}: {e}")

print("-" * 60)
print("Saving to Excel...")

df = pd.DataFrame(all_data)

df.to_excel(OUTPUT_FILE, index=False)

print(f"SUCCESS! Data saved to '{OUTPUT_FILE}'")
print(f"Total Songs Collected: {len(df)}")