# FinVarta Email - Corporate Announcements Processor

This script processes corporate announcements from screener.in and generates AI-powered summaries with email delivery capabilities.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

3. Update the `.env` file with your actual credentials:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `EMAIL_SENDER`: Your email address
   - `EMAIL_PASSWORD`: Your email password (use App Password for Gmail)
   - `EMAIL_RECIPIENTS`: Comma-separated list of recipient emails
   - `SCREENER_COOKIE_HEADER`: Optional authentication for screener.in

## Usage

```bash
python3 announcement_processor.py           # Process all announcements
python3 announcement_processor.py test      # Test mode (first 3 documents)
python3 announcement_processor.py sample   # Sample mode (use sample data)
python3 announcement_processor.py email     # Process and send email
python3 announcement_processor.py test email # Test mode + send email
```

## Security

All sensitive information (API keys, passwords, etc.) is now stored in the `.env` file and should never be committed to version control. The `.env` file is automatically ignored by git.


# Corporate Announcements Processor API

A FastAPI application that processes corporate announcements and sends email reports.

## Features

- **Single Endpoint**: `/process` - Equivalent to `python3 announcement_processor.py email`
- **Email Integration**: Automatically sends PDF reports via email
- **Test Mode**: Process only first 3 documents for testing
- **Sample Data Mode**: Use sample data without web requests
- **Health Check**: Monitor API status and configuration

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables** (create `.env` file):
   ```env
   OPENAI_API_KEY=your-openai-api-key
   EMAIL_SENDER=your-email@gmail.com
   EMAIL_PASSWORD=your-app-password
   EMAIL_RECIPIENTS=recipient1@example.com,recipient2@example.com
   ```

3. **Run the API**:
   ```bash
   python fastapi_app.py
   ```

4. **Test the Endpoint**:
   ```bash
   curl -X POST "http://localhost:8000/process"
   ```

## API Endpoints

### POST `/process`
Process announcements and send email report.

**Parameters** (query parameters):
- `test_mode` (bool, optional): Process only first 3 documents (default: false)
- `use_sample_data` (bool, optional): Use sample data instead of web requests (default: false)
- `cookie_header` (string, optional): Authentication cookie for screener.in

**Example Requests**:
```bash
# Process all announcements
curl -X POST "http://localhost:8000/process"

# Test mode (3 documents only)
curl -X POST "http://localhost:8000/process?test_mode=true"

# Use sample data (no web requests)
curl -X POST "http://localhost:8000/process?use_sample_data=true"

# With authentication cookie
curl -X POST "http://localhost:8000/process?cookie_header=your-cookie-value"
```

**Response Example**:
```json
{
  "success": true,
  "processing_time_seconds": 45.67,
  "new_announcements_processed": 5,
  "test_mode": false,
  "sample_data_used": false,
  "timestamp": "2024-01-15 14:30:25",
  "email_sent": true,
  "email_time_seconds": 2.34,
  "pdf_filename": "New_Announcements_Report.pdf",
  "recipients": ["user1@example.com", "user2@example.com"],
  "new_announcements": [
    {
      "company": "TCS",
      "pdf_url": "https://example.com/announcement.pdf",
      "text_length": 2500,
      "model_used": "gpt-3.5-turbo"
    }
  ]
}
```

### GET `/health`
Check API health and configuration status.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15 14:30:25",
  "openai_configured": true,
  "email_configured": true
}
```

### GET `/`
Get API information and available endpoints.

## Configuration

The API uses the same configuration as the original `announcement_processor.py`:

- **OpenAI Settings**: `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_MAX_TOKENS`, etc.
- **Email Settings**: `EMAIL_SENDER`, `EMAIL_PASSWORD`, `EMAIL_RECIPIENTS`, etc.
- **File Settings**: `SUMMARIES_FILE`, `PDF_OUTPUT_FILE`, etc.

## Error Handling

The API provides detailed error messages for common issues:

- **500**: OpenAI API key not configured
- **500**: Email configuration missing
- **500**: Processing errors (network, PDF parsing, etc.)

## Development

To run in development mode with auto-reload:
```bash
uvicorn fastapi_app:app --reload --host 0.0.0.0 --port 8000
```

## Production Deployment

For production deployment, use a WSGI server like Gunicorn:
```bash
gunicorn fastapi_app:app -w 4 -k uvicorn.workers.UvicornWorker
```

