# Zapier Integration Setup

## Quick Setup Guide

### 1. Create Zapier Workflow

1. **Trigger**: Zoom → New Cloud Recording
2. **Action**: Webhooks by Zapier → POST

### 2. Configure Webhook

**URL**: `https://your-app.vercel.app/api/webhook/process`

**Payload Type**: JSON

**Data Fields**:
```json
{
  "video_url": "{{1. Video Files Download URL}}",
  "Topic": "{{1. Topic}}",
  "Host Email": "{{1. Host Email}}",
  "Duration": "{{1. Duration}}",
  "Meeting ID": "{{1. Meeting ID}}"
}
```

**Headers**:
- Key: `Content-Type`
- Value: `application/json`

### 3. Test Locally

```bash
# Terminal 1: Start server
python process_zoom_video.py

# Terminal 2: Create tunnel
ngrok http 3000

# Use ngrok URL in Zapier
https://[your-id].ngrok.app/webhook
```

### 4. Deploy to Production

```bash
# Deploy to Vercel
vercel --prod

# Set environment variables in Vercel dashboard:
# - OPENAI_API_KEY
# - ASSEMBLYAI_API_KEY
# - UPSTASH_REDIS_REST_URL
# - UPSTASH_REDIS_REST_TOKEN
```

## Testing

Test with the provided script:
```bash
python test-zoom-webhook.py --url https://your-app.vercel.app --wait
```

## Processing Flow

1. Zapier sends Zoom recording URL to webhook
2. AssemblyAI transcribes video (2-5 minutes)
3. System chunks into 30-minute blocks
4. OpenAI analyzes each block
5. Reports saved to `debug_output/`
6. Optional: Send results back to Zapier callback

## Troubleshooting

- **No video URL found**: Check field mapping in Zapier
- **Timeout errors**: Videos > 5 minutes need async processing
- **API errors**: Verify API keys in environment variables