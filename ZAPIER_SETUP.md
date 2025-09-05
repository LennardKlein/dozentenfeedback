# Zapier Workflow Setup with Google Drive

## Complete Zapier Workflow

### Step 1: Trigger - Zoom Recording
- **App**: Zoom
- **Event**: New Cloud Recording
- **Test**: Use a recent Zoom recording

### Step 2: Webhook - Process Video
- **App**: Webhooks by Zapier
- **Event**: POST
- **URL**: `https://dozentenfeedback-rypdeudue-lennards-projects-d56ed79f.vercel.app/api/webhook/process-simple`
- **Payload Type**: JSON
- **Data**:
  ```json
  {
    "video_url": "{{1. Video Files Download URL}}",
    "Topic": "{{1. Topic}}",
    "Host Email": "{{1. Host Email}}",
    "Duration": "{{1. Duration}}",
    "Meeting ID": "{{1. Meeting ID}}"
  }
  ```
- **Headers**: 
  - Key: `Content-Type`
  - Value: `application/json`

### Step 3: Google Drive - Save PDF
- **App**: Google Drive
- **Event**: Upload File
- **Drive**: My Drive (or select your preferred drive)
- **Folder**: Choose your DozentenFeedback folder
- **File**:
  - **Use a Custom Value**: Select the field from Step 2
  - **File Content**: `{{2. pdf_base64}}`
  - **Convert to Document**: No
  - **File Name**: `{{2. pdf_filename}}`
  - **File Extension**: pdf

### Step 4: Slack Notification (Optional)
- **App**: Slack
- **Event**: Send Channel Message
- **Channel**: Choose your channel
- **Message Text**:
  ```
  📊 Dozenten-Feedback Analysis Complete!
  
  **Topic**: {{1. Topic}}
  **Host**: {{1. Host Email}}
  **Score**: {{2. overall_score}}/5.0
  **Duration**: {{1. Duration}}
  
  **Summary**:
  {{2. summary}}
  
  📄 PDF Report saved to Google Drive
  ```

## What the Webhook Returns

The webhook processes the video and returns:

```json
{
  "success": true,
  "overall_score": 3.5,
  "blocks_analyzed": 3,
  "summary": "Detailed summary text...",
  "metadata": {
    "topic": "Meeting Topic",
    "host_email": "mail@example.com",
    "duration": "71 minutes",
    "meeting_id": "123456789",
    "score": 3.5
  },
  "processing_complete": true,
  "message": "Analysis complete. Score: 3.5/5.0",
  "pdf_filename": "DozentenFeedback_20240105_1430_mail_Meeting_Topic.pdf",
  "pdf_base64": "JVBERi0xLjMKJeLj...", // Base64 encoded PDF
  "pdf_size_bytes": 245678
}
```

## Key Fields for Zapier Actions

- **`pdf_base64`**: The PDF report encoded as base64 (use for Google Drive upload)
- **`pdf_filename`**: Suggested filename for the PDF
- **`overall_score`**: Numeric score (1-5) for the recording
- **`summary`**: Text summary for Slack/Email notifications
- **`metadata`**: All the original meeting information

## Testing

1. **Test the webhook first**: Use Zapier's test feature to ensure the webhook returns data
2. **Check the PDF**: The base64 data should be present in the response
3. **Verify Google Drive upload**: Ensure the PDF appears in your chosen folder
4. **Test notifications**: Make sure Slack/Email notifications contain the right data

## Troubleshooting

- **Timeout errors**: Videos longer than 5 minutes may timeout. The current limit is 300 seconds.
- **No pdf_base64 in response**: Check that the video URL is accessible and the processing completed
- **Google Drive upload fails**: Ensure you've connected your Google account and selected a valid folder
- **Score is 0**: This usually means the analysis failed - check the webhook logs in Vercel

## Processing Time

- 10-minute video: ~2-3 minutes
- 30-minute video: ~3-4 minutes  
- 60-minute video: ~4-5 minutes
- 4-hour video: May exceed timeout - consider splitting

## Support

For issues, check the Vercel function logs at:
https://vercel.com/lennards-projects-d56ed79f/dozentenfeedback/functions