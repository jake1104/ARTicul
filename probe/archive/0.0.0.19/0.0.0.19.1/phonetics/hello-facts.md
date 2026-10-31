# American English "hello" — ground-truth phonetics vs engine tables (0.0.0.19.1)

Demo input: X-SAMPA `hE "loU`, segments `[h E l o U]`, stress on `o`.
Engine plan (utterance): `h 78ms 134.70->131.94 | E 89ms 131.94->133.18 |
l 50ms 133.18->155.55 | o 148ms 155.55->80.09 | U 83ms 80.09->80.09`
(448 ms; source: `probe/archive/0.0.0.18/0.0.0.18.1/frontend/plan.txt:55-60`).
Engine vowel synthesis: static per-segment cascade targets + raised-cosine
inter-segment glide (`crates/articul-cli/src/synth.rs:424-456`).

## 1. Ground-truth values

### 1a. Citation form
- GA narrow transcription: **[həˈloʊ]** — reduced schwa-like first vowel,
  primary stress on the second syllable, GOAT diphthong /oʊ/ as the nucleus.
  (Textbook consensus: Wells lexical sets HE + GOAT; Ladefoged & Johnson vowel/diphthong
  inventory. Note the demo input writes a full `E` where nature has [ə].)
- Male mean speaking F0 ≈ **118–132 Hz** (Peterson & Barney 1952 list per-vowel
  pitch for 76 speakers; grand mean for men ≈ 132 Hz — Yang, cit. in
  eksss PSS 10(4):31). Engine `base_f0 = 120.0` is compatible.

### 1b. Monophthong anchors (adult male means, Peterson & Barney 1952)
Canonical values as reproduced in textbooks / Praat "Create formant table
(Peterson & Barney 1952)" (source page fetched 2026-10-28):

| vowel (P&B word) | F1 (Hz) | F2 (Hz) | F3 (Hz) |
|---|---|---|---|
| /ɛ/ (head) | ~530–580 | ~1790–1840 | ~2480–2520 |
| /ɔ/ (hawed) | ~570 | ~840 | ~2410 |
| /ʊ/ (hood) | ~440 | ~1020 | ~2240 |

- Hillenbrand et al. 1995 (139 speakers) superset: formants sampled at steady
  state **and** 20/50/80% of duration (`vowdata.dat`; dataset readme fetched
  2026-10-28) — i.e. the reference methodology itself treats vowels as
  **dynamic**, and American /oʊ/ ("oa", as in "hoed") is a diphthong, not a
  steady state. Diphthongs are defined by formant movement, F2 movement most
  prominent (Lee et al. 2014, J. Acoust. Soc. Am. developmental diphthong study).
- GOAT /oʊ/ trajectory (P&B anchors): onset ≈ [o] (F1 ~480–570, F2 ~840–950)
  → offglide ≈ [ʊ] (F1 ~400–440, F2 ~1000–1120): **F1 falls, F2 rises slightly**.
  One syllable, continuous glide — never two steady states.

### 1c. /h/ — voiceless transition, not a noise burst
- [h] "has no inherent place or manner of articulation"; "the shape of the
  vocal tract is often simply that of the surrounding sounds" — a voiceless /
  breathy counterpart of the following vowel (Ladefoged & Maddieson 1996:325–326,
  via Wikipedia "Voiceless glottal fricative", fetched 2026-10-28).
- English /h/ before /ə~ɛ/ = **voiceless [ə~ɛ]-shaped resonance**: formants ≈
  the following vowel's (≈ F1 500–580, F2 1500–1650), turbulence **weakest of
  all fricatives, strongest around ~1000 Hz** (EdUHK Phonetics & Phonology 3.2.2E,
  fetched 2026-10-28). No voicing bar word-initially; medially breathy-voiced.

### 1d. /l/ in "hello" — clear [l] (stressed-syllable onset), not dark [ɫ]
- GA allophony: clear [l] before vowels ("lady"), dark [ɫ] before consonants /
  finally ("bold", "tell") (EdUHK 3.2.4D, fetched 2026-10-28). /l/ in /həˈloʊ/
  is the **onset of the stressed syllable → canonically clear [l]** (some NA
  intervocalic darkening exists — Mackenzie 2018 — but the target is light).
- Clear [l]: **F1 200–400, F2 950–1500 (light /l/ F2 > 1500), F3 2700–3200**;
  dark [ɫ]: F1 350–550, **F2 650–850**, F3 2200–2700 (Cox via EdUHK 3.2.4D;
  Rodrigues et al. 2019 review: dark-/l/ F2 ≈ 1000, light-/l/ F2 > 1500).
  Approximants generally: low F1 (<1000 Hz), faint but visible formant structure,
  highly resonant, **no turbulence** (EdUHK 3.2.4, fetched 2026-10-28).
- Expected for hello's /l/: F1 ~300, F2 ~1300–1600, F3 ~2700–3000.

### 1e. Natural segment durations (citation-form "hello", ~450–550 ms total)
Typical ranges (Klatt-style intrinsic data; stress-shortening in spontaneous
English — Chodroff 2026; Tanner et al. 2019 — qualitative direction cited,
numbers are consensus synthesis):
- /h/: ~80–110 ms (voiceless, pre-vocalic).
- Reduced /hə/ vowel: **~50–70 ms** (unstressed ≈ 0.5–0.6× stressed — engine's
  ×0.55 factor itself is correct in size).
- Intervocalic onset /l/: **~60–80 ms**.
- Stressed /loʊ/ rhyme: **~200–280 ms total**, realized as ONE diphthong with
  the glide inside it (no internal boundary).
- Engine total 448 ms is fine; the **distribution** is wrong (E 89 ms too long
  for [ə]; l 50 ms short; diphthong split 148+83 with a stress cliff between).

### 1f. Greeting intonation
- Neutral citation declarative: nuclear **H\* on the stressed rhyme, peak
  mid-rhyme, then L-L\% fall completing inside the stressed syllable** (ToBI
  consensus). Calling "hello!" often rise / rise-fall (chanted contour —
  Gibbon 2017).
- Either way: the rise culminates **inside /loʊ/** and any fall completes
  **inside /loʊ/**. There is no pitch event on the /l/–/o/ boundary and no
  flat low tail parked on the offglide.

## 2. DIFF — every mismatch vs engine tables/plan (with file:line refs)

- **D1. GOAT diphthong rendered as two static monophthongs.** `o` (stressed,
  148 ms, full target) + `U` (unstressed, 83 ms, centralized) are separate
  steady-state cascade specs joined only by a raised-cosine crossfade
  (`synth.rs:424-456`; stress split in `prosody.rs:403-406`; `plan.txt:38-39`).
  Truth (§1b): one syllable, continuous F1 500→400 fall + F2 900→1100 rise.
  The engine has **no diphthong/glide target anywhere** — `vowel_formants`
  (`vowels.rs:6-79`) returns one point per vowel.
- **D2. Entire nuclear fall dumped on `o`, offglide left flat + creaky.**
  `o`: 155.55→80.09 Hz (full +5 st accent then −7 st floor across one segment);
  `U`: flat 80.09 Hz (`plan.txt:38-39`; `prosody.rs:261-266`) **with creak**
  (`synth.rs:378-380`, utterance-final voiced rule ramps over final 60%).
  Truth (§1f): H\* peak sits mid-diphthong, fall completes within it; a flat
  80 Hz creaky offglide is not a GOAT offglide.
- **D3. /h/ is a fixed-band noise burst, not a voiceless [ə~ɛ].**
  Voiceless-fricative path → raw white `frication_noise` (`synth.rs:361-362`)
  through static shaping `[(1400,400,0.4),(2600,600,0.25)]` (`parallel.rs:100`).
  Truth (§1c): /h/ carries the **following vowel's formants** (≈576/1624 here)
  with weak ~1000 Hz turbulence. Engine's 1400/2600 peaks match neither the
  vowel nor the 1000 Hz /h/ locus; there is no formant transition into `E`.
- **D4. /h/ gain floored to −12 dB.** Glottal + voiceless fricative → base −18 dB
  (`synth.rs:199-208`), declination −0 dB at index 0, floor −12 dB
  (`synth.rs:223-228`). So `h −12.0 | E −4.5 | l −9.0 | o −3.0 | U −7.5 dB`.
  Truth: /h/ is weak but only a few dB below the vowel, and a −9 dB /l/ hole
  between vowels is unnatural for a sonorant sequence. (0.0.0.18.4 already
  noted the file peak sits at the o→U glide junction — a D1 symptom.)
- **D5. /l/ has no lateral formant structure at all.** Lateral approximants fall
  through to neutral `default_pairs` (500/1500/2500/…) (`synth.rs:28-41,163-172`);
  locus equations apply only to vowels (`vowels.rs:81-88`; `synth.rs:58-64`).
  Truth (§1d): clear-[l] needs ≈ F1 300 / F2 1300–1600 / F3 ~2700–3000. F2 1500
  is an accidental near-miss; F1 500 (= vowel-like, vs ~300) and F3 2500
  (vs ~2900) are wrong, and duration 50 ms is ~15–30 ms short (§1e).
- **D6. First vowel too full, too long: [ɛ] instead of [ə].**
  Unstressed `E` → 30% centralization only: (600,1720)→**(576,1624)** plus
  alveolar-locus pull F2→**1587** (`vowels.rs:107-113`; `vowels.rs:90-99`;
  `synth.rs:58-64`). Truth: reduced [ə] ≈ (500,1500). Residual error ≈
  +76 Hz F1 / +90–125 Hz F2 — still audibly [ɛ]-like. Duration 89 ms vs
  natural ~50–70 ms for a reduced vowel (§1e); F3 2670 Hz (≈ +150–190 vs
  P&B /ɛ/ ≈ 2480–2520, from the `2500−20·hi+250` front rule `vowels.rs:63-77`).
- **D7. F0 rise happens on the wrong segment.** Rise 133→156 Hz is spread across
  unstressed /l/ (`plan.txt:37`, tail term `prosody.rs:267-275` anticipating the
  nucleus), peaking exactly at `o` onset, then a monotonic 75 Hz cliff.
  Truth (§1f): rise culminates **mid-stressed-rhyme**, not at its left edge;
  the accent peak should sit ~60–70% through /loʊ/, with decline after.
- **D8 (minor). Monophthong target offsets vs P&B men:** `o` (480,950,2300):
  F1/F2 acceptable for [o], F3 ≈ −110 vs /ɔ/ 2410; `U`→(436,1120,2320) vs
  /ʊ/ (440,1020,2240): F2 ≈ +100. Errors are second-order **if** D1 were fixed
  (they would become glide endpoints, not steady states).

## 3. Verdict

Single most wrong thing: **the GOAT diphthong /oʊ/ is split into two static
monophthong segments with the entire nuclear pitch fall (155→80 Hz) plus
utterance-final creak straddling the split** (D1+D2) — nature produces one
continuously gliding syllable carrying peak and fall together. Everything else
(/h/ noise-burst shaping at −12 dB, default-formant /l/, [ɛ]-for-[ə]) degrades
quality; D1+D2 destroys the word's identity as "hello".
