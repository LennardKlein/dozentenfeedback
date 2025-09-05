#!/usr/bin/env python3
"""
Test script for Zoom webhook integration.
Tests with actual Zoom recording data structure.
"""

import argparse
import json
import time
import requests


def test_zoom_webhook(base_url: str, zoom_data: dict, callback_url: str):
    """Test the webhook with Zoom data."""
    
    # Prepare webhook payload matching Zoom structure
    payload = {
        # Primary video URL
        "video_url": zoom_data.get("video_url"),
        "callback_url": callback_url,
        
        # Top-level Zoom fields
        "Topic": zoom_data.get("topic", "Test Meeting"),
        "Meeting ID": zoom_data.get("meeting_id", "test-123"),
        "Host Email": zoom_data.get("host_email", "admin@talentspring-academy.com"),
        "Duration": zoom_data.get("duration", "71"),
        "Start Time": zoom_data.get("start_time", "2025-09-03T11:53:00Z"),
        "Share URL": zoom_data.get("share_url", ""),
        
        # Metadata
        "metadata": {
            "meeting_uuid": zoom_data.get("meeting_uuid", "8QKMBVFhTXmKzIYpPBzGLw=="),
            "account_id": zoom_data.get("account_id", "AcQ1Qrg8RhyfIzNL3foJdw"),
            "host_id": zoom_data.get("host_id", "DU4P9R5XSsiZbpg1dmyFEA"),
            "timezone": zoom_data.get("timezone", "Europe/Berlin"),
            "total_size": zoom_data.get("total_size", "371752328"),
            "recording_count": zoom_data.get("recording_count", "4")
        }
    }
    
    print(f"Testing Zoom webhook at: {base_url}/api/webhook/process")
    print(f"Meeting Topic: {payload['Topic']}")
    print(f"Host Email: {payload['Host Email']}")
    print(f"Duration: {payload['Duration']} minutes")
    print(f"Video URL: {payload['video_url'][:100]}..." if payload['video_url'] else "No video URL")
    
    # Send webhook request
    response = requests.post(
        f"{base_url}/api/webhook/process",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"\nResponse Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        return result
    else:
        print(f"Error: {response.text}")
        return None


def check_processing_status(base_url: str, task_id: str, max_wait: int = 300):
    """Check status and wait for completion."""
    
    print(f"\nChecking status for task: {task_id}")
    print("This may take 3-5 minutes for transcription...")
    
    start_time = time.time()
    check_interval = 10  # Check every 10 seconds
    
    while time.time() - start_time < max_wait:
        response = requests.get(f"{base_url}/api/webhook/status?task_id={task_id}")
        
        if response.status_code == 200:
            status_data = response.json()
            status = status_data.get("status", "unknown")
            
            elapsed = int(time.time() - start_time)
            print(f"[{elapsed}s] Status: {status}")
            
            if status == "completed":
                print("\n✅ Processing completed!")
                if "result" in status_data:
                    result = status_data["result"]
                    print(f"Overall Score: {result.get('overall_score')}/5")
                    print(f"Blocks Analyzed: {result.get('blocks_analyzed')}")
                return status_data
            
            elif status == "failed":
                print(f"\n❌ Processing failed: {status_data.get('error')}")
                return status_data
        
        time.sleep(check_interval)
    
    print("\n⏱️ Timeout: Processing taking longer than expected")
    return None


def main():
    parser = argparse.ArgumentParser(description="Test Zoom webhook integration")
    parser.add_argument("--url", required=True, help="Vercel deployment URL")
    parser.add_argument(
        "--video-url",
        default="https://zoom.us/rec/download/_FbHNjXaLU3UJ50uOW7xjocuO6qUHp3Lry3Q_DdtZXrza2Zn4OvR7oSNlja73_zSVl9bHaGNIq9h1_1I.K1ZplQQurTpRfbsz",
        help="Zoom video download URL"
    )
    parser.add_argument(
        "--callback-url",
        help="Callback webhook URL (optional)"
    )
    parser.add_argument(
        "--topic",
        default="Karriere-Insights & Best Practices",
        help="Meeting topic"
    )
    parser.add_argument(
        "--host-email",
        default="admin@talentspring-academy.com",
        help="Host email address"
    )
    parser.add_argument(
        "--duration",
        default="71",
        help="Meeting duration in minutes"
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for processing to complete"
    )
    
    args = parser.parse_args()
    
    # Prepare Zoom data
    zoom_data = {
        "video_url": args.video_url,
        "topic": args.topic,
        "host_email": args.host_email,
        "duration": args.duration,
        "meeting_id": "8QKMBVFhTXmKzIYpPBzGLw==",
        "start_time": "2025-09-03T11:53:00Z",
        "share_url": "https://zoom.us/rec/share/example"
    }
    
    # Get callback URL
    callback_url = args.callback_url
    if not callback_url:
        print("\n📝 No callback URL provided.")
        print("Visit https://webhook.site to get a test URL")
        callback_url = input("Enter callback URL (or press Enter to skip): ").strip()
        if not callback_url:
            callback_url = "https://webhook.site/test"
    
    # Test webhook
    print("\n🚀 Sending Zoom recording to webhook...")
    result = test_zoom_webhook(args.url, zoom_data, callback_url)
    
    if result and result.get("success"):
        task_id = result.get("task_id")
        print(f"\n✅ Task created successfully!")
        print(f"Task ID: {task_id}")
        print(f"Status URL: {result.get('status_url')}")
        
        if args.wait:
            print("\n⏳ Waiting for processing to complete...")
            final_status = check_processing_status(args.url, task_id)
            
            if final_status and final_status.get("status") == "completed":
                print("\n📊 Analysis Results:")
                print("-" * 50)
                result = final_status.get("result", {})
                print(f"Overall Score: {result.get('overall_score')}/5")
                print(f"Blocks Analyzed: {result.get('blocks_analyzed')}")
                print(f"Timestamp: {result.get('timestamp')}")
                
                if callback_url and callback_url != "https://webhook.site/test":
                    print(f"\n📨 Full results sent to: {callback_url}")
    else:
        print("\n❌ Failed to create task")


if __name__ == "__main__":
    main()