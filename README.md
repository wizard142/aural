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

Generated playlists use downloaded songs only. They live in memory and disappear when the app closes, including an abnormal exit. **Edit** can rename/recolor a temporary mix. **Save mix** keeps it permanently. Saving does not change the chosen order. For large libraries, up to 250 metadata profiles are shortlisted by relevance; the AI never invents unavailable track IDs or adds duplicate IDs.

New downloads save an additional hidden `.song.json` profile alongside the download metadata, including available artist, album, release year, duration, tags, description, reported genres, source and license. Existing downloads get profiles lazily when used by AI. Missing facts remain unknown. Keyword genre hints and optional AI genre/mood/energy estimates are marked as estimates, with their evidence kept separate. The app does not analyze audio or claim perfect genre recognition. **Song details** in the song menu lets you inspect this provenance without cluttering the library.

The logo follows the selected palette in the sidebar, window/taskbar and installed shortcuts. Desktop icon caches may refresh a little later than the app. Windows installer artwork remains the default logo; your installed app icon changes with your palette.

## Your collection lives here

| System | Default data folder |
| --- | --- |
| Linux | `~/.local/share/aural`, or `$XDG_DATA_HOME/aural` |
| Windows | `%LOCALAPPDATA%\Aural` |

`AURAL_DATA` overrides the location. Playlists, favorites, settings, listening history and browser profiles persist there. The local library works offline; discovery, downloads and remote artwork need internet access.

Stats start when Aural records local playback. They don't import your previous YouTube history or count listening inside the remote website. A play counts after 30 seconds, or half the track's duration if shorter. Pauses and seek jumps do not pad your listening time.

## A few honest limits

The embedded browser uses Qt WebEngine. Its optional filter blocks known ad/tracker requests; it does **not** promise an ad-free YouTube Music experience. Some site items do not expose a draggable song link. Downloader support depends on YouTube changes, so keep yt-dlp current or rebuild the Windows package. Download resume and automatic app updates are not implemented.

Aural is audio-only. Existing video files from earlier local versions stay on disk but are hidden. It has no paid features, donation integration, or Aural advertising.

Download only content you own or are authorized to download, and respect the source service's terms and applicable rights. Aural does not grant rights to music.

## Development and checks

```sh
python -m pip install -r requirements-build.txt
python -m unittest discover -s tests -v
python desktop.py --self-test --self-test-result smoke-result.json
```

The desktop smoke test uses an isolated temporary library and a generated silent audio fixture. It checks real playback, like/unlike persistence, playlists, drag-and-drop, themes, layouts, duplicate rejection, listening history, deletion, and media-tool conversion. It leaves your music alone. A failed check exits nonzero and writes a JSON report.

Previous stable Linux and Windows builds passed; the AI update is being verified in CI. See [verification details](docs/TESTING.md). GitHub Actions runs Linux and Windows checks and exercises the **packaged** Windows executable as well as the source app. A passing test run is evidence for the covered behavior, not a claim that every YouTube page or Windows hardware setup works.

## Credits

Built with [Qt for Python](https://doc.qt.io/qtforpython-6/), [yt-dlp](https://github.com/yt-dlp/yt-dlp), [FFmpeg](https://ffmpeg.org/), and [Lucide](https://lucide.dev/) icons. Lucide's license is bundled in `static/icons/LICENSE`. The filled heart is derived from the bundled Lucide heart.

Aural's own code is [MIT licensed](LICENSE). Third-party dependencies keep their own licenses. Windows builds include notices; FFmpeg binary distribution also requires matching source arrangements described in the build notes.
