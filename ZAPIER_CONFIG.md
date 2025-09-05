# Zapier Webhook Configuration for GitHub Actions

## Webhook URL
```
https://api.github.com/repos/lennardklein/dozentenfeedback/dispatches
```

## Headers
- **Authorization**: `Bearer YOUR_GITHUB_TOKEN`
- **Accept**: `application/vnd.github.v3+json`
- **Content-Type**: `application/json`

## JSON Payload Structure
```json
{
  "event_type": "process-video",
  "client_payload": {
    "video_url": "{{video_url_from_zapier}}",
    "meeting_id": "{{meeting_id_from_zapier}}",
    "topic": "{{topic_from_zapier}}",
    "participant_name": "{{participant_from_zapier}}"
  }
}
```

## Important Notes:
1. The payload MUST be wrapped in `event_type` and `client_payload`
2. Use "Custom Request" action in Zapier (not "Webhooks by Zapier")
3. Set method to POST
4. Add all three headers exactly as shown
5. Map your Zoom fields to the placeholders in client_payload

## Test Command
Run this to test the webhook locally:
```bash
python3 test_github_webhook.py
```

## Monitor Results
Check workflow runs at:
https://github.com/lennardklein/dozentenfeedback/actions