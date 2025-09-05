#!/usr/bin/env python3
"""
Test script to verify GitHub Actions webhook trigger
This simulates what Zapier sends to GitHub
"""

import requests
import json
import sys

# GitHub repository details
GITHUB_OWNER = "lennardklein"
GITHUB_REPO = "dozentenfeedback"

# Your GitHub token (same one you'll use in Zapier)
# Replace with your actual token
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', 'YOUR_GITHUB_TOKEN')

def test_webhook():
    """Test the GitHub Actions webhook trigger"""
    
    # This is the exact payload structure Zapier should send
    payload = {
        "event_type": "process-video",
        "client_payload": {
            "video_url": "https://example.zoom.us/recording/test.mp4",
            "meeting_id": "test-meeting-123",
            "topic": "Test Video Processing",
            "participant_name": "Test User"
        }
    }
    
    # GitHub API endpoint for repository dispatch
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/dispatches"
    
    # Headers required by GitHub API
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    
    print("🚀 Testing GitHub Actions webhook...")
    print(f"📍 Endpoint: {url}")
    print(f"📦 Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 204:
            print("✅ Success! Webhook triggered successfully.")
            print("📊 Check your GitHub Actions at:")
            print(f"   https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/actions")
        else:
            print(f"❌ Failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_webhook()