#!/bin/bash

# Deploy script for Railway
echo "🚀 Preparing for Railway deployment..."

# Remove any local virtual environment references
echo "📁 Cleaning up local environment references..."

# Add all files to git
git add .

# Commit changes
git commit -m "Fix Railway deployment - exclude local env directory"

# Push to GitHub
git push origin main

echo "✅ Changes pushed to GitHub"
echo "🔄 Now redeploy on Railway dashboard"
echo "📋 Make sure to set these environment variables in Railway:"
echo "   - OPENAI_API_KEY"
echo "   - EMAIL_SENDER" 
echo "   - EMAIL_PASSWORD"
echo "   - EMAIL_RECIPIENTS"
