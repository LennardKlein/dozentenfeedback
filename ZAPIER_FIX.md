# Fix for Zapier Configuration

## The Problem
Your Authorization header is missing "Bearer " prefix and the client_payload fields aren't properly mapped.

## Correct Configuration in Zapier:

### Headers (EXACT format):
1. **Authorization**: `Bearer YOUR_GITHUB_TOKEN`
   (Note: Must have "Bearer " before the token)

2. **Accept**: `application/vnd.github.v3+json`

3. **Content-Type**: `application/json`

### Data Section:
In the Data field, you need to properly map the Zapier variables. Use this exact structure:

```json
{
  "event_type": "process-video",
  "client_payload": {
    "video_url": "{{1__video_files_download_url}}",
    "topic": "{{1__topic}}",
    "host_email": "{{1__host_email}}",
    "duration": "{{1__duration}}",
    "meeting_id": "{{1__meeting_id}}"
  }
}
```

## Steps to Fix:

1. In the **Authorization** header field, change from:
   - `token YOUR_GITHUB_TOKEN`
   - To: `Bearer YOUR_GITHUB_TOKEN`

2. In the **client_payload** section, replace the blue pill mappings with the proper JSON structure above.

3. Make sure the JSON is valid (no trailing commas, proper quotes).

The blue pills you see in Zapier should be inserted as `{{variable_name}}` in the JSON string.