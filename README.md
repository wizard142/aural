<div align="center">
  <img src="static/aural.svg" width="100" alt="Aural logo">
  <h1>Aural</h1>
  <p>A little less tab juggling. A lot more music.</p>
</div>

[![Desktop checks](https://github.com/wizard142/aural/actions/workflows/ci.yml/badge.svg)](https://github.com/wizard142/aural/actions/workflows/ci.yml)

Aural is an audio-first desktop library for Linux and Windows. Browse YouTube Music inside the app, bring permitted audio into your local collection, and organize it without turning your screen into a dashboard of dashboards.

## What's inside

- **AI mixes with your own API key:** ask for a genre, a mood, a personal scenario, or a transition from one style to another. Mixes are temporary until you save them.
- **A local library:** search, favorites, playlists and offline playback.
- **YouTube Music in the window:** search, copy a song link, add music, or drag an available song link into the library.
- **Playlists with personality:** names and colors, drag-to-add, and colored outlines on songs. Multiple playlists? Multiple colors.
- **A small listening dashboard:** your most-played songs, listening time, favorite artist by listening time, and a weekly activity chart.
- **A player that stays put:** shuffle, repeat, seek, previous/next, and ten-second rewind/forward.
- **Six palettes, three layouts:** album grid, song list, or compact. The discovery pane follows your palette too.
- **One copy is enough:** duplicate downloads are checked by YouTube video ID, including downloads already running.

The heart fills and lights up when you favorite a song. Click it again to unlike. Tiny button, important job.

## Linux — including CachyOS

On CachyOS / Arch:

```sh
sudo pacman -S python yt-dlp ffmpeg
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python install.py
```

Search **Aural** in your application menu. To launch from a terminal:

```sh
.venv/bin/python desktop.py
```

Other Linux distributions can install Python, yt-dlp and FFmpeg from their package manager, then use the same virtual-environment steps. Keep the source folder in place if you use its launcher.

## Windows

For a source installation, install Python 3.12 x64, extract or clone this repo into a permanent directory, and double-click **Setup-Windows.cmd**. Setup installs the Python dependencies, prepares verified media tools, and adds a Start-menu shortcut. Then search **Aural** in Start.

The portable Windows build includes Python, Qt, yt-dlp, FFmpeg/ffprobe and Deno; its users do not need to install those separately. Windows CI builds and tests that package. Build and installer instructions are in [WINDOWS.md](packaging/windows/WINDOWS.md). Test results are in [GitHub Actions](https://github.com/wizard142/aural/actions).

## Quick tour

1. Open **YouTube Music** and find a song.
2. Use **Add music**, or drag a song link into the library. Audio downloads as MP3.
3. Create a playlist with **＋**, give it a name and color, and drag local songs onto it.
4. Like a song with the heart; unlike with the same button.
5. Open **Settings** when your library needs a different palette or layout.

Use **•••** on a song to manage playlist membership or delete its local files. Deleting a playlist keeps the songs. Deleting a song removes it from every playlist. The app asks before deletion.

## AI mixes

Open **Settings → AI**, select a provider, enter a model ID available to your account, and add its API key. Presets support OpenAI, Claude/Anthropic, Google Gemini, DeepSeek, Groq, Mistral, xAI, and OpenRouter; a custom OpenAI-compatible HTTPS endpoint is also supported.

Keys are kept in memory unless you choose **Remember key securely**. Saved keys use Windows Credential Manager, macOS Keychain where available, or a supported Linux Secret Service/KWallet backend. If secure storage is unavailable or locked, the key stays session-only and the app tells you. Aural does not write keys into its settings JSON, song metadata or playlists. **Forget key** removes the app's stored key; provider environment variables are managed separately.

Select **AI mix** and describe what you want: “calm jazz, gradually switch to metal, about 40 minutes” or “upbeat pop for a rainy commute.” The prompt and selected song metadata go to your configured provider when you confirm. API billing and provider data-retention policies apply. Audio files, file paths, listening history and API keys are not included in the prompt.

Generated playlists use downloaded songs only. They live in memory and disappear when the app closes, including an abnormal exit. **Edit** can rename/recolor a temporary mix. **Save mix** keeps it permanently. Saving does not change the chosen order. For large libraries, up to 250 metadata profiles are shortlisted by relevance within a bounded metadata budget. Groq uses a smaller budget, compact descriptions and mixes of up to 20 songs to suit limited accounts. A size rejection gets one retry with a smaller shortlist; the AI never invents unavailable track IDs or adds duplicate IDs.

New downloads save an additional hidden `.song.json` profile alongside the download metadata, including available artist, album, release year, duration, tags, description, reported genres, source and license. Existing downloads get profiles lazily when used by AI. Missing facts remain unknown. Keyword genre hints and optional AI genre/mood/energy estimates are marked as estimates, with their evidence kept separate. Local audio analysis adds evidence rather than guaranteed mood labels. **Song details** in the song menu lets you inspect this provenance without cluttering the library.

The logo follows the selected palette in the sidebar, window/taskbar and installed shortcuts. Desktop icon caches may refresh a little later than the app. Windows installer artwork remains the default logo; your installed app icon changes with your palette.

## Your collection lives here

| System | Default data folder |
| --- | --- |
| Linux | `~/.local/share/aural`, or `$XDG_DATA_HOME/aural` |
| Windows | `%LOCALAPPDATA%\Aural` |

`AURAL_DATA` overrides the location. Playlists, favorites, settings, listening history and browser profiles persist there. The local library works offline; discovery, downloads and remote artwork need internet access.

Stats start when Aural records local playback. They don't import your previous YouTube history or count listening inside the remote website. A play counts after 30 seconds, or half the track's duration if shorter. Pauses and seek jumps do not pad your listening time.

## Give your songs better profiles

**Settings → Song profiles → Analyze library** scans existing downloads; no redownload is needed. New downloads are analyzed automatically unless you turn that off. First analysis downloads approximately 20 MB of hash-verified MTG/Essentia ONNX models. FFmpeg samples three sections locally; a Discogs Effnet model estimates styles and four mood classifiers score sad, happy, relaxed and aggressive. Rough tempo and RMS energy measurements are also recorded, with their limitations. Playback stays available while one background worker processes the library. Results are cached in `.song.json`; scans skip current profiles unless you choose to analyze a song again.

**Song menu → Song details → Your labels** lets you correct genres, moods and energy, add a personal note, or exclude particular moods. Clear corrections to return to automatic estimates. Your labels have priority in AI prompts and relevance shortlisting, survive source metadata refreshes, and are preserved if you edit them while analysis is running. Model scores are not accuracy percentages.

For **fingerprint identification**, register an application at [AcoustID](https://acoustid.org/new-application) and put its application/client key in Settings → Song profiles. This is separate from your AI-provider key and from AcoustID's user submission key. Choose Identify library or Identify recording, or enable identification of future downloads. Aural sends a Chromaprint fingerprint and duration, never the audio file, then fetches recording metadata from MusicBrainz with rate limiting. Low-scoring or conflicting matches remain unconfirmed; source metadata is not overwritten. Identification does not classify mood. Linux needs `fpcalc` (CachyOS/Arch: `chromaprint`; Debian/Ubuntu: `libchromaprint-tools`); the Windows installer bundles it.

AI mixes receive compact audio estimates, identified metadata and your corrections alongside source evidence. Private fingerprints and local paths are excluded. Missing mood tags no longer mean a song cannot fit a mood. Hosted AI calls and lookup services still need their configured keys; audio inference itself runs offline after model installation.

The models are separately licensed **CC BY-NC-SA 4.0** by the Music Technology Group at Universitat Pompeu Fabra. Their upstream URLs, versions and hashes are recorded in `model-assets.json`. Commercial model/service use requires appropriate licensing; the application's own code remains MIT.

## A few honest limits

The embedded browser uses Qt WebEngine. Its optional filter blocks known ad/tracker requests; it does **not** promise an ad-free YouTube Music experience. Some site items do not expose a draggable song link. Downloader support depends on YouTube changes, so keep yt-dlp current or rebuild the Windows package. Download resume and automatic app updates are not implemented.

Aural is audio-only. Existing video files from earlier local versions stay on disk but are hidden. It has no paid features, donation integration, or Aural advertising.

Download only content you own or are authorized to download, and respect the source service's terms and applicable rights. Aural does not grant rights to music.

## Development and checks

```sh
python -m pip install -r requirements-build.txt
python audio_analysis.py
python -m unittest discover -s tests -v
python tests/audio_inference.py
python desktop.py --self-test --self-test-result smoke-result.json
```

The desktop smoke test uses an isolated temporary library, a generated playback fixture, and generated audible music for real local inference and fingerprint checks. It checks real playback, like/unlike persistence, playlists, drag-and-drop, themes, layouts, duplicate rejection, listening history, deletion, and media-tool conversion. It leaves your music alone. A failed check exits nonzero and writes a JSON report.

The AI update passed Linux and Windows CI, including the portable and installed Windows app. See [verification details](docs/TESTING.md). GitHub Actions runs Linux and Windows checks and exercises the **packaged** Windows executable as well as the source app. A passing test run is evidence for the covered behavior, not a claim that every YouTube page or Windows hardware setup works.

## Credits

Built with [Qt for Python](https://doc.qt.io/qtforpython-6/), [yt-dlp](https://github.com/yt-dlp/yt-dlp), [FFmpeg](https://ffmpeg.org/), and [Lucide](https://lucide.dev/) icons. Lucide's license is bundled in `static/icons/LICENSE`. The filled heart is derived from the bundled Lucide heart.

Aural's own code is [MIT licensed](LICENSE). Third-party dependencies keep their own licenses. Windows builds include notices; FFmpeg binary distribution also requires matching source arrangements described in the build notes.
