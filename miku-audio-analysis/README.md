<div align="center">

![fig_Aikotoba_V](https://github.com/user-attachments/assets/b0345b71-039f-4e72-8034-52e4a817cc0d)


# Are Vocaloid Songs Getting Denser?

### A Longitudinal Audio Analysis of 1,900 Hatsune Miku Songs (2007–2025)

[![Paper](https://img.shields.io/badge/📄_Paper-Knowledge_Commons-4ecdc4?style=for-the-badge)](https://doi.org/10.17613/yd6ys-m6e87)
[![Dataset](https://img.shields.io/badge/📊_Dataset-Excel_+_CSV-ff6b9d?style=for-the-badge)](#data)
[![Python](https://img.shields.io/badge/Python-3.9+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-a8edea?style=for-the-badge)](#license)

*This study is both a scientific inquiry and a love letter to Miku and the Vocaloid community — 18 years of songs, producers, and an ever-evolving sound.*

---

</div>

## Overview

This repository contains the full data pipeline, analysis scripts, and results for the paper:

> **Lau, K. (2026).** *Are Vocaloid Songs Getting Denser? A Longitudinal Audio Analysis of 1,900 Hatsune Miku Songs (2007–2025).* Knowledge Commons. https://doi.org/10.17613/yd6ys-m6e87

We analyzed **12 acoustic features** extracted from **1,900 songs** (100 per year, 2007–2025), ranked by community score on VocaDB/Niconico. The core finding: Vocaloid music has undergone **structural compression**. Songs are shorter, more harmonically active, rhythmically denser, and more complex. But barely any faster in raw BPM.

---

## Key Findings

| Metric | Trend | Change | p-value |
|--------|-------|--------|---------|
| BPM | ↑ Increasing | +2.3% | 0.004** |
| Onset Density | ↑ Increasing | +6.4% | 0.010** |
| Song Duration | ↓ Decreasing | −6.8% | 0.002** |
| Rhythm Complexity | ↑ Increasing | +9.1% | <0.001*** |
| Harmonic Change Rate | ↑ Increasing | +8.0% | 0.042* |
| Tempo Stability | ↓ Decreasing | −0.7% | <0.001*** |

**The core insight:** Songs didn't get much *faster*. They got *denser*. More notes, more chords, more rhythmic variety, crammed into less time. A post-2020 inflection point coincides with the rise of TikTok and YouTube Shorts in Japan.

<div align="center">

</div>

---

## Repository Structure

```
miku-audio-analysis/
│
├── data/
│   ├── miku_advanced_data.xlsx       # Metadata: 1,900 songs from VocaDB (2007–2025)
│   └── miku_trend_statistics.xlsx    # Statistical results: Mann-Kendall, Sen's Slope
│
├── scripts/
│   ├── excel_via_VocaDB.py           # Utility: metadata-only fetch from VocaDB API
│   ├── excel_via_spotify.py          # Utility: Spotify audio features (supplementary)
│   ├── step1_vocadb_fetch.py         # Step 1: Metadata + URL acquisition
│   ├── step2_download_audio.py       # Step 2: Batch audio download via yt-dlp
│   ├── step2_retry_failed.py         # Step 2b: Aggressive retry for failed downloads
│   ├── step3_analyze_audio.py        # Step 3: Librosa feature extraction (12 metrics)
│   └── step4_trend_analysis.py       # Step 4: Mann-Kendall tests + visualizations
│
└── README.md
```
> **Note:** Audio files are not included in this repository due to copyright. The full pipeline re-downloads them from public Niconico/YouTube sources.

---

## Methods

<img width="1550" height="524" alt="image" src="https://github.com/user-attachments/assets/5f067501-b0d7-4080-bd89-975eb38cb8bd" />


### Data Collection
- **Source:** Top 100 songs/year (2007–2025) by community rating on [VocaDB](https://vocadb.net)
- **Audio:** Downloaded via `yt-dlp` from Niconico and YouTube (192 kbps MP3)
- **Total:** 1,900 songs, 100% audio acquisition rate

### Feature Extraction (librosa v0.10, 22,050 Hz)

| Category | Features |
|----------|----------|
| **Tempo & Rhythm** | BPM, Onset Density, Tempo Stability, Rhythm Complexity |
| **Energy** | RMS Energy, Loudness (LUFS approx.) |
| **Spectral** | Spectral Centroid, Spectral Flux, Zero Crossing Rate |
| **Harmonic** | Harmonic Change Rate, Key, Mode |
| **Structure** | Duration |

### Statistical Tests
- **Mann-Kendall** non-parametric trend test (α = 0.05)
- **Sen's Slope** for trend magnitude estimation
- **Welch's t-test** + Cohen's *d* for era comparisons
- **Pearson & Spearman** correlations (Year × Feature)

---

## Era Analysis

The 19-year span was divided into four eras reflecting platform shifts:

<img width="1584" height="645" alt="image" src="https://github.com/user-attachments/assets/289ddf66-ce25-4e40-a6f1-b91a7343b78a" />


| Era | Years | n | Mean Duration |
|-----|-------|---|---------------|
| Early Vocaloid | 2007–2011 | 500 | 235.7 s |
| Growth | 2012–2016 | 500 | 248.1 s |
| Streaming | 2017–2020 | 400 | 230.6 s |
| Short-Video | 2021–2025 | 500 | **196.9 s** |

The **Short-Video era** (post-TikTok mainstream adoption in Japan, 2020–2021) saw the sharpest structural compression, with songs averaging ~40 seconds shorter than the Early era (Cohen's *d* = 0.61).

---

## Data

### `miku_advanced_data.xlsx`
Raw metadata for all 1,900 songs:

| Column | Description |
|--------|-------------|
| `Year` | Publication year (2007–2025) |
| `Rank` | Popularity rank within the year (1–100) |
| `Title (English)` | Song title in English |
| `Artist` | Producer/artist string |
| `Duration (Seconds)` | Song length |
| `BPM` | Tempo (VocaDB metadata or librosa estimate) |
| `Score` | VocaDB community rating score |

### `miku_trend_statistics.xlsx`
Statistical results for each metric:

| Column | Description |
|--------|-------------|
| `MK_Trend` | Mann-Kendall trend direction |
| `MK_p` | p-value |
| `MK_Tau` | Kendall's τ |
| `Sens_Slope/yr` | Rate of change per year |
| `Total_%_Change` | Endpoint percentage change (2007→2025) |

---

## Citation

If you use this code or dataset, please cite:

```bibtex
@misc{lau_2026_yd6ys-m6e87,
  author    = {Lau, Kaikwan},
  title     = {{Are Vocaloid Songs Getting Denser? A Longitudinal
                Audio Analysis of 1,900 Hatsune Miku Songs (2007--2025)}},
  month     = mar,
  year      = 2026,
  publisher = {Knowledge Commons},
  doi       = {10.17613/yd6ys-m6e87},
  url       = {https://doi.org/10.17613/yd6ys-m6e87}
}
```

---

## Acknowledgements

This work would not exist without the thousands of Vocaloid producers who have shared their music on Niconico and YouTube over the past 18 years — and the community at VocaDB who meticulously catalogued it all.

To every producer who ever made a Miku song: **ありがとう。** 💙

---

## License

This repository is licensed under the **MIT License**. The dataset is for research and educational use only. Audio files are not redistributed; all copyright remains with the original creators.

---

<div align="center">

*Made with 💙 for Hatsune Miku and the Vocaloid community*

**初音ミクへ、18年間の音楽をありがとう。**

*(To Hatsune Miku: thank you for 18 years of music.)*

</div>