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
