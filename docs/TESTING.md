# Verified desktop builds

Verification completed on 7 October 2026.

| Environment | Backend/platform tests | Desktop checks | Result |
| --- | --- | --- | --- |
| Local CachyOS/Linux | 17 | 17 | Pass |
| Ubuntu GitHub runner | 17 | 17 | Pass |
| Windows GitHub runner, source | 17 | 17 | Pass |
| Windows x64 portable executable | — | 17 | Pass |
| Windows x64 installed executable | — | 17 | Pass |

The Windows installer also passed installation, Start-menu shortcut targeting, uninstall, and preservation of user data. Each desktop check used a generated silent WAV/MP3 fixture and an isolated temporary library. No real user's collection was used.

Desktop coverage: FFmpeg conversion; real downloader-worker download and audio extraction from a local fixture; request filtering; MP3 playback; favorite on and off with persistence and a filled theme-colored heart; playlist drag-and-drop; playlist outlines; all palettes and layouts; settings drawer; duplicate and video rejection; listening history; deletion cleanup; native URL-drop routing; and packaged WebEngine assets.

- [Successful Windows job: source, package, installer and uninstall](https://github.com/wizard142/aural/actions/runs/37661087735/job/112928488695)
- [Successful Ubuntu verification](https://github.com/wizard142/aural/actions/runs/37662518045)

Windows tested application commit: `da05a8b`. Linux CI commit: `f83daa7`. The change between those commits only adjusted CI dependency setup and platform selection; the application code and assets are identical. The combined run's obsolete Ubuntu job was cancelled after a system package update stalled; the Windows job completed successfully and the replacement Linux verification is green.

Reports for source, portable and installed Windows runs and Linux runs are uploaded in their Actions artifacts. Automated coverage does not prove that every YouTube Music tile exposes a drag link, that every ad is blocked, or that all Windows hardware and older operating-system versions are supported. Windows binaries are unsigned.

## AI update checks (8 October 2026)

Local backend tests now cover nine provider request/response adapters, no key in request prompts/settings files, secure-storage fallback, scoped custom-endpoint credentials, playlist-ID validation, metadata provenance, temporary rename/save/cleanup, and late-generation rejection after the session ends. Desktop tests exercise AI settings, generating a temporary mix, rename, save, metadata estimates, close cleanup, and theme-colored SVG/native icons. Provider generation uses a mocked response in these checks; no live paid-provider call has been made without a supplied key.

The AI update passed [Linux and Windows CI](https://github.com/wizard142/aural/actions/runs/37824274863) at application commit `2d3f416`. All 28 backend/platform tests passed. Linux passed 25 desktop checks; Windows passed 26 checks (including a secure credential-store round trip) in source, portable and installed modes. Installation, theme-aware shortcut targeting, and data-preserving uninstall passed. The installed-app run also verified the Windows settings read/write coordination fix. Live paid-provider generation still requires a user-supplied key and was not exercised by CI; request/response adapters and generation behavior were tested with mocks.

## Audio profiles update (9 October 2026)

Local verification at application commit `7190fc4`: all 42 backend/platform tests and 31 Linux desktop checks pass. Coverage includes personal label validation and clearing, retaining corrections through metadata refresh and background analysis, deleted-song protection, compact AI catalogs with user labels/audio/identity evidence and no fingerprints, confident/ambiguous fingerprint match handling, fingerprint-only lookup requests, bounded download retries, and model checksum rejection. Desktop tests cover profile controls, label saving, identification-key setup/removal, and the native AcoustID registration link without launching a real browser.

Real offline inference is tested on generated audible music using the actual hash-pinned Discogs Effnet ONNX extractor and four mood heads. Real Chromaprint fingerprint generation is also checked. Tests assert valid output shapes and score ranges, not the subjective correctness of moods. A separate comparison against Essentia's reference TensorflowInputMusiCNN implementation found a maximum absolute mel-feature difference of `0.0000706` across a 128-frame seeded test sample. The reference library was used only for validation, not added as an app dependency.

[Ubuntu CI](https://github.com/wizard142/aural/actions/runs/37905211397) passed at `c87b304`. The original Ubuntu job encountered a model-host connection timeout; bounded retries and a fresh runner resolved preparation. The later `7190fc4` change adds regression tests and fixes the desktop registration link; the complete source desktop check was repeated locally.

Fingerprint service responses and paid AI-provider calls are mocked in regression tests. Live AcoustID lookup requires an application/client key and has not been exercised with a user key. Audio inference and fingerprint generation are real and offline. Classification scores are not accuracy guarantees; personal corrections remain authoritative evidence.

[Final Windows verification](https://github.com/wizard142/aural/actions/runs/37905525630) passed at application commit `7190fc4`: all 42 backend/platform tests, real model inference/fingerprinting, and 32 desktop checks in source, portable and installed forms. Installer shortcuts and data-preserving uninstall also passed. The tested v1.2.0 Windows installer bundles the audio models and Chromaprint tool.
