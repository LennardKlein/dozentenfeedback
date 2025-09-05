# Complete Zapier Integration Guide

## Current Setup
You have Zap #1 that triggers GitHub Actions when a Zoom recording is ready.

## Next Steps for Google Drive Integration

### Option 1: Direct Webhook Callback (Recommended)
Add a webhook callback to your GitHub Actions that notifies Zapier when processing is complete.

**Step 1: Create a Zapier Webhook URL**
1. Create a new Zap in Zapier
2. Choose trigger: "Webhooks by Zapier" → "Catch Hook"
3. Copy the webhook URL (looks like: https://hooks.zapier.com/hooks/catch/...)

**Step 2: Add the webhook URL to GitHub Secrets**
1. Go to: https://github.com/lennardklein/dozentenfeedback/settings/secrets/actions
2. Add new secret: `ZAPIER_WEBHOOK_URL` with your webhook URL

**Step 3: Your workflow will send results back**
The workflow sends a webhook with:
- PDF file (base64 encoded)
- Score and analysis summary
- Meeting metadata

**Step 4: In your second Zap**
1. Trigger: Webhooks (catches the GitHub result)
2. Action: Google Drive - Upload File
   - Convert base64 PDF to file
   - Save to your folder

### Option 2: GitHub Artifacts + API (Alternative)
1. Keep your current Zap
2. Add delay: 15-30 minutes (adjust based on typical video length)
3. Add action: HTTP Request to GitHub API
   - GET https://api.github.com/repos/lennardklein/dozentenfeedback/actions/artifacts
   - Authorization: Bearer YOUR_TOKEN
4. Parse response and download latest artifact
5. Upload to Google Drive

### Option 3: Direct Google Drive from GitHub (Simplest)
Let GitHub Actions upload directly to Google Drive:

1. Get Google Service Account credentials
2. Add to GitHub Secrets as `GOOGLE_DRIVE_CREDENTIALS`
3. The workflow already has code to upload directly!

## Recommended Approach

**Use Option 3** - Let GitHub upload directly to Google Drive. This is already partially implemented in your workflow!

### To Enable Direct Google Drive Upload:

1. **Create Google Service Account:**
   - Go to Google Cloud Console
   - Create new service account
   - Download JSON credentials
   - Share your Google Drive folder with the service account email

2. **Add to GitHub Secrets:**
   - Name: `GOOGLE_DRIVE_CREDENTIALS`
   - Value: Paste the entire JSON credentials file
   - Add another secret: `GOOGLE_DRIVE_FOLDER_ID` with your folder ID

3. **Your workflow already handles the rest!**

The PDF will automatically upload to Google Drive and the workflow will output the Google Drive link.

## Zapier Flow Summary

### Current Flow:
```
Zoom Recording Ready → Zapier Zap #1 → GitHub Actions → Process Video
```

### With Direct Upload (Option 3):
```
Zoom Recording Ready → Zapier Zap #1 → GitHub Actions → Process Video → Upload to Google Drive
```

### With Webhook Callback (Option 1):
```
Zoom Recording Ready → Zapier Zap #1 → GitHub Actions → Process Video
                                                ↓
                                    Webhook to Zapier Zap #2
                                                ↓
                                        Upload to Google Drive
```

## No Need for Delays!
Since we're using webhooks or direct upload, you don't need to add delays or polling. The system will notify you when complete.