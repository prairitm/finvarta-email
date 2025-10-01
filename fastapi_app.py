#!/usr/bin/env python3
"""
FastAPI Application for Corporate Announcements Processor
Provides a single endpoint that processes announcements and sends email reports
Equivalent to: python3 announcement_processor.py email
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import asyncio
import os
import sys
from typing import Optional
import json
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the announcement processor functions
from announcement_processor import (
    process_announcements,
    send_email_with_pdf,
    PDF_OUTPUT_FILE,
    EMAIL_SENDER,
    EMAIL_PASSWORD,
    EMAIL_RECIPIENTS,
    OPENAI_API_KEY
)

app = FastAPI(
    title="Corporate Announcements Processor",
    description="Process corporate announcements and send email reports",
    version="1.0.0"
)

@app.get("/")
async def root():
    """Root endpoint with basic information"""
    return {
        "message": "Corporate Announcements Processor API",
        "version": "1.0.0",
        "endpoints": {
            "/process": "POST - Process announcements and send email report"
        }
    }

@app.post("/process")
async def process_announcements_endpoint(
    test_mode: bool = False,
    use_sample_data: bool = False,
    cookie_header: Optional[str] = None
):
    """
    Process corporate announcements and send email report
    
    Args:
        test_mode: If True, only process first 3 documents (default: False)
        use_sample_data: If True, use sample HTML data instead of fetching from web (default: False)
        cookie_header: Optional cookie header for authentication
        
    Returns:
        JSON response with processing results
    """
    
    # Check if OpenAI API key is set
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=500, 
            detail="OpenAI API key not configured. Please set OPENAI_API_KEY in environment variables."
        )
    
    # Check if email configuration is set
    if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECIPIENTS:
        raise HTTPException(
            status_code=500,
            detail="Email configuration not set. Please configure EMAIL_SENDER, EMAIL_PASSWORD, and EMAIL_RECIPIENTS in environment variables."
        )
    
    try:
        # Get cookie header from environment or parameter (same as original script)
        env_cookie_header = os.getenv("SCREENER_COOKIE_HEADER")
        final_cookie_header = cookie_header if cookie_header else env_cookie_header
        
        print(f"🚀 Starting announcement processing...")
        print(f"   Test Mode: {test_mode}")
        print(f"   Sample Data: {use_sample_data}")
        print(f"   Cookie Header: {'Set' if final_cookie_header else 'Not set'}")
        if final_cookie_header:
            print(f"   Cookie Source: {'Parameter' if cookie_header else 'Environment'}")
        
        # Process announcements
        start_time = time.time()
        new_summaries = process_announcements(
            cookie_header=final_cookie_header,
            test_mode=test_mode,
            use_sample_data=use_sample_data
        )
        processing_time = time.time() - start_time
        
        # Prepare response data
        response_data = {
            "success": True,
            "processing_time_seconds": round(processing_time, 2),
            "new_announcements_processed": len(new_summaries) if new_summaries else 0,
            "test_mode": test_mode,
            "sample_data_used": use_sample_data,
            "cookie_header_used": bool(final_cookie_header),
            "cookie_source": "parameter" if cookie_header else "environment" if env_cookie_header else "none",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Send email if new announcements were processed
        if new_summaries and len(new_summaries) > 0:
            print(f"📧 Sending email with {len(new_summaries)} new announcements...")
            
            email_start_time = time.time()
            email_success = send_email_with_pdf(PDF_OUTPUT_FILE)
            email_time = time.time() - email_start_time
            
            response_data.update({
                "email_sent": email_success,
                "email_time_seconds": round(email_time, 2),
                "pdf_filename": PDF_OUTPUT_FILE,
                "recipients": EMAIL_RECIPIENTS
            })
            
            if email_success:
                print(f"✅ Email sent successfully to {len(EMAIL_RECIPIENTS)} recipients")
            else:
                print(f"❌ Failed to send email")
                response_data["email_error"] = "Failed to send email - check email configuration"
        else:
            response_data.update({
                "email_sent": False,
                "email_skipped": True,
                "email_reason": "No new announcements to send"
            })
            print("ℹ️  No new announcements, skipping email")
        
        # Add summary details if available
        if new_summaries:
            response_data["new_announcements"] = [
                {
                    "company": summary.get("company", "Unknown"),
                    "pdf_url": summary.get("pdf_url", ""),
                    "text_length": summary.get("text_length", 0),
                    "model_used": summary.get("model_used", "Unknown")
                }
                for summary in new_summaries
            ]
        
        print(f"✅ Processing completed successfully in {processing_time:.2f} seconds")
        return JSONResponse(content=response_data)
        
    except Exception as e:
        error_message = f"Error processing announcements: {str(e)}"
        print(f"❌ {error_message}")
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": error_message,
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            }
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "openai_configured": bool(OPENAI_API_KEY),
        "email_configured": bool(EMAIL_SENDER and EMAIL_PASSWORD and EMAIL_RECIPIENTS),
        "cookie_configured": bool(os.getenv("SCREENER_COOKIE_HEADER")),
        "cookie_source": "environment" if os.getenv("SCREENER_COOKIE_HEADER") else "none"
    }

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Corporate Announcements Processor API")
    print("=" * 60)
    print("Available endpoints:")
    print("  GET  /           - API information")
    print("  POST /process    - Process announcements and send email")
    print("  GET  /health     - Health check")
    print("=" * 60)
    print("Example usage:")
    print("  curl -X POST 'http://localhost:8000/process'")
    print("  curl -X POST 'http://localhost:8000/process?test_mode=true'")
    print("  curl -X POST 'http://localhost:8000/process?use_sample_data=true'")
    print("  curl -X POST 'http://localhost:8000/process?cookie_header=csrftoken=value;sessionid=value'")
    print("=" * 60)
    print("Note: Cookie header can also be set via SCREENER_COOKIE_HEADER environment variable")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
