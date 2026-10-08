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
