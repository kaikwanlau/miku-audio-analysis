# ===================================================================================
#
# STEP 3: FEATURE EXTRACTION
#
# This script performs the core signal processing and acoustic feature extraction.
#
# Actions:
# 1. Loads local audio files using `librosa` (resampled to 22,050 Hz).
# 2. Extracts 12 key acoustic metrics, including:
#    - Temporal: BPM (Tempo), Onset Density (Notes per second), Duration.
#    - Spectral: Spectral Centroid (Brightness), Spectral Flux, Rolloff.
#    - Dynamic: RMS Energy, Loudness (LUFS proxy).
# 3. Computes "Rhythm Complexity" using entropy measures of the onset envelope.
# 4. Appends computed feature vectors to the master metadata dataframe.
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
import warnings
import numpy as np
import pandas as pd
import librosa
from scipy import stats
from tqdm import tqdm

warnings.filterwarnings("ignore")

INPUT_EXCEL = "miku_with_paths.xlsx"
OUTPUT_EXCEL = "miku_fully_analyzed.xlsx"
ANALYSIS_LOG = "analysis_log.json"
SAMPLE_RATE = 22050
HOP_LENGTH = 512

FEATURE_COLS = [
    "BPM", "BPM_Confidence", "Onset_Density", "Tempo_Stability",
    "RMS_Energy", "Dynamic_Range_dB", "Energy_Entropy", "Loudness_LUFS_approx",
    "Spectral_Centroid_Hz", "Spectral_Flux_Mean", "Spectral_Flux_Std",
    "Spectral_Rolloff_Hz", "Zero_Crossing_Rate",
    "Harmonic_Change_Rate", "Key", "Mode", "Key_Confidence",
    "Rhythm_Complexity", "Avg_Note_Duration_s",
]


KEY_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
                           2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                           2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def extract_features(audio_path):
    """Extract all 19 scientific features from an audio file."""
    result = {}

    y, sr = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)
    result["Analyzed_Duration"] = round(duration, 1)

    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=HOP_LENGTH)
    bpm = float(np.atleast_1d(tempo)[0])
    result["BPM"] = round(bpm, 1)

    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP_LENGTH)
    ac = librosa.autocorrelate(onset_env, max_size=len(onset_env))
    ac_norm = ac / (ac[0] + 1e-10)
    bpm_lag = int(round(60.0 * sr / (bpm * HOP_LENGTH)))
    result["BPM_Confidence"] = round(float(ac_norm[min(bpm_lag, len(ac_norm) - 1)]), 3)

    onsets = librosa.onset.onset_detect(y=y, sr=sr, hop_length=HOP_LENGTH)
    onset_times = librosa.frames_to_time(onsets, sr=sr, hop_length=HOP_LENGTH)
    result["Onset_Density"] = round(len(onset_times) / max(duration, 0.1), 2)

    if len(beat_frames) > 2:
        beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=HOP_LENGTH)
        ibis = np.diff(beat_times)
        ibis = ibis[ibis > 0]
        if len(ibis) > 1:
            local_bpms = 60.0 / ibis
            cv = np.std(local_bpms) / (np.mean(local_bpms) + 1e-10)
            result["Tempo_Stability"] = round(max(0, min(1, 1 - cv)), 3)
        else:
            result["Tempo_Stability"] = None
    else:
        result["Tempo_Stability"] = None


    rms = librosa.feature.rms(y=y, hop_length=HOP_LENGTH)[0]
    result["RMS_Energy"] = round(float(np.mean(rms)), 6)

    rms_db = librosa.amplitude_to_db(rms, ref=np.max)
    result["Dynamic_Range_dB"] = round(float(np.max(rms_db) - np.min(rms_db)), 2)

    rms_norm = rms / (np.sum(rms) + 1e-10)
    entropy = -np.sum(rms_norm * np.log2(rms_norm + 1e-10))
    max_ent = np.log2(len(rms_norm)) if len(rms_norm) > 0 else 1
    result["Energy_Entropy"] = round(float(entropy / (max_ent + 1e-10)), 3)

    rms_sq = np.mean(rms ** 2)
    result["Loudness_LUFS_approx"] = round(-0.691 + 10 * np.log10(rms_sq + 1e-10), 2) if rms_sq > 0 else None


    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=HOP_LENGTH)[0]
    result["Spectral_Centroid_Hz"] = round(float(np.mean(centroid)), 1)

    S = np.abs(librosa.stft(y, hop_length=HOP_LENGTH))
    flux = np.sqrt(np.sum(np.diff(S, axis=1) ** 2, axis=0))
    result["Spectral_Flux_Mean"] = round(float(np.mean(flux)), 4)
    result["Spectral_Flux_Std"] = round(float(np.std(flux)), 4)

    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=HOP_LENGTH, roll_percent=0.85)[0]
    result["Spectral_Rolloff_Hz"] = round(float(np.mean(rolloff)), 1)

    zcr = librosa.feature.zero_crossing_rate(y, hop_length=HOP_LENGTH)[0]
    result["Zero_Crossing_Rate"] = round(float(np.mean(zcr)), 5)


    try:
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=HOP_LENGTH)
        chroma_diff = np.sum(np.abs(np.diff(chroma, axis=1)), axis=0)
        result["Harmonic_Change_Rate"] = round(float(np.mean(chroma_diff)), 4)

        chroma_mean = np.mean(chroma, axis=1)
        best_corr, best_key, best_mode = -1, "C", 1
        for shift in range(12):
            shifted = np.roll(chroma_mean, -shift)
            c_maj = np.corrcoef(shifted, MAJOR_PROFILE)[0, 1]
            c_min = np.corrcoef(shifted, MINOR_PROFILE)[0, 1]
            if c_maj > best_corr:
                best_corr, best_key, best_mode = c_maj, KEY_NAMES[shift], 1
            if c_min > best_corr:
                best_corr, best_key, best_mode = c_min, KEY_NAMES[shift], 0
        result["Key"] = best_key
        result["Mode"] = best_mode
        result["Key_Confidence"] = round(float(best_corr), 3)
    except Exception:
        result["Harmonic_Change_Rate"] = None
        result["Key"] = None
        result["Mode"] = None
        result["Key_Confidence"] = None


    if len(onset_times) > 2:
        ioi = np.diff(onset_times)
        ioi = ioi[ioi > 0]
        if len(ioi) > 1:
            hist, _ = np.histogram(ioi, bins=50, density=True)
            hist = hist / (np.sum(hist) + 1e-10)
            result["Rhythm_Complexity"] = round(float(-np.sum(hist * np.log2(hist + 1e-10))), 3)
        else:
            result["Rhythm_Complexity"] = None
    else:
        result["Rhythm_Complexity"] = None

    if result["Onset_Density"] > 0:
        result["Avg_Note_Duration_s"] = round(1.0 / result["Onset_Density"], 3)
    else:
        result["Avg_Note_Duration_s"] = None

    return result



def main():
    print("=" * 70)
    print("  STEP 3: Scientific Audio Feature Extraction")
    print("=" * 70)

    if not os.path.exists(INPUT_EXCEL):
        print(f"\n[ERROR] File not found: {INPUT_EXCEL}")
        print("  Run step2_download_audio.py first.")
        sys.exit(1)

    df = pd.read_excel(INPUT_EXCEL)
    print(f"\n[INFO] Loaded {len(df)} songs")

    has_audio = sum(1 for _, r in df.iterrows()
                    if pd.notna(r.get("Audio_Path")) and os.path.exists(str(r["Audio_Path"])))
    print(f"[INFO] Audio files available: {has_audio}/{len(df)}")

    if has_audio == 0:
        print("\n[ERROR] No audio files found. Run step2 first.")
        sys.exit(1)

    for col in FEATURE_COLS:
        if col not in df.columns:
            df[col] = None

    log = {}
    if os.path.exists(ANALYSIS_LOG):
        with open(ANALYSIS_LOG, "r", encoding="utf-8") as f:
            log = json.load(f)
        already_done = sum(1 for v in log.values() if v.get("success"))
        print(f"[INFO] Resuming — {already_done} already analyzed")

    success = 0
    failed = 0
    skipped_no_audio = 0

    print(f"\n{'─' * 70}")
    print(f"  Analyzing {has_audio} audio files...")
    print(f"  Estimated time: ~{has_audio * 3 / 60:.0f} minutes")
    print(f"{'─' * 70}\n")

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Analyzing"):
        year = int(row["Year"])
        rank = int(row["Rank"])
        log_key = f"{year}_{rank}"
        audio_path = row.get("Audio_Path")

        if pd.isna(audio_path) or not os.path.exists(str(audio_path)):
            skipped_no_audio += 1
            continue

        if log_key in log and log[log_key].get("success"):
            cached = log[log_key].get("features", {})
            for col in FEATURE_COLS:
                if col in cached and cached[col] is not None:
                    df.at[idx, col] = cached[col]
            success += 1
            continue

        try:
            features = extract_features(str(audio_path))
            for col in FEATURE_COLS:
                if col in features and features[col] is not None:
                    if col == "BPM" and pd.notna(row.get("VocaDB_BPM")):
                        df.at[idx, "BPM_librosa"] = features["BPM"]
                        df.at[idx, "BPM"] = row["VocaDB_BPM"]
                    else:
                        df.at[idx, col] = features[col]

            log[log_key] = {"success": True, "features": features}
            success += 1

        except Exception as e:
            log[log_key] = {"success": False, "error": str(e)}
            failed += 1

        if idx % 50 == 0:
            with open(ANALYSIS_LOG, "w", encoding="utf-8") as f:
                json.dump(log, f, ensure_ascii=False, indent=1)
            df.to_excel(OUTPUT_EXCEL, index=False)

    with open(ANALYSIS_LOG, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=1)

    if "BPM_librosa" not in df.columns:
        df["BPM_librosa"] = None

    df.to_excel(OUTPUT_EXCEL, index=False)

    print(f"\n{'═' * 70}")
    print(f"  STEP 3 COMPLETE")
    print(f"{'═' * 70}")
    print(f"  Successfully analyzed: {success}")
    print(f"  Failed:               {failed}")
    print(f"  No audio (skipped):   {skipped_no_audio}")
    print(f"\n  Output saved to:      {OUTPUT_EXCEL}")

    print(f"\n{'─' * 70}")
    print(f"  Quick Statistics:")
    print(f"{'─' * 70}")
    for col in ["BPM", "Onset_Density", "RMS_Energy", "Spectral_Centroid_Hz", "Duration (Seconds)"]:
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(vals) > 0:
                print(f"  {col:<25} mean={vals.mean():.2f}  std={vals.std():.2f}  "
                      f"range=[{vals.min():.1f}, {vals.max():.1f}]")

    print(f"\n  Next step: python step4_trend_analysis.py")
    print(f"{'═' * 70}\n")


if __name__ == "__main__":
    main()
