# Recording Transcription & Analysis System

A comprehensive system for transcribing and analyzing video recordings (especially Zoom meetings) using AssemblyAI for transcription and OpenAI for intelligent analysis. Features Zapier webhook integration for automatic processing.

## 🚀 Features

- **Automatic Transcription**: Uses AssemblyAI to transcribe video/audio with speaker detection
- **Intelligent Chunking**: Splits long recordings into 30-minute blocks for analysis
- **AI-Powered Analysis**: Evaluates content based on 10 criteria using OpenAI GPT-4
- **Comprehensive Reporting**: Generates detailed markdown reports with scores and recommendations
- **Zapier Integration**: Webhook endpoint for automatic processing of Zoom recordings
- **Multiple Input Formats**: Supports MP4, MP3, M4A, WAV, FLAC, AAC, VTT, and TXT

## Installation

### Prerequisites

- Python 3.9+
- FFmpeg (for video processing): `brew install ffmpeg` (macOS)

### Setup

1. **Clone the repository**:
   ```bash
   git clone [your-repo-url]
   cd RecordingTranscription
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys:
   # OPENAI_API_KEY=sk-...
   # ASSEMBLYAI_API_KEY=...
   ```

## Usage

### Quick Start - Process Zoom Recording

```bash
# Process a Zoom video directly
python process_zoom_video.py

# Or with a specific URL
python process_zoom_video.py "https://zoom.us/rec/download/..."
```

### CLI Commands

```bash
# Basic analysis with text file
python -m src.app.main --input transcription.txt

# Analyze audio/video file (automatically transcribed)
python -m src.app.main --input lecture.mp4
python -m src.app.main --input audio.wav

# Use VTT subtitles file
python -m src.app.main --input subtitles.vtt

# With custom output file
python -m src.app.main --input lecture.mp4 --output my_analysis.md

# JSON output format
python -m src.app.main --input audio.wav --format json

# Dry run (test without API calls)
python -m src.app.main --input lecture.mp4 --dry-run
```

### Supported Input Formats

- **Audio/Video**: `.mp4`, `.wav`, `.mp3`, `.m4a`, `.flac`, `.aac` (transcribed via AssemblyAI)
- **Text**: `.vtt` (subtitles with timestamps), `.txt` (plain text)

**Note**: VTT files and audio/video files are preferred as they provide accurate timestamps for proper 30-minute chunking.

## 🔗 Zapier Integration

### Setting up with Zapier

1. **Create a Zap**:
   - Trigger: Zoom → New Cloud Recording
   - Action: Webhooks by Zapier → POST

2. **Configure Webhook**:
   ```json
   {
     "video_url": "{{Video Files Download URL}}",
     "Topic": "{{Topic}}",
     "Host Email": "{{Host Email}}",
     "Duration": "{{Duration}}"
   }
   ```

3. **Deploy to Vercel**:
   ```bash
   vercel --prod
   ```

### Local Testing

1. Start local server:
   ```bash
   python test-webhook.py
   ```

2. Create ngrok tunnel:
   ```bash
   ngrok http 3000
   ```

3. Use ngrok URL in Zapier

## 📊 Output

The system generates three files in `debug_output/`:

1. **last_transcription.vtt** - Full transcription with timestamps
2. **last_report.md** - Detailed analysis report with scores
3. **last_summary.md** - Executive summary (Kurzfassung)

### Analysis Criteria

Each recording is evaluated on 10 criteria (scored 1-5):

1. Strukturierung & Aufbau (Structure)
2. Interaktionsniveau (Interaction Level)
3. Praktische Anwendbarkeit (Practical Applicability)
4. Mediennutzung (Media Usage)
5. Sprachliche Klarheit (Linguistic Clarity)
6. Zielgruppenorientierung (Target Audience)
7. Zeitmanagement (Time Management)
8. Engagement-Förderung (Engagement)
9. Fachliche Tiefe (Technical Depth)
10. Nachbereitung (Follow-up Materials)

## 🚀 Deployment

Deploy to Vercel for production use:

```bash
vercel --prod
```

Required environment variables:
- `OPENAI_API_KEY`
- `ASSEMBLYAI_API_KEY`
- `UPSTASH_REDIS_REST_URL` (for queue management)
- `UPSTASH_REDIS_REST_TOKEN`
- `WEBHOOK_SECRET`

## 📁 Project Structure

```
.
├── src/app/                  # Core application logic
│   ├── transcription.py      # Audio/video transcription
│   ├── chunker.py            # Text chunking
│   ├── analyzer.py           # OpenAI analysis
│   ├── aggregator.py         # Score aggregation
│   └── formatter.py          # Report formatting
├── api/                      # Vercel API endpoints
│   └── webhook/              # Webhook handlers
├── debug_output/             # Generated reports
└── process_zoom_video.py     # Main processing script
```
