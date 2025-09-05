#!/usr/bin/env python3
"""
Test script for webhook integration.
Usage: python test-webhook.py [--local] [--video-url URL]
"""

import argparse
import json
import time
from typing import Dict, Any
import requests


def test_webhook(base_url: str, video_url: str, callback_url: str) -> Dict[str, Any]:
    """Test the webhook processing endpoint."""
    
    # Prepare test data
    payload = {
        "video_url": video_url,
        "callback_url": callback_url,
        "metadata": {
            "meeting_topic": "Test Meeting",
            "meeting_id": "test-123",
            "host_email": "test@example.com",
            "duration": "30",
            "recording_date": "2024-01-01"
        }
    }
    
    print(f"Testing webhook at: {base_url}/api/webhook/process")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    # Send webhook request
    response = requests.post(
        f"{base_url}/api/webhook/process",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Body: {response.text}")
    
    if response.status_code != 200:
        return {"error": f"Webhook failed with status {response.status_code}"}
    
    result = response.json()
    
    if not result.get("success"):
        return {"error": "Webhook returned success=false"}
    
    return result


def check_status(base_url: str, task_id: str) -> Dict[str, Any]:
    """Check the status of a processing task."""
    
    url = f"{base_url}/api/webhook/status?task_id={task_id}"
    print(f"\nChecking status at: {url}")
    
    response = requests.get(url)
    
    if response.status_code != 200:
        return {"error": f"Status check failed with status {response.status_code}"}
    
    return response.json()


def main():
    parser = argparse.ArgumentParser(description="Test webhook integration")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Test against local development server"
    )
    parser.add_argument(
        "--video-url",
        default="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        help="Video URL to test with (default: Big Buck Bunny sample)"
    )
    parser.add_argument(
        "--callback-url",
        default="https://webhook.site/unique",
        help="Callback URL for results (default: webhook.site)"
    )
    parser.add_argument(
        "--vercel-url",
        help="Custom Vercel deployment URL"
    )
    parser.add_argument(
        "--poll",
        action="store_true",
        help="Poll for status updates"
    )
    
    args = parser.parse_args()
    
    # Determine base URL
    if args.local:
        base_url = "http://localhost:3000"
    elif args.vercel_url:
        base_url = args.vercel_url
    else:
        print("Please specify --local or --vercel-url")
        return
    
    # Update callback URL if using webhook.site
    if args.callback_url == "https://webhook.site/unique":
        print("\n⚠️  Using default webhook.site URL.")
        print("Visit https://webhook.site to get your unique URL")
        print("Then run again with --callback-url YOUR_URL")
        user_input = input("\nEnter your webhook.site URL (or press Enter to continue): ")
        if user_input:
            args.callback_url = user_input
    
    # Test webhook
    result = test_webhook(base_url, args.video_url, args.callback_url)
    
    if "error" in result:
        print(f"\n❌ Error: {result['error']}")
        return
    
    task_id = result.get("task_id")
    print(f"\n✅ Task created: {task_id}")
    print(f"Status URL: {result.get('status_url')}")
    
    # Poll for status if requested
    if args.poll and task_id:
        print("\nPolling for status updates...")
        max_attempts = 60  # 5 minutes with 5-second intervals
        
        for i in range(max_attempts):
            time.sleep(5)
            status = check_status(base_url, task_id)
            
            print(f"Attempt {i+1}/{max_attempts}: Status = {status.get('status', 'unknown')}")
            
            if status.get("status") == "completed":
                print("\n✅ Processing completed!")
                print(f"Overall Score: {status.get('result', {}).get('overall_score')}")
                print(f"Blocks Analyzed: {status.get('result', {}).get('blocks_analyzed')}")
                break
            elif status.get("status") == "failed":
                print(f"\n❌ Processing failed: {status.get('error')}")
                break
        else:
            print("\n⏱️  Timeout: Processing taking longer than expected")
    
    print("\n📝 Check your callback URL for the final results:")
    print(f"   {args.callback_url}")


if __name__ == "__main__":
    main()