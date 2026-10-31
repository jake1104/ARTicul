# CASES survey: what real implementations do about naturalness (0.0.0.19.1)

Scope: read-only research. ARTicul engine in 1-2 files (see section 1).
Survey of 6 systems below; each notes the ONE mechanism most relevant to
ARTicul's gaps. Ends with a steal list of max 6 concrete mechanisms.

## 1. ARTicul engine type (brief)

ARTicul is a Klatt-style cascade/parallel formant synthesizer with an
LF glottal pulse source. Per-segment branch selection lives in
`crates/articul-cli/src/synth.rs` (`spec_for`: fricatives take the
parallel branch via `fricative_shaping`, vowels/sonorants take the
cascade branch with table F1-F3 plus fixed upper F4-F6), rendered
segment-by-segment in `render_units` with a 50 ms vowel-vowel
`filter_glide` (per-sample retuned resonators, warmup state carry) and
an 8 ms crossfade elsewhere, plus `NotchFilter` nasal zero, lip
radiation `R(z)=1-0.97z^-1`, per-segment scalar gain, and
Fujisaki-style phrase/accent F0 command-response with per-segment glide
interpolation. DSP primitives (resonators, LF source with
jitter/shimmer/breath/creak, noise, radiation) live in
`crates/articul-dsp/src` (`source.rs`, `cascade.rs`, `parallel.rs`).

What it still lacks (from todo.md + CHANGELOG Unreleased, cascades
0.0.0.11-0.0.0.18): time-varying source parameters (open quotient and
spectral tilt are fixed), no band-split mixed excitation (one global
aspiration scalar), fricatives are raw shaped noise with no transient
or aspiration-phase structure, and formant targets are static per
segment with only pairwise glides.

## 2. System notes

### eSpeak NG — intelligible but robotic
Hybrid engine: additive harmonic synthesis for vowels/sonorants
(`wavegen.c`: sine-stack voiced frames) plus recorded/sampled
unvoiced consonants mixed in, with an optional Klatt cascade/parallel
backend (`klatt.c`: port of Klatt 1980/1990 with flutter, tilt,
breathiness, sampled glottal source options). Phoneme durations come
from `setlengths.c` rules; stress promotion in `phonemelist.c`.
Relevant mechanism: the hybrid split itself. Pure rule synthesis
carries vowels fine (harmonic stack = smooth F0), but consonant
bursts/transients are sampled, not synthesized — that is where eSpeak
gets intelligibility without solving transient synthesis. Its issue
tracker even notes the Klatt path sounds harsh/static-y vs Eloquence,
i.e. filtered-noise consonants alone read as static.
Sources:
- https://github.com/espeak-ng/espeak-ng (formant synthesis, small size, clear but not natural; Klatt + MBROLA backends)
- https://en.wikipedia.org/wiki/ESpeak (additive voiced + recorded unvoiced; voiced fricatives mix both)
- https://github.com/espeak-ng/espeak-ng/blob/master/src/libespeak-ng/klatt.c (flutter per Klatt & Klatt 1990; tilt low-pass; breathiness in open phase; sampled source option)
- https://github.com/espeak-ng/espeak-ng/issues/2173 (Klatt path harsh/static complaint; proposal for Klatt-based consonants)

### Gnuspeech — tube model + rhythm/intonation
True articulatory waveguide (tube resonance / transmission-line) model
of the vocal tract (TRM in Tube.framework) instead of independent
per-formant resonators, driven by posture tracks; separate published
models of English rhythm and intonation with an editor (Monet) for the
parameter tracks and contours. Relevant mechanism: coarticulation and
transitions fall out of continuous tube-shape interpolation rather
than per-segment formant targets plus pairwise glides, and prosody is
a separately editable track layer, not baked into segment gains.
ARTicul's closest analogue today is `locus_pull_toward` + glide zones;
the tube shows the next step is continuous posture tracks.
Sources:
- https://www.gnu.org/software/gnuspeech (event-based articulatory synthesis; rhythm/intonation models; TRAcT tube model)
- https://savannah.gnu.org/projects/gnuspeech (tube resonance/waveguide as filter; dictionary + letter-to-sound + rhythm/intonation front end)
- https://cspages.ucalgary.ca/~hilld/papers/tract-manual.pdf (TRM manual: waveguide maps onto articulatory/acoustic behaviour directly)
- https://cspages.ucalgary.ca/~hilld/papers/synthesizer/menu.html (Synthesizer manual: resonant system, throat transmission, noise and glottal sources incl. breathy voice)

### Flite — data beats rules above a size threshold
Small fast runtime for deploying Festival/FestVox voices: diphone and
unit-selection/clustergen voices with LPC/MLSA residual playback,
target-plus-join cost (spectral mismatch at joins), prosody from
predicted F0/duration models. Relevant mechanism: the lesson is
negative — even at 2 MB diphone + 600 KB lexicon, concatenative data
beats any rule set for naturalness, and join cost (spectral continuity
at boundaries) is the metric rules engines lack. ARTicul's zone-relative
click gate (0.0.0.15.4) is a join-cost embryo; without recorded units
the steal is the discipline: penalize spectral discontinuity at joins
explicitly and keep prosody prediction separate from waveform assembly.
Sources:
- https://www.cs.cmu.edu/~awb/papers/ISCA01/flite.pdf (Flite paper: small fast runtime; unit databases; diphone/LPC design)
- http://cmuflite.org/doc/flite.pdf (Flite 2.0 manual: language models, lexicon, unit database + voice definition)
- https://github.com/festvox/flite (4 bundled voices: 3 clustergen + kal diphone; footprint table)
- https://www.cambridge.org/core/books/texttospeech-synthesis/unitselection-synthesis/498C8A5B17A9E82F2FF6A4955D79A4E (unit selection: target cost + join cost; prosody beyond F0/timing; signal-processing distortion)

### DECtalk / Klattalk — parameter richness
KLSYN88 cascade-parallel plant (Klatt & Klatt 1990) with ~19 exposed
controls driven every 5 ms from rules: AV/AF/AH/AVS source amplitudes,
F0, F1-F6 + nasal pole/zero, parallel-branch amplitudes A1-A6/AN/AB,
plus the Klattalk voicing upgrade — open quotient (OQ), spectral tilt
(TL), and breathiness (AH/ATurb) varying with F0/amplitude/stress.
Relevant mechanism: naturalness came from modulating the SOURCE
(OQ/TL/breathiness) continuously, not just formant tracks. ARTicul has
fixed OQ=0.6/asymmetry=0.7/tilt-none; DECtalk varies them per segment
and accent. Oxford's parameter-generation page confirms the 5 ms update
discipline: every frame re-queries rules for all source + filter
parameters with defaults filling the rest.
Sources:
- https://languagelog.ldc.upenn.edu/myl/ldc/Turkeltaub/KlattChapter3Description.pdf (KLSYN88 design; control-parameter effects; KLSYN88 vs 1980 changes)
- https://sail.usc.edu/~lgoldste/Ling582/Week%2013/Klatt1987.pdf (Klattalk voicing: OQ, spectral tilt, breathiness family of waveshapes)
- https://www.phon.ox.ac.uk/synth (parameter file every 5 ms; AV/AF/AH/AVS/F0/F1-F5/FNZ/B1-B3/parallel amplitudes)
- https://en.wikipedia.org/wiki/DECtalk (DECtalk 1983, Klatt MITalk source-filter; per-voice editable parameters)

### Praat KlattGrid — reference implementation to copy
Superset of Klatt & Klatt (1990 figure 14): 6 oral + nasal +
tracheal + frication formants with anti-formants, driven by TIME-based
tiers (not frames) with interpolation, fully inspectable inside Praat;
synthesis switches expose phonation (voicing/flutter/double
pulsing/collision phase/spectral tilt/flow function), vocal
tract, frication bypass, aspiration, and breathiness separately.
Relevant mechanism: the tier architecture itself — every parameter is
a time-stamped target track with interpolation, so source-filter
interaction (e.g. aspiration gated by open phase, double-pulsing
creak) is declarative data, not code branches. ARTicul's
`render_units` match on Cf0Mode/creak/frication is the hard-coded
shadow of this; KlattGrid shows how to make it data.
Sources:
- https://praat.org/manual/KlattGrid.html (KlattGrid object: tiers, superset of Klatt & Klatt 1990)
- https://www.fon.hum.uva.nl/david/ba_shs/2009/is2009_klattgrid.pdf (Weenink 2009: time-based not frame-based; free sampling rates; Praat integration)
- https://praat.org/manual/KlattGrid__To_Sound__phonation____.html (phonation switches: flutter, double pulsing, collision, tilt, flow, aspiration, breathiness)
- https://praat.org/manual/KlattGrid__To_Sound__special____.html (cascade/parallel model switch, formant ranges, frication bypass)

### WORLD — the modern bar
Analysis/synthesis vocoder decomposing speech into F0 (DIO/Harvest),
spectral envelope (CheapTrick), and APERIODICITY (D4C/PLATINUM), then
resynthesizing with mixed excitation; band aperiodicity in ~5 bands
suffices for natural speech. Relevant mechanism: per-BAND
voiced/unvoiced ratio. ARTicul's 0.0.0.18 verdict (raw-noise
fricatives + masking normalize = static) is exactly what band
aperiodicity fixes: breathiness lives mostly in high bands during
vowels, low bands stay periodic. One global `aspiration_noise`
scalar cannot express that; per-band mixing gains can.
Sources:
- https://github.com/mmorise/World (WORLD repo: F0 + aperiodicity + envelope; modified-BSD; no patents)
- https://www.jstage.jst.go.jp/article/transinf/E99.D/7/E99.D_2015EDP7457/_pdf/-char/en (DIO + CheapTrick + PLATINUM pipeline; F0/envelope manipulation)
- https://apsipa.org/proceedings/2019/pdfs/109.pdf (5-band aperiodicity suffices for natural synthesis)
- https://arxiv.org/pdf/2208.07282v1 (differentiable WORLD: F0 + envelope + aperiodicity-ratio features to phase-coherent waveform)

## 3. Steal list (max 6, mapped to ARTicul files)

1. Parallel-branch amplitude tracks (A1-A6/AN + AF/AH/AV per 5 ms frame) for voiced fricatives and sonorants — `crates/articul-dsp/src/parallel.rs`, `crates/articul-cli/src/synth.rs::spec_for`.
2. Time-varying source trio OQ + spectral tilt + breathiness keyed to stress/accent (re-admit slow flutter under the null-gate lesson) — `crates/articul-dsp/src/source.rs` (`GlottalSource`).
3. KlattGrid-style time-based parameter tiers with per-section switches (phonation/frication-bypass/aspiration/breathiness) replacing hard-coded render branches — `crates/articul-cli/src/synth.rs::render_units`.
4. Sampled transient grafts for stop bursts/affricates alongside the ruled vowel path (eSpeak hybrid lesson) — `crates/articul-cli/src/synth.rs` burst envelope path + new transient asset slot.
5. Band-split mixed excitation (WORLD-style per-band voiced/noise ratios, high-band breathiness in vowels) replacing the global aspiration scalar — `crates/articul-dsp/src/source.rs::effective_aspiration`, `crates/articul-dsp/src/parallel.rs`.
6. Explicit spectral-discontinuity join cost at unit boundaries as a regression gate (Flite lesson), extending the 0.0.0.15.4 zone-relative click gate — new test beside `crates/articul-cli/tests/click.rs`.

Single best reference implementation to copy: Praat KlattGrid (Weenink 2009) — open, time-based tier superset of Klatt & Klatt 1990 covering every mechanism above except sampled transients and band aperiodicity, and it maps 1:1 onto ARTicul's cascade/parallel + LF-source architecture.
