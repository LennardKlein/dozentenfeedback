#!/bin/bash

# GitHub Repository Setup Script
# This script creates and pushes the dozentenfeedback repository

echo "🚀 GitHub Repository Setup for DozentenFeedback"
echo "=============================================="
echo ""

# Check if gh is authenticated
if gh auth status > /dev/null 2>&1; then
    echo "✅ GitHub CLI is authenticated"
else
    echo "❌ GitHub CLI is not authenticated"
    echo ""
    echo "Please authenticate using one of these methods:"
    echo ""
    echo "Method 1: Device code (recommended)"
    echo "  Run: gh auth login"
    echo ""
    echo "Method 2: Personal Access Token"
    echo "  1. Go to: https://github.com/settings/tokens"
    echo "  2. Generate new token with 'repo' and 'workflow' scopes"
    echo "  3. Run: export GITHUB_TOKEN=your_token_here"
    echo "  4. Run: echo \$GITHUB_TOKEN | gh auth login --with-token"
    echo ""
    exit 1
fi

echo ""
echo "📦 Creating GitHub repository..."

# Create the repository
gh repo create dozentenfeedback \
    --public \
    --description "Automated video transcription and analysis system for Zoom recordings" \
    --homepage "https://github.com/lennardklein/dozentenfeedback" \
    --clone=false

if [ $? -eq 0 ]; then
    echo "✅ Repository created successfully"
else
    echo "⚠️  Repository might already exist or creation failed"
fi

echo ""
echo "🔗 Adding remote and pushing code..."

# Add remote if not exists
if ! git remote | grep -q "origin"; then
    git remote add origin https://github.com/lennardklein/dozentenfeedback.git
    echo "✅ Remote 'origin' added"
else
    echo "ℹ️  Remote 'origin' already exists"
fi

# Push to GitHub
echo ""
echo "📤 Pushing code to GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Success! Your repository is ready at:"
    echo "   https://github.com/lennardklein/dozentenfeedback"
    echo ""
    echo "📝 Next steps:"
    echo "1. Add secrets at: https://github.com/lennardklein/dozentenfeedback/settings/secrets/actions"
    echo "   - OPENAI_API_KEY"
    echo "   - ASSEMBLYAI_API_KEY"
    echo "   - GITHUB_TOKEN (for triggering workflows)"
    echo ""
    echo "2. Test the workflow at: https://github.com/lennardklein/dozentenfeedback/actions"
    echo ""
    echo "3. Configure Zapier webhook to trigger GitHub Actions"
else
    echo "❌ Failed to push to GitHub. Please check your authentication and try again."
fi