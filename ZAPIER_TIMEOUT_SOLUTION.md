# Solution for Zapier Timeouts with Long Videos

## The Problem
- Zapier webhooks timeout after 30 seconds
- Vercel Functions timeout after 5 minutes (300 seconds)
- Long videos (1-4 hours) can take 10-20 minutes to process

## The Simple Solution: Use Zapier's Built-in Features

### Option 1: Use Zapier Storage (Recommended)

**Step 1: Submit for Processing**
- URL: `/api/webhook/process-split`
- This returns immediately with a task_id

**Step 2: Add Delay**
- Use "Delay by Zapier" 
- Wait for 5-10 minutes (based on video length)

**Step 3: Retrieve Results**  
- URL: `/api/webhook/check-status`
- Send the task_id
- Get the PDF back

### Option 2: Use External Storage (Best for Production)

Instead of trying to return the PDF through Zapier, save it directly to storage:

1. **Process video** → Save PDF to S3/Google Drive/Dropbox
2. **Return URL** to Zapier
3. **Zapier sends notification** with link

## Quick Fix for Your Current Setup

Since you want to return data to Zapier, use the `/api/webhook/process-split` endpoint:

```
https://dozentenfeedback-b142ue19i-lennards-projects-d56ed79f.vercel.app/api/webhook/process-split
```

This endpoint:
- Tries to process videos under 20 minutes immediately
- Returns a task_id for longer videos
- You can check status after a delay

## For Videos Over 20 Minutes

The reality is that for very long videos (over 20 minutes), you need:

1. **External processing** (not Vercel Functions)
   - Use a background job service like Render, Railway, or Fly.io
   - Or use AWS Lambda with extended timeout (15 minutes)

2. **Direct storage integration**
   - Process the video
   - Save PDF directly to Google Drive
   - Send notification with link

## Recommended Production Architecture

```
Zoom → Zapier → Submit Endpoint → Queue (SQS/Redis) → Worker (processes video) → Google Drive
                                                                                  ↓
                                                    Zapier ← Notification (via webhook or email)
```

This avoids ALL timeout issues because:
- Submit endpoint returns immediately
- Worker processes in background (no timeout)
- Results go directly to storage
- Notification sent when complete