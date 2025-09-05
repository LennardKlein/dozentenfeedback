#!/usr/bin/env python3
"""
GitHub Actions Webhook Trigger
This script triggers a GitHub Actions workflow via repository_dispatch
"""

import os
import sys
import json
import requests
from datetime import datetime

def trigger_github_action(video_url, metadata, github_token=None, repo_owner="lennardklein", repo_name="dozentenfeedback"):
    """
    Trigger GitHub Actions workflow using repository_dispatch
    """
    
    # GitHub API endpoint
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/dispatches"
    
    # Get token from environment or parameter
    token = github_token or os.environ.get('GITHUB_TOKEN')
    if not token:
        raise ValueError("GitHub token not provided. Set GITHUB_TOKEN environment variable.")
    
    # Prepare payload
    payload = {
        "event_type": "process-video",
        "client_payload": {
            "video_url": video_url,
            "topic": metadata.get('topic', 'Unknown'),
            "host_email": metadata.get('host_email', 'mail@lennard-klein.com'),
            "duration": metadata.get('duration', 'Unknown'),
            "meeting_id": metadata.get('meeting_id', 'Unknown'),
            "triggered_at": datetime.now().isoformat()
        }
    }
    
    # Headers with authentication
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {token}",
        "Content-Type": "application/json"
    }
    
    # Send request
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 204:
        print(f"✅ Successfully triggered GitHub Actions workflow")
        print(f"   Repository: {repo_owner}/{repo_name}")
        print(f"   Video URL: {video_url[:100]}...")
        print(f"   Topic: {metadata.get('topic', 'Unknown')}")
        return {
            "success": True,
            "message": "GitHub Actions workflow triggered successfully",
            "repository": f"{repo_owner}/{repo_name}",
            "workflow_url": f"https://github.com/{repo_owner}/{repo_name}/actions",
            "metadata": metadata
        }
    else:
        print(f"❌ Failed to trigger workflow: {response.status_code}")
        print(f"   Response: {response.text}")
        return {
            "success": False,
            "error": f"Failed with status {response.status_code}",
            "response": response.text
        }

if __name__ == "__main__":
    # Test the trigger
    import argparse
    
    parser = argparse.ArgumentParser(description='Trigger GitHub Actions for video processing')
    parser.add_argument('--video-url', required=True, help='URL of the video to process')
    parser.add_argument('--topic', default='Test Video', help='Video topic')
    parser.add_argument('--host-email', default='mail@lennard-klein.com', help='Host email')
    parser.add_argument('--duration', default='60', help='Duration in minutes')
    parser.add_argument('--meeting-id', default='test-123', help='Meeting ID')
    parser.add_argument('--token', help='GitHub token (or set GITHUB_TOKEN env var)')
    parser.add_argument('--repo-owner', default='lennardklein', help='GitHub repository owner')
    parser.add_argument('--repo-name', default='dozentenfeedback', help='GitHub repository name')
    
    args = parser.parse_args()
    
    metadata = {
        'topic': args.topic,
        'host_email': args.host_email,
        'duration': args.duration,
        'meeting_id': args.meeting_id
    }
    
    result = trigger_github_action(
        args.video_url, 
        metadata,
        github_token=args.token,
        repo_owner=args.repo_owner,
        repo_name=args.repo_name
    )
    
    print(json.dumps(result, indent=2))