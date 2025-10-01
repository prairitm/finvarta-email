#!/usr/bin/env python3
"""
Combined Announcement Processor
Combines functionality from html.py, news.py, openai_summarizer.py, and pdf_generator.py

This script:
1. Fetches HTML from screener.in announcements page
2. Extracts company-PDF pairs from the HTML
3. Downloads and processes PDFs using OpenAI API for summarization
4. Generates a comprehensive PDF report
5. Sends the PDF report via email (optional)

Usage:
    python3 announcement_processor.py           # Process all announcements
    python3 announcement_processor.py test      # Test mode (first 3 documents)
    python3 announcement_processor.py sample    # Sample mode (use sample data)
    python3 announcement_processor.py email     # Process and send email
    python3 announcement_processor.py test email # Test mode + send email
"""

import requests
import time
import io
import re
import json
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Optional, List, Tuple
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "12000"))
DELAY_BETWEEN_REQUESTS = int(os.getenv("DELAY_BETWEEN_REQUESTS", "2"))

# File Configuration
SUMMARIES_FILE = os.getenv("SUMMARIES_FILE", "openai_announcement_summaries.json")
PDF_OUTPUT_FILE = os.getenv("PDF_OUTPUT_FILE", "New_Announcements_Report.pdf")
FULL_PDF_OUTPUT_FILE = os.getenv("FULL_PDF_OUTPUT_FILE", "Corporate_Announcements_Report.pdf")

# Email Configuration
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECIPIENTS = os.getenv("EMAIL_RECIPIENTS", "").split(",") if os.getenv("EMAIL_RECIPIENTS") else []

# Email Content Configuration
EMAIL_SUBJECT_PREFIX = os.getenv("EMAIL_SUBJECT_PREFIX", "Corporate Announcements Report")
EMAIL_SENDER_NAME = os.getenv("EMAIL_SENDER_NAME", "FinVarta AI")
EMAIL_GREETING = os.getenv("EMAIL_GREETING", "Dear User,")
EMAIL_SIGNATURE = os.getenv("EMAIL_SIGNATURE", "Best regards,\nFinVarta AI")

# Web Scraping Configuration
SCREENER_BASE_URL = os.getenv("SCREENER_BASE_URL", "https://www.screener.in")
SCREENER_ANNOUNCEMENTS_URL = os.getenv("SCREENER_ANNOUNCEMENTS_URL", f"{SCREENER_BASE_URL}/announcements/")
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# PDF regex pattern
PDF_REGEX = re.compile(r"\.pdf(?:[#?].*)?$", re.IGNORECASE)


def parse_cookie_header(cookie_header: str) -> Dict[str, str]:
    """
    Convert a raw 'Cookie:' header string into a dict for requests.
    """
    cookies = {}
    for part in cookie_header.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


def get_screener_announcements(
    cookie_header: Optional[str] = None,
    timeout: int = 20
) -> str:
    """
    Fetches https://www.screener.in/announcements/ and returns the HTML as text.

    Args:
        cookie_header: A raw Cookie header string (e.g., "key1=val1; key2=val2").
                       If None, no cookies are sent.
        timeout: Request timeout in seconds.

    Returns:
        The response body (HTML) as a string.

    Raises:
        requests.HTTPError on non-2xx responses.
        requests.RequestException for network/timeout issues.
    """
    url = SCREENER_ANNOUNCEMENTS_URL

    # Headers mirroring your browser request (minus HTTP/2 pseudo-headers)
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
        "priority": "u=0, i",
        "referer": "https://www.screener.in/announcements/user-filters/86082/",
        "sec-ch-ua": "\"Not;A=Brand\";v=\"99\", \"Google Chrome\";v=\"139\", \"Chromium\";v=\"139\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"macOS\"",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": USER_AGENT,
    }

    cookies = parse_cookie_header(cookie_header) if cookie_header else None

    with requests.Session() as s:
        # Requests handles compression automatically for gzip/deflate/br/zstd when available.
        resp = s.get(url, headers=headers, cookies=cookies, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        return resp.text


def extract_groups(html_text: str) -> Tuple[List[str], List[Tuple[str, str]]]:
    """
    Extract company-PDF pairs from HTML content.
    
    Args:
        html_text: HTML content as string
        
    Returns:
        Tuple of (group_1, group_2) where:
        - group_1: hrefs containing '/company' and ending with .pdf
        - group_2: consecutive pairs (href_i has '/company', href_{i+1} ends with .pdf)
    """
    # Parse HTML
    soup = BeautifulSoup(html_text, "html.parser")

    # Collect hrefs
    hrefs = [a.get("href").strip() for a in soup.find_all("a") if a.get("href")]

    # Group 1: contains '/company' and ends with .pdf
    group_1 = [h for h in hrefs if "/company" in h and PDF_REGEX.search(h)]

    # Group 2: consecutive company -> pdf
    group_2 = []
    for i in range(len(hrefs) - 1):
        if "/company" in hrefs[i] and PDF_REGEX.search(hrefs[i + 1]):
            group_2.append((hrefs[i], hrefs[i + 1]))

    return group_1, group_2


def query_openai_api(text: str, company_name: str) -> str:
    """Query OpenAI API for text summarization with a custom prompt"""
    
    # Clean and truncate text to avoid token limits
    cleaned_text = text.strip()
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
    
    # Truncate if too long (OpenAI has token limits)
    if len(cleaned_text) > MAX_TEXT_LENGTH:
        cleaned_text = cleaned_text[:MAX_TEXT_LENGTH] + "..."
        print(f"Text truncated to {len(cleaned_text)} characters")
    
    if not cleaned_text.strip():
        return "No meaningful text to summarize"
    
    # Create a comprehensive prompt for financial document summarization
    prompt = f"""
You are a financial analyst specializing in Indian stock market announcements. Please analyze and summarize the following corporate announcement document for {company_name}.

Document Text:
{cleaned_text}

Please provide a structured summary that includes:

1. **Document Type**: What type of announcement is this? (AGM, EGM, Quarterly Results, Dividend, Board Meeting, etc.)

2. **Summary**: A concise 2-3 sentence summary of the most important information

3. **Sentiment Analysis**: Assess the overall sentiment of the announcement (e.g., Positive, Negative, Neutral) and briefly explain your reasoning.

4. **Key Dates**: Extract any important dates mentioned (meeting dates, record dates, ex-dates, etc.)

5. **Financial Highlights**: Any financial figures, ratios, or performance metrics mentioned

6. **Corporate Actions**: Any dividends, bonuses, stock splits, or other corporate actions

7. **Business Updates**: Any significant business developments, partnerships, or strategic initiatives

8. **Regulatory Compliance**: Any regulatory filings, compliance updates, or SEBI-related information



Format your response as a clear, structured summary that would be useful for investors and analysts.
"""

    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": "You are a professional financial analyst with expertise in Indian corporate announcements and stock market regulations."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            timeout=30
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        error_str = str(e)
        if "rate_limit" in error_str.lower():
            print("Rate limit exceeded, waiting 60 seconds...")
            time.sleep(60)
            return query_openai_api(text, company_name)  # Retry once
        else:
            return f"OpenAI API Error: {error_str}"


def create_basic_summary(text: str) -> str:
    """Create a basic summary when API fails"""
    lines = text.split('\n')
    important_lines = []
    
    # Look for lines with key financial terms
    keywords = ['announcement', 'notice', 'meeting', 'dividend', 'result', 'quarterly', 'annual', 'board', 'agm', 'egm', 'sebi', 'bse', 'nse']
    
    for line in lines[:50]:  # Check first 50 lines
        line_lower = line.lower().strip()
        if any(keyword in line_lower for keyword in keywords) and len(line.strip()) > 10:
            important_lines.append(line.strip())
    
    if important_lines:
        return f"Key Information: {' | '.join(important_lines[:3])}"
    else:
        # Fallback to first few sentences
        sentences = text.split('.')[:3]
        return f"Document Preview: {'. '.join(sentences)}..."


def extract_pdf_text(url: str, headers: Dict[str, str]) -> str:
    """Extract text from PDF URL"""
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        with io.BytesIO(response.content) as open_pdf_file:
            reader = PdfReader(open_pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ''
            return text
    except requests.RequestException as e:
        return f"Request Error: {e}"
    except Exception as e:
        return f"PDF Processing Error: {e}"


def get_company_name_from_url(company_url: str) -> str:
    """Extract company name from URL"""
    match = re.search(r'/company/([^/]+)/?', company_url)
    if match:
        return match.group(1)
    return "Unknown Company"


def get_sample_html_data() -> str:
    """Return sample HTML data for testing purposes"""
    return """
<div>

  <div class="card card-medium">
    <div class="sub margin-bottom-16">Today</div>
    
      <div class="bordered rounded padding-12-18 announcement-item margin-top-12">
        <div class="flex flex-gap-16">
          <img class="img-32" src="https://cdn-static.screener.in/icons/announcement.0a7339d57d0a.svg" alt="press release">
          <div class="flex flex-column">
            <a href="/company/MAHSCOOTER/" class="font-weight-500 font-size-14 sub-link" target="_blank">
              <span class="ink-900 hover-link">Mah. Scooters</span>
              <i class="icon-link-ext"></i>
            </a>
            <a href="https://www.bseindia.com/stockinfo/AnnPdfOpen.aspx?Pname=0b1f42b4-9fae-4035-af80-0ebf86322ba5.pdf" target="_blank" rel="noopener noreferrer">
              Intimation Under Regulation 42 Of The SEBI (LODR) Regulations, 2015 - Record Date
              <i class="icon-file-pdf font-size-14"></i>
              
                <span class="ink-600 smaller">25m ago</span>
              
                <div class="sub">Interim dividend Rs160 per share; record date 22 Sep 2025; payout ~13 Oct 2025; Company Secretary appointed 1 Oct.</div>
              
            </a>
          </div>
        </div>
      </div>
    
      <div class="bordered rounded padding-12-18 announcement-item margin-top-12">
        <div class="flex flex-gap-16">
          <img class="img-32" src="https://cdn-static.screener.in/icons/announcement.0a7339d57d0a.svg" alt="press release">
          <div class="flex flex-column">
            <a href="/company/TCS/consolidated/" class="font-weight-500 font-size-14 sub-link" target="_blank">
              <span class="ink-900 hover-link">TCS</span>
              <i class="icon-link-ext"></i>
            </a>
            <a href="https://www.bseindia.com/stockinfo/AnnPdfOpen.aspx?Pname=030da518-31d8-4310-9aa8-64d1212a352f.pdf" target="_blank" rel="noopener noreferrer">
              Press Release - The Warehouse Group Selects TCS To Lead Strategic IT Transformation Initiatives
              <i class="icon-file-pdf font-size-14"></i>
              
                <span class="ink-600 smaller">48m ago</span>
              
                <div class="sub">TCS to modernise TWG's IT; partnership estimated to cut licenses/managed services costs by up to $40 million over five years.</div>
              
            </a>
          </div>
        </div>
      </div>
    
      <div class="bordered rounded padding-12-18 announcement-item margin-top-12">
        <div class="flex flex-gap-16">
          <img class="img-32" src="https://cdn-static.screener.in/icons/announcement.0a7339d57d0a.svg" alt="press release">
          <div class="flex flex-column">
            <a href="/company/LT/consolidated/" class="font-weight-500 font-size-14 sub-link" target="_blank">
              <span class="ink-900 hover-link">Larsen &amp; Toubro</span>
              <i class="icon-link-ext"></i>
            </a>
            <a href="https://www.bseindia.com/stockinfo/AnnPdfOpen.aspx?Pname=14409621-a12b-41a1-90bc-647e73dbd239.pdf" target="_blank" rel="noopener noreferrer">
              Announcement under Regulation 30 (LODR)-Award_of_Order_Receipt_of_Order
              <i class="icon-file-pdf font-size-14"></i>
              
                <span class="ink-600 smaller">1h ago</span>
              
                <div class="sub">Won 156 RKM ballastless track Package T1 for Mumbai-Ahmedabad HSR; includes 21km underground; announced 15 Sept 2025.</div>
              
            </a>
          </div>
        </div>
      </div>
    
  </div>

</div>
"""


def generate_pdf_report(new_summaries=None):
    """
    Generate PDF report using the pdf_generator.py functionality
    
    Args:
        new_summaries: List of new summaries to include in PDF. If None, includes all summaries.
    """
    print("📊 Generating PDF report...")
    
    try:
        if new_summaries is not None and len(new_summaries) > 0:
            # Generate PDF with only new summaries
            from pdf_generator import CorporateAnnouncementsPDFGenerator
            
            # Create a temporary generator with only new summaries
            generator = CorporateAnnouncementsPDFGenerator()
            
            # Override the data loading to use only new summaries
            generator.summaries_data = new_summaries
            
            # Generate PDF with custom filename
            generator.generate_pdf(output_filename=PDF_OUTPUT_FILE)
            print(f"✅ PDF report generated successfully with {len(new_summaries)} new announcements")
        elif new_summaries is not None and len(new_summaries) == 0:
            # No new summaries to process - skip PDF generation
            print("ℹ️  No new announcements to include in PDF report")
            return True
        else:
            # Generate PDF with all summaries (original behavior)
            from pdf_generator import CorporateAnnouncementsPDFGenerator
            generator = CorporateAnnouncementsPDFGenerator()
            generator.generate_pdf()
            print("✅ PDF report generated successfully")
        return True
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        return False


def send_email_with_pdf(pdf_filename=PDF_OUTPUT_FILE):
    """
    Send individual emails with PDF attachment to each recipient
    Each recipient only sees their own email address
    
    Args:
        pdf_filename: Name of the PDF file to attach
    """
    print("📧 Sending individual emails with PDF attachment...")
    
    # Check if email configuration is set
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("⚠️  Email configuration not set. Please update EMAIL_SENDER and EMAIL_PASSWORD in the .env file.")
        print("   For Gmail, use an App Password instead of your regular password.")
        return False
    
    # Check if PDF file exists
    if not os.path.exists(pdf_filename):
        print(f"❌ PDF file {pdf_filename} not found")
        return False
    
    try:
        # Connect to SMTP server once
        server = smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        
        successful_sends = 0
        
        # Send individual email to each recipient
        for recipient in EMAIL_RECIPIENTS:
            try:
                # Create message for this recipient
                msg = MIMEMultipart()
                msg['From'] = EMAIL_SENDER
                msg['To'] = recipient  # Only this recipient sees their email
                msg['Subject'] = f"{EMAIL_SUBJECT_PREFIX} - {time.strftime('%Y-%m-%d %H:%M')}"
                
                # Email body
                body = f"""
{EMAIL_GREETING}

Please find attached the latest Corporate Announcements Report generated on {time.strftime('%Y-%m-%d at %H:%M')}.

This report contains:
• Executive Summary of all announcements
• Detailed analysis of each company announcement
• AI-powered sentiment analysis
• Comprehensive market intelligence

The report was generated using AI for intelligent analysis of corporate announcements.

{EMAIL_SIGNATURE}
                """
                
                msg.attach(MIMEText(body, 'plain'))
                
                # Attach PDF file
                with open(pdf_filename, "rb") as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {pdf_filename}',
                )
                msg.attach(part)
                
                # Send email to this recipient only
                text = msg.as_string()
                server.sendmail(EMAIL_SENDER, [recipient], text)
                successful_sends += 1
                print(f"✅ Email sent to: {recipient}")
                
            except Exception as e:
                print(f"❌ Error sending email to {recipient}: {e}")
        
        server.quit()
        
        print(f"✅ Successfully sent {successful_sends} out of {len(EMAIL_RECIPIENTS)} emails")
        print(f"📎 Attached file: {pdf_filename}")
        return successful_sends > 0
        
    except Exception as e:
        print(f"❌ Error connecting to email server: {e}")
        return False


def load_existing_summaries():
    """Load existing summaries to check for duplicates"""
    try:
        with open(SUMMARIES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []


def get_processed_pdf_urls():
    """Get set of already processed PDF URLs"""
    existing_summaries = load_existing_summaries()
    return {summary.get('pdf_url', '') for summary in existing_summaries}


def filter_new_announcements(announcements: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """
    Filter out announcements that have already been processed
    
    Args:
        announcements: List of (company_url, pdf_url) tuples
        
    Returns:
        List of new announcements that haven't been processed yet
    """
    processed_urls = get_processed_pdf_urls()
    new_announcements = []
    
    for company_url, pdf_url in announcements:
        if pdf_url not in processed_urls:
            new_announcements.append((company_url, pdf_url))
        else:
            print(f"⏭️  Skipping already processed: {pdf_url}")
    
    return new_announcements


def process_announcements(cookie_header: Optional[str] = None, test_mode: bool = False, use_sample_data: bool = False):
    """
    Main function to process announcements from screener.in
    
    Args:
        cookie_header: Optional cookie header for authentication
        test_mode: If True, only process first 3 documents
        use_sample_data: If True, use sample HTML data instead of fetching from web
        
    Returns:
        List of new summaries that were processed in this run
    """
    
    # Download headers for PDF requests
    download_headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br'
    }
    
    print("=" * 80)
    print("STOCK MARKET ANNOUNCEMENTS PROCESSOR")
    print("=" * 80)
    
    # Step 1: Get HTML content
    if use_sample_data:
        print("Step 1: Using sample HTML data...")
        html_content = get_sample_html_data()
        print("✅ Sample HTML data loaded")
    else:
        print("Step 1: Fetching HTML from screener.in...")
        try:
            html_content = get_screener_announcements(cookie_header)
            print("✅ HTML fetched successfully")
        except Exception as e:
            print(f"❌ Failed to fetch HTML: {e}")
            return
    
    # Step 2: Extract company-PDF pairs
    print("\nStep 2: Extracting company-PDF pairs...")
    g1, g2 = extract_groups(html_content)
    print(f"✅ Found {len(g1)} general announcements and {len(g2)} company-PDF pairs")
    
    # Step 3: Check for already processed announcements
    print("\nStep 3: Checking for already processed announcements...")
    existing_summaries = load_existing_summaries()
    print(f"📊 Found {len(existing_summaries)} previously processed announcements")
    
    # Filter out already processed announcements
    new_announcements = filter_new_announcements(g2)
    print(f"🆕 Found {len(new_announcements)} new announcements to process")
    
    # Process Group 1 (if any)
    if g1:
        print("\nGROUP 1 - General Announcements:")
        print("-" * 50)
        for item in g1:
            print(f"• {item}")
    
    # Initialize summaries list with existing summaries
    summaries = existing_summaries.copy()
    new_summaries = []  # Track new summaries added in this run
    
    # Process Group 2 (Company-PDF pairs) - only new ones
    if new_announcements:
        # Limit to first 3 if in test mode
        if test_mode:
            new_announcements = new_announcements[:3]
            print(f"\nGROUP 2 - New Company Announcements (TEST MODE - {len(new_announcements)} documents):")
        else:
            print(f"\nGROUP 2 - New Company Announcements ({len(new_announcements)} documents):")
        print("-" * 50)
        
        for i, (company_url, pdf_url) in enumerate(new_announcements, 1):
            company_name = get_company_name_from_url(company_url)
            
            print(f"\n[{i}/{len(new_announcements)}] Processing: {company_name}")
            print(f"Company URL: {SCREENER_BASE_URL}{company_url}")
            print(f"PDF URL: {pdf_url}")
            
            # Extract PDF text
            print("Extracting PDF text...")
            pdf_text = extract_pdf_text(pdf_url, download_headers)
            
            if not pdf_text.strip() or pdf_text.startswith("Request Error") or pdf_text.startswith("PDF Processing Error"):
                summary = f"No extractable text from PDF. Error: {pdf_text}"
                print(f"⚠️  {summary}")
            else:
                print("Generating AI summary...")
                summary = query_openai_api(pdf_text, company_name)
                print(f"✅ Summary generated successfully")
                print(f"📝 Summary Preview: {summary[:200]}...")
            
            # Store summary for final report
            new_summary = {
                'company': company_name,
                'company_url': f"{SCREENER_BASE_URL}{company_url}",
                'pdf_url': pdf_url,
                'summary': summary,
                'text_length': len(pdf_text) if pdf_text else 0,
                'model_used': DEFAULT_MODEL
            }
            summaries.append(new_summary)
            new_summaries.append(new_summary)  # Track this as a new summary
            
            print("=" * 50)
            
            # Add delay to avoid overwhelming the API
            if i < len(new_announcements):
                time.sleep(DELAY_BETWEEN_REQUESTS)
    else:
        print(f"\nGROUP 2 - No new announcements to process")
        print("✅ All announcements have already been processed")
        print("-" * 50)
    
    # Generate final summary report
    print("\n" + "=" * 80)
    print("FINAL SUMMARY REPORT")
    print("=" * 80)
    
    # Calculate new vs existing summaries
    new_summaries = summaries[len(existing_summaries):] if len(summaries) > len(existing_summaries) else []
    successful_summaries = [s for s in summaries if not s['summary'].startswith("No extractable text") and not s['summary'].startswith("OpenAI API Error")]
    failed_summaries = [s for s in summaries if s['summary'].startswith("No extractable text") or s['summary'].startswith("OpenAI API Error")]
    
    print(f"Total Documents in Database: {len(summaries)}")
    print(f"Previously Processed: {len(existing_summaries)}")
    print(f"New Documents Processed: {len(new_summaries)}")
    print(f"Successfully Summarized: {len(successful_summaries)}")
    print(f"Failed to Process: {len(failed_summaries)}")
    
    if successful_summaries:
        print(f"\nSUCCESSFUL SUMMARIES:")
        print("-" * 50)
        for summary in successful_summaries:
            print(f"\n🏢 {summary['company']}")
            print(f"📄 PDF: {summary['pdf_url']}")
            print(f"📊 Text Length: {summary['text_length']} characters")
            print(f"🤖 Model: {summary['model_used']}")
            print(f"📝 Summary: {summary['summary']}")
            print("-" * 30)
    
    if failed_summaries:
        print(f"\nFAILED TO PROCESS:")
        print("-" * 50)
        for summary in failed_summaries:
            print(f"❌ {summary['company']}: {summary['summary']}")
    
    # Save to JSON file
    with open(SUMMARIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(summaries, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 All summaries saved to: {SUMMARIES_FILE}")
    
    # Generate PDF report
    print("\n" + "=" * 80)
    print("GENERATING PDF REPORT")
    print("=" * 80)
    
    if generate_pdf_report(new_summaries):
        print("✅ PDF report generated successfully")
    else:
        print("❌ Failed to generate PDF report")
    
    print("=" * 80)
    
    return new_summaries


def show_help():
    """Show usage help"""
    print("""
📊 CORPORATE ANNOUNCEMENTS PROCESSOR
====================================

This script processes corporate announcements from screener.in and generates AI-powered summaries.

USAGE:
    python3 announcement_processor.py [mode] [email]

MODES:
    (no mode)     Process all announcements from screener.in
    test          Process only first 3 documents (for testing)
    sample        Use sample HTML data (for testing without web requests)
    email         Process announcements and send PDF via email

EMAIL OPTION:
    email         Add 'email' as second argument to send PDF report via email

EXAMPLES:
    python3 announcement_processor.py                    # Process all announcements
    python3 announcement_processor.py test               # Test mode (3 documents)
    python3 announcement_processor.py sample             # Sample mode (no web requests)
    python3 announcement_processor.py email              # Process + send email
    python3 announcement_processor.py test email         # Test + send email
    python3 announcement_processor.py sample email       # Sample + send email

CONFIGURATION:
    Before using email functionality, update these settings in the script:
    - EMAIL_SENDER: Your email address
    - EMAIL_PASSWORD: Your email password (use App Password for Gmail)
    - EMAIL_RECIPIENTS: List of recipient email addresses

OUTPUTS:
    - openai_announcement_summaries.json: AI summaries in JSON format
    - Corporate_Announcements_Report.pdf: Comprehensive PDF report
    - Email with PDF attachment (if email mode enabled)
    """)


def main():
    """Main entry point"""
    import sys
    
    # Check for help request
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help", "help"]:
        show_help()
        return
    
    # Check if OpenAI API key is set
    if not OPENAI_API_KEY:
        print("❌ Please set your OpenAI API key in the .env file!")
        print("Add OPENAI_API_KEY=your-api-key to the .env file")
        sys.exit(1)
    
    # Parse command line arguments
    test_mode = len(sys.argv) > 1 and sys.argv[1] == "test"
    sample_mode = len(sys.argv) > 1 and sys.argv[1] == "sample"
    email_mode = len(sys.argv) > 1 and sys.argv[1] == "email"
    send_email = len(sys.argv) > 2 and sys.argv[2] == "email"
    
    # Optional cookie header for authentication (load from environment)
    cookie_header = os.getenv("SCREENER_COOKIE_HEADER")
    # cookie_header = None
    
    if test_mode:
        print("🧪 Running in TEST MODE (processing first 3 documents only)")
    elif sample_mode:
        print("📄 Running in SAMPLE MODE (using sample HTML data)")
    elif email_mode:
        print("📧 Running in EMAIL MODE (processing announcements and sending email)")
    
    # Process announcements
    new_summaries = process_announcements(cookie_header=cookie_header, test_mode=test_mode, use_sample_data=sample_mode)
    
    # Send email only if a new PDF was generated
    if (email_mode or send_email) and new_summaries is not None and len(new_summaries) > 0:
        print("\n" + "=" * 80)
        print("SENDING EMAIL")
        print("=" * 80)
        
        # Use the PDF filename that was actually generated
        pdf_filename = PDF_OUTPUT_FILE
        
        if send_email_with_pdf(pdf_filename):
            print("✅ Email sent successfully")
        else:
            print("❌ Failed to send email")
        
        print("=" * 80)
    elif (email_mode or send_email):
        print("\n" + "=" * 80)
        print("No new announcements, so no email sent.")
        print("=" * 80)


if __name__ == "__main__":
    main()
