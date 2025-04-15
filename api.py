from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import base64
import json
from io import BytesIO
import pandas as pd
import requests
from specialized_only import analyze_real_estate_document_json
from standard_only import analyze_real_estate_document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Text to PDF conversion function
def text_to_pdf(text, max_width=170*mm):
    buffer = BytesIO()                      # Create a buffer to hold the PDF
    c = canvas.Canvas(buffer, pagesize=A4)  # Create a canvas for the PDF
    width, height = A4                      # Get the dimensions of the A4 page
    x_margin, y_margin = 20*mm, 20*mm       # Set margins
    y = height - y_margin                   # Start drawing from the top
    c.setFont("Helvetica", 11)              # Set the font for the PDF

    # Function to wrap lines of text to fit within the specified width
    def wrap_line(line, font_name="Helvetica", font_size=11):
        words = line.split()  # Split the line into words
        lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip()  # Test the current line with the new word
            if stringWidth(test_line, font_name, font_size) <= max_width:
                current_line = test_line  # If it fits, add the word to the current line
            else:
                lines.append(current_line)  # If it doesn't fit, save the current line
                current_line = word  # Start a new line with the current word
        if current_line:
            lines.append(current_line)  # Add the last line if it exists
        return lines

    # Iterate through each line of the text
    for raw_line in text.split("\n"):
        wrapped_lines = wrap_line(raw_line)  # Wrap the line to fit the page
        for line in wrapped_lines:
            if y < y_margin:                    # Check if we need to start a new page
                c.showPage()                    # Create a new page
                c.setFont("Helvetica", 11)      # Reset the font
                y = height - y_margin           # Reset the y position
            c.drawString(x_margin, y, line)     # Draw the line on the PDF
            y -= 14                             # Move down for the next line

    c.save()        # Save the PDF to the buffer
    buffer.seek(0)  # Move to the beginning of the buffer
    return buffer   # Return the buffer containing the PDF

@app.post("/analyze")
async def analyze_document(request: dict):
    try:
        # Extract parameters from the request
        pdf_content = request.get("pdf_content")
        checklist_content = request.get("checklist_content")
        api_key = request.get("api_key", "")
        
        if not pdf_content or not checklist_content:
            raise HTTPException(
                status_code=400, 
                detail="Missing required parameters: pdf_content and checklist_content are required"
            )
        
        # Log the request parameters
        print(f"Received analyze request for PDF: {pdf_content}")
        print(f"Checklist content: {checklist_content}")
        print(f"API key provided: {bool(api_key)}")
        
        # Call the specialized analysis function
        result = analyze_real_estate_document_json(
            pdf_content,
            checklist_content,
            api_key
        )
        
        # Call the standard analysis function
        result_summary = analyze_real_estate_document(
            pdf_content,
            checklist_content,
            api_key
        )

        # Check if specialized analysis was successful
        if not result.get("success", False):
            error_msg = result.get("error", "Unknown error in specialized document analysis")
            print(f"Specialized analysis failed: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
            
        # # Check if standard analysis was successful
        if not result_summary.get("success", False):
            error_msg = result_summary.get("error", "Unknown error in standard document analysis")
            print(f"Standard analysis failed: {error_msg}")
            # We'll continue even if standard analysis fails

        print("Analysis completed successfully")
        
        # Return both results
        return {
            "json_output": result.get("json_output", {}),
            "standard_report": result_summary.get("standard_report", "") if result_summary.get("success", False) else ""
        }        
        
    except Exception as e:
        print(f"Error in analyze endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/convert")
async def convert_text_to_pdf(request: Request):
    """
    Endpoint to convert text to PDF
    
    Accepts JSON data with a 'text' field or form data with a 'text' field
    Returns a PDF file for download
    """
    try:
        text = ""
        
        # Check content type to determine how to extract the text
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            # Handle JSON request
            data = await request.json()
            text = data.get("text", "")
        else:
            # Handle form data request
            form_data = await request.form()
            text = form_data.get("text", "")
        
        # Check if text is empty
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")
        
        # Convert text to PDF
        pdf_buffer = text_to_pdf(text)
        
        # Return the PDF as a downloadable file
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=converted.pdf"
            }
        )
    
    except Exception as e:
        print(f"Error in convert endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 