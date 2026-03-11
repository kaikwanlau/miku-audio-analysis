# ===================================================================================
#
# UTILITY: SPOTIFY API DATA COLLECTOR
#
# This script provides an alternative method for gathering audio features using
# Spotify's pre-computed descriptors (Energy, Valence, Danceability) instead of
# raw audio analysis.
#
# Actions:
# 1. Authenticates with the Spotify Web API (requires valid Client ID/Secret).
# 2. Searches for "Hatsune Miku" tracks year-by-year (2007–2025).
# 3. Retrieves Spotify's internal audio features:
#    - BPM (Tempo)
#    - Energy & Danceability (Perceptual metrics)
#    - Valence (Musical positiveness)
# 4. Exports data to CSV for comparison with Librosa-based results.
#
# Note:
# This script is supplementary. The main paper results rely on direct audio
# analysis (Librosa) rather than Spotify's "Black Box" algorithms.
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

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import pandas as pd
import time

CLIENT_ID = 'YOUR_SPOTIFY_CLIENT_ID'
CLIENT_SECRET = 'YOUR_SPOTIFY_CLIENT_SECRET'

client_credentials_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

START_YEAR = 2007
END_YEAR = 2025
SONGS_PER_YEAR = 100
SEARCH_QUERY = "artist:Hatsune Miku"

all_data = []

print(f"Starting Data Collection: {START_YEAR} to {END_YEAR}...")
print("-" * 60)

for year in range(START_YEAR, END_YEAR + 1):
    print(f"Processing Year: {year}...")

    query = f"{SEARCH_QUERY} year:{year}-{year}"

    try:
        results = sp.search(q=query, type='track', limit=SONGS_PER_YEAR)
        tracks = results['tracks']['items']

        if not tracks:
            print(f"  Warning: No songs found for {year}. Skipping.")
            continue

        track_ids = [track['id'] for track in tracks]

        audio_features = sp.audio_features(track_ids)

        for track, features in zip(tracks, audio_features):
            if features:
                song_data = {
                    'year': year,
                    'track_name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'popularity': track['popularity'],
                    'bpm': features['tempo'],
                    'duration_sec': features['duration_ms'] / 1000,
                    'energy': features['energy'],
                    'danceability': features['danceability'],
                    'valence': features['valence']
                }
                all_data.append(song_data)

        print(f"  > Successfully collected {len(tracks)} songs.")

        time.sleep(2)

    except Exception as e:
        print(f"  > Error fetching {year}: {e}")

print("-" * 60)
df = pd.DataFrame(all_data)

filename = 'miku_evolution_data.csv'
df.to_csv(filename, index=False)

print(f"DONE! Data saved to '{filename}'")
print(f"Total Songs Collected: {len(df)}")
print("Average BPM by Year preview:")
print(df.groupby('year')['bpm'].mean())