# Production Setup for Vercel

## Quick Answer: What You Need

### Minimum Requirements (Simple Setup)
- ✅ Vercel account
- ✅ OpenAI API key
- ✅ AssemblyAI API key
- ❌ Redis NOT required for basic setup

### For Production, Choose Your Storage:

## Option 1: Return Results to Zapier (Simplest)
```javascript
// In Zapier, receive the results directly
// No storage needed - Zapier handles it
```

**Vercel Endpoint**: `/api/webhook/process-simple`
- Processes video
- Returns JSON with results
- Zapier saves to Google Drive/Email/Slack

## Option 2: Email Results (Recommended)
```python
# Add to your webhook handler
import resend  # or sendgrid

resend.api_key = os.environ['RESEND_API_KEY']
resend.send({
    "to": metadata['host_email'],
    "subject": f"Analysis: {metadata['topic']}",
    "html": markdown_report
})
```

## Option 3: Cloud Storage

### Cloudflare R2 (S3-compatible, cheap)
```python
import boto3

s3 = boto3.client('s3',
    endpoint_url='https://YOUR_ACCOUNT.r2.cloudflarestorage.com',
    aws_access_key_id=os.environ['R2_ACCESS_KEY'],
    aws_secret_access_key=os.environ['R2_SECRET_KEY']
)

# Save report
s3.put_object(
    Bucket='reports',
    Key=f'{meeting_id}/report.md',
    Body=markdown_report
)
```

### Supabase (Free tier available)
```python
from supabase import create_client

supabase = create_client(
    os.environ['SUPABASE_URL'],
    os.environ['SUPABASE_KEY']
)

# Save to database
supabase.table('reports').insert({
    'meeting_id': meeting_id,
    'score': overall_score,
    'report': markdown_report,
    'summary': summary
}).execute()
```

## Deployment Steps

### 1. Update vercel.json (remove Redis)
```json
{
  "functions": {
    "api/webhook/process-simple.py": {
      "maxDuration": 300
    }
  },
  "env": {
    "OPENAI_API_KEY": "@openai-api-key",
    "ASSEMBLYAI_API_KEY": "@assemblyai-api-key"
  }
}
```

### 2. Deploy to Vercel
```bash
vercel --prod
```

### 3. Set Environment Variables
In Vercel Dashboard:
- `OPENAI_API_KEY`
- `ASSEMBLYAI_API_KEY`
- (Optional) `RESEND_API_KEY` for email

### 4. Update Zapier Webhook
Point to: `https://your-app.vercel.app/api/webhook/process-simple`

## Handling Long Videos (> 5 minutes)

### Option A: Increase Vercel Timeout
- Pro plan: Up to 300 seconds (5 minutes)
- Enterprise: Up to 900 seconds (15 minutes)

### Option B: Use Vercel Cron Jobs
```javascript
// api/cron/process-queue.js
export default async function handler(req, res) {
  // Process pending videos
}
```

In vercel.json:
```json
{
  "crons": [{
    "path": "/api/cron/process-queue",
    "schedule": "*/5 * * * *"  // Every 5 minutes
  }]
}
```

### Option C: Split Processing
1. Webhook starts transcription
2. Return task ID immediately
3. Zapier polls for status
4. Return results when ready

## Recommended Production Setup

For most use cases:

1. **Use `/api/webhook/process-simple`** (no Redis)
2. **Email results** to host (Resend/SendGrid)
3. **Return summary to Zapier** for further actions
4. **Set 300s timeout** in vercel.json

```python
# Minimal production webhook
def handler(request):
    # Process video
    result = process_video(video_url)
    
    # Email full report
    send_email(host_email, result['report'])
    
    # Return summary to Zapier
    return {
        'score': result['score'],
        'summary': result['summary'],
        'email_sent': True
    }
```

## Cost Optimization

- **AssemblyAI**: ~$0.65 per hour of audio
- **OpenAI GPT-4**: ~$0.30 per analysis
- **Vercel**: Free tier includes 100GB bandwidth
- **Storage**: 
  - R2: $0.015/GB/month
  - Supabase: 1GB free
  - Email: Resend 100/day free

## No Redis Required! 

The simplest approach:
1. Receive webhook from Zapier
2. Process video (2-5 minutes)
3. Return results directly to Zapier
4. Let Zapier handle storage/distribution

This works for 90% of use cases!