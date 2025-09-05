# Complete Zapier Setup Guide

## Overview
Two-Zap system: One triggers processing, one receives results (~15 minutes later)

## Zap #1: Trigger Video Processing (Already Done ✅)
- **Trigger**: New Zoom Recording
- **Action**: Custom Request to GitHub
  - URL: `https://api.github.com/repos/LennardKlein/dozentenfeedback/dispatches`
  - Headers: Bearer token, etc.
  - Sends video URL to GitHub Actions

## Zap #2: Receive Processing Results (New)

### Step 1: Create the Webhook Catcher
1. Create a new Zap in Zapier
2. **Trigger**: Choose "Webhooks by Zapier"
3. **Event**: "Catch Hook"
4. Click Continue
5. Copy the webhook URL (looks like: `https://hooks.zapier.com/hooks/catch/123456/abcdef/`)

### Step 2: Add Webhook URL to GitHub
1. Go to: https://github.com/LennardKlein/dozentenfeedback/settings/secrets/actions
2. Click "New repository secret"
3. Name: `ZAPIER_WEBHOOK_URL`
4. Value: Paste the webhook URL from Step 1
5. Click "Add secret"

### Step 3: What You'll Receive
When processing completes (~15 minutes), GitHub sends back:
```json
{
  "status": "success",
  "metadata": {
    "topic": "Lecture Title",
    "host_email": "professor@university.edu",
    "duration": "71",
    "meeting_id": "ABC123",
    "score": 4.5
  },
  "score": 4.5,
  "total_blocks": 12,
  "criteria_scores": {
    "Klarheit der Lernziele": 4.8,
    "Struktur und Aufbau": 4.2,
    // ... all 10 criteria
  },
  "summary": "Zusammenfassung des Vortrags...",
  "markdown_report": "Full markdown formatted report",
  "pdf_base64": "base64_encoded_pdf_content",
  "strengths": ["Clear examples", "Good structure", ...],
  "improvements": ["More interaction", ...],
  "recommendations": ["Add quiz", ...]
}
```

### Step 4: Process the Results in Zapier

Add actions to your Zap #2:

#### Option A: Save PDF to Google Drive
1. **Action**: Google Drive - Create File from Text
2. Map fields:
   - Folder: Choose your folder
   - File Name: `{{metadata__topic}}_{{metadata__meeting_id}}.pdf`
   - File Content: `{{pdf_base64}}`
   - Convert to: PDF (from base64)

#### Option B: Send to Slack
1. **Action**: Slack - Send Channel Message
2. Message text:
```
📚 *Video Analysis Complete*
Topic: {{metadata__topic}}
Score: {{score}}/5.0 ⭐
Summary: {{summary}}
```

#### Option C: Create Spreadsheet Row
1. **Action**: Google Sheets - Create Spreadsheet Row
2. Map all the scores and metadata to columns

#### Option D: Send Email
1. **Action**: Gmail - Send Email
2. Include the summary and attach the PDF

## Timeline
1. Zoom recording ready → Zap #1 triggers
2. GitHub Actions processes (5-15 minutes depending on video length)
3. Results sent to Zap #2
4. Zap #2 saves to Drive/Slack/Email/etc.

## Testing
1. Set up both Zaps
2. Test Zap #1 (already working)
3. In Zap #2, after adding the webhook URL to GitHub, click "Test trigger"
4. Run Zap #1 to process a video
5. Wait for results to appear in Zap #2

## No Delays Needed!
- GitHub Actions will call your webhook when done
- Processing takes ~15 minutes for a 4-hour video
- You get all data: PDF, Markdown, JSON, scores