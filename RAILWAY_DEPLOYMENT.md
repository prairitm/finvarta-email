# Railway Deployment Guide

This guide will help you deploy your FastAPI Corporate Announcements Processor to Railway.

## Prerequisites

1. **GitHub Repository**: Your code should be pushed to a GitHub repository
2. **Railway Account**: Sign up at [railway.app](https://railway.app)
3. **Environment Variables**: Have your API keys and credentials ready

## Step 1: Deploy to Railway

### Option A: Deploy from GitHub (Recommended)

1. **Go to Railway Dashboard**
   - Visit [railway.app](https://railway.app)
   - Sign in with your GitHub account

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your `finvarta-email` repository
   - Railway will automatically detect it's a Python project
   - **Important**: Make sure to push all the new configuration files (railway.json, nixpacks.toml, .dockerignore) to your repository

3. **Configure Environment Variables**
   - Go to your project dashboard
   - Click on "Variables" tab
   - Add the following environment variables:

   ```
   OPENAI_API_KEY=your-openai-api-key
   EMAIL_SENDER=your-email@gmail.com
   EMAIL_PASSWORD=your-app-password
   EMAIL_RECIPIENTS=recipient1@example.com,recipient2@example.com
   SCREENER_COOKIE_HEADER=your-cookie-header (optional)
   ```

4. **Deploy**
   - Railway will automatically build and deploy your application
   - You'll get a URL like: `https://your-app-name.up.railway.app`

### Option B: Deploy with Railway CLI

1. **Install Railway CLI**
   ```bash
   npm install -g @railway/cli
   ```

2. **Login to Railway**
   ```bash
   railway login
   ```

3. **Initialize Project**
   ```bash
   railway init
   ```

4. **Set Environment Variables**
   ```bash
   railway variables set OPENAI_API_KEY=your-key
   railway variables set EMAIL_SENDER=your-email
   railway variables set EMAIL_PASSWORD=your-password
   railway variables set EMAIL_RECIPIENTS=recipient1,recipient2
   ```

5. **Deploy**
   ```bash
   railway up
   ```

## Step 2: Test Your Deployment

Once deployed, test your endpoints:

### Health Check
```bash
curl https://your-app-name.up.railway.app/health
```

### Process Announcements
```bash
curl -X POST "https://your-app-name.up.railway.app/process"
```

### Test Mode (3 documents only)
```bash
curl -X POST "https://your-app-name.up.railway.app/process?test_mode=true"
```

### Sample Data Mode
```bash
curl -X POST "https://your-app-name.up.railway.app/process?use_sample_data=true"
```

## Step 3: Configure Custom Domain (Optional)

1. **In Railway Dashboard**
   - Go to your project settings
   - Click "Domains"
   - Add your custom domain
   - Follow the DNS configuration instructions

## Step 4: Set Up Monitoring

1. **View Logs**
   - In Railway dashboard, click on "Deployments"
   - Click on your latest deployment
   - View real-time logs

2. **Monitor Usage**
   - Check the "Metrics" tab for CPU, memory, and network usage
   - Monitor your Railway usage in the dashboard

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | Your OpenAI API key for AI processing |
| `EMAIL_SENDER` | Yes | Email address to send from |
| `EMAIL_PASSWORD` | Yes | Email password (use App Password for Gmail) |
| `EMAIL_RECIPIENTS` | Yes | Comma-separated list of recipient emails |
| `SCREENER_COOKIE_HEADER` | No | Authentication cookie for screener.in |

## Troubleshooting

### Common Issues

1. **Build Failures**
   - Check that all dependencies are in `requirements.txt`
   - Ensure Python version compatibility

2. **Environment Variables Not Working**
   - Verify variables are set in Railway dashboard
   - Check variable names match exactly (case-sensitive)

3. **Email Not Sending - Network Unreachable (Errno 101)**
   - Railway's network may block outbound SMTP connections on port 587
   - The app automatically tries port 465 (SSL) as fallback
   - **Solution 1**: Use an email service API instead of SMTP (recommended)
     - Consider: SendGrid, Mailgun, Postmark, AWS SES
   - **Solution 2**: Use Railway's TCP Proxy for outbound connections
   - **Solution 3**: Set `EMAIL_SMTP_PORT=465` environment variable to use SSL directly
   - Verify email credentials are correct
   - For Gmail, use App Password instead of regular password
   - Check Railway logs for detailed error messages

4. **OpenAI API Errors**
   - Verify your API key is valid and has credits
   - Check API rate limits

### Getting Help

- **Railway Documentation**: [docs.railway.app](https://docs.railway.app)
- **Railway Discord**: [discord.gg/railway](https://discord.gg/railway)
- **Check Logs**: Always check Railway deployment logs for detailed error messages

## Cost Information

- **Free Tier**: $5 credit monthly (usually sufficient for small applications)
- **Usage**: Pay only for what you use
- **Scaling**: Automatically scales based on traffic

## Security Notes

- Never commit API keys or passwords to your repository
- Use Railway's environment variables for sensitive data
- Consider using Railway's secrets management for production

## Next Steps

1. **Set up monitoring** for your application
2. **Configure custom domain** if needed
3. **Set up automated deployments** from your main branch
4. **Consider setting up alerts** for failed deployments

Your FastAPI application is now deployed and ready to process corporate announcements!
