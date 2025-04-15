import os
import fitz  # PyMuPDF for PDF handling
import pandas as pd
from dotenv import load_dotenv
import requests
import json
from io import BytesIO
# from reportlab.lib.pagesizes import A4
# from reportlab.pdfgen import canvas
# from reportlab.lib.units import mm
# from reportlab.pdfbase.pdfmetrics import stringWidth
from datetime import datetime

# Load API key from environment variables
load_dotenv()
# MODEL = "anthropic/claude-3.7-sonnet"  # Model to be used for API calls
MODEL = "google/gemini-2.0-flash-001" 

# Function to download content from a URL
def download_from_url(url):
    """
    Download content from a URL
    
    Args:
        url (str): URL to download content from
        
    Returns:
        bytes: Downloaded content
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.content
    except Exception as e:
        print(f"Error downloading from {url}: {str(e)}")
        raise Exception(f"Failed to download content from URL: {str(e)}")

# Function to extract text from a PDF file
def extract_pdf_text(file_content):
    """
    Extract text from PDF content
    
    Args:
        file_content (bytes or str): Either PDF file content as bytes or URL to PDF
        
    Returns:
        str: Extracted text from the PDF
    """
    # If file_content is a URL, download the content
    if isinstance(file_content, str) and (file_content.startswith('http://') or file_content.startswith('https://')):
        file_content = download_from_url(file_content)
        
    doc = fitz.open(stream=file_content, filetype="pdf")  # Open the PDF file
    text = ""
    for page in doc:  # Iterate through each page
        text += page.get_text()  # Extract text from the page
    return text.lower().replace("\n", " ").replace("  ", " ")  # Clean up the text

# Function to call the Claude AI agent with a prompt
def call_agent(prompt, model=MODEL, api_key=None):
    
    if not api_key:
        raise Exception("No API key provided for AI service")
        
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://yourapplication.com/",  # Update with your application's URL
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}]
    }

    # Make a POST request to the AI API
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        data=json.dumps(payload)  # Convert payload to JSON
    )

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]  # Return the AI's response
    else:
        error_message = f"Error: {response.status_code}, {response.text}"
        print(error_message)  # Log error
        raise Exception(f"API call failed: {error_message}")

# # Function to convert text to a PDF using ReportLab
# def text_to_pdf(text, max_width=170*mm):
#     buffer = BytesIO()                      # Create a buffer to hold the PDF
#     c = canvas.Canvas(buffer, pagesize=A4)  # Create a canvas for the PDF
#     width, height = A4                      # Get the dimensions of the A4 page
#     x_margin, y_margin = 20*mm, 20*mm       # Set margins
#     y = height - y_margin                   # Start drawing from the top
#     c.setFont("Helvetica", 11)              # Set the font for the PDF

#     # Function to wrap lines of text to fit within the specified width
#     def wrap_line(line, font_name="Helvetica", font_size=11):
#         words = line.split()  # Split the line into words
#         lines = []
#         current_line = ""
#         for word in words:
#             test_line = f"{current_line} {word}".strip()  # Test the current line with the new word
#             if stringWidth(test_line, font_name, font_size) <= max_width:
#                 current_line = test_line  # If it fits, add the word to the current line
#             else:
#                 lines.append(current_line)  # If it doesn't fit, save the current line
#                 current_line = word  # Start a new line with the current word
#         if current_line:
#             lines.append(current_line)  # Add the last line if it exists
#         return lines

#     # Iterate through each line of the text
#     for raw_line in text.split("\n"):
#         wrapped_lines = wrap_line(raw_line)  # Wrap the line to fit the page
#         for line in wrapped_lines:
#             if y < y_margin:                    # Check if we need to start a new page
#                 c.showPage()                    # Create a new page
#                 c.setFont("Helvetica", 11)      # Reset the font
#                 y = height - y_margin           # Reset the y position
#             c.drawString(x_margin, y, line)     # Draw the line on the PDF
#             y -= 14                             # Move down for the next line

#     c.save()        # Save the PDF to the buffer
#     buffer.seek(0)  # Move to the beginning of the buffer
#     return buffer   # Return the buffer containing the PDF

def analyze_real_estate_document(pdf_file_content, checklist_file_content, api_key=None):
    """
    Analyze a real estate document against a compliance checklist and provide only standard report
    
    Args:
        pdf_file_content (bytes or str): Content of the PDF file to analyze or URL to the PDF
        checklist_file_content (bytes or str): Content of the Excel checklist file or URL to the Excel file
        api_key (str, optional): API key for OpenRouter. Defaults to environment variable.
        
    Returns:
        dict: A dictionary containing the standard report as a string and success status
    """
    try:
        print(f"Starting standard analysis. PDF type: {type(pdf_file_content)}, Checklist type: {type(checklist_file_content)}")
        
        # Extract text from the PDF (URL or content)
        pdf_text = extract_pdf_text(pdf_file_content)
        print(f"PDF text extracted, length: {len(pdf_text)} characters")
        
        # Process the checklist file (URL or content)
        if isinstance(checklist_file_content, str) and (checklist_file_content.startswith('http://') or checklist_file_content.startswith('https://')):
            checklist_content = download_from_url(checklist_file_content)
            checklist_buffer = BytesIO(checklist_content)
        else:
            checklist_buffer = BytesIO(checklist_file_content)
        
        # Read the checklist from the Excel file
        try:
            checklist = pd.read_excel(checklist_buffer)
            print(f"Checklist loaded, shape: {checklist.shape}")
        except Exception as e:
            print(f"Error reading Excel file: {str(e)}")
            raise Exception(f"Failed to read Excel checklist: {str(e)}")
        
        results = []  # List to hold analysis results
        for index, row in checklist.iterrows():  # Iterate through each row in the checklist
            clause_id = row["Code form."]  # Get clause ID
            clause_name = row["Nom de la clause"]  # Get clause name
            validations = str(row["Éléments de validation"])  # Get validation elements

            status = "✅ Conforme"  # Default status
            missing = []  # List to hold missing items

            for point in validations.split("-"):  # Check each validation point
                point = point.strip().lower()  # Clean up the point
                if point and point not in pdf_text:  # Check if the point is missing in the PDF text
                    status = "🟡 Partiellement conforme"  # Update status if partially compliant
                    missing.append(point)  # Add missing point to the list

            if any("rapport" in m for m in missing):  # Check for specific missing items
                status = "🔴 Non conforme"  # Update status if non-compliant

            # Append the result for this clause
            results.append(f"### {clause_id} - {clause_name}\nStatus: {status}\nMissing: {', '.join(missing) if missing else 'None'}\n")

        standard_analysis = "".join(results)  # Combine results into a single string
        print("Completed standard initial analysis")

        # Prompts for AI analysis
        std_prompt = """
        <Instruction>
        You are an expert real estate assistant specializing in form validation and compliance analysis. Your task is to analyze a "Déclarations du vendeur" (DV) form based on a detailed validation table that outlines expected responses, required documents, and critical checks for each section (DV1 to DV16).

        The first pdf document is the report to analyze. The second xlsx document is the validation table/checklist that provides the criteria for analysis.

        You must:
        Evaluate conformity of each section (DV1 to DV16) by comparing the form content with the validation table.

        Identify:
        ✅ Conforming elements (complete, clear, and documented)
        🟡 Partial elements (missing minor info, ambiguous, incomplete)
        🔴 Critical non-conformities (missing required documentation or information that creates risk)

        Give a conformity score as a percentage based on overall completeness and correctness.
        </Instruction>

        Format your output as follows:
        DV [form number] : [score]% Voici l'évaluation complète du formulaire "Déclarations du vendeur" (DV) de [NOM VENDEUR(S)], daté du [DATE], pour un immeuble résidentiel de moins de 5 logements.

        1. SCORE DE CONFORMITÉ GÉNÉRAL : [score]% – [niveau de conformité : Conforme, Conforme avec points à bonifier, Non conforme]
        Résumé de l'état général du document (structure, signatures, etc.).

        2. ÉLÉMENTS CONFORMES :
        Section
        Détails conformes
        (List each conforming DV section with relevant details.)

        3. OBSERVATIONS / POINTS À BONIFIER
        Section
        Problème détecté
        Recommandation
        (List each partially conforming section, what's missing, and how to fix it.)

        4. POINTS À CORRIGER POUR ÉVITER RISQUES :
        Section
        Risque identifié
        Action immédiate
        (List critical issues and what must be corrected.)

        5. RECOMMANDATIONS À L'AGENCE / COURTIER
        (Add specific recommendations for the agency or broker based on observed patterns or recurring mistakes.)

        6. CONCLUSION
        (Summarize if the form is valid, under what conditions, and what documents must be urgently provided.)

        Important Notes for Evaluation:
        Use section D15 for details if "oui" is checked elsewhere.
        Require Annexe G where applicable (for technical/maintenance details).
        Require original or attached documents (e.g. inspection reports, invoices).
        A missing signature or D15 clarification on a critical item may invalidate the form.        
        """

        # Prepare prompt for the AI
        standard_prompt = std_prompt + f"""\n\n Analyse:{standard_analysis} \n\n Using:{checklist}"""
        print("Sending prompt to AI std service...")

        standard_report = call_agent(standard_prompt, api_key=api_key)  # Get standard report
        print(f"Received AI response, length: {len(standard_report)} characters")
        
        # Return the final result with success status
        return {
            "standard_report": standard_report,
            "success": True,
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
        }
        
    except Exception as e:
        print(f"Error in standard analysis: {str(e)}")
        return {
            "error": str(e),
            "standard_report": None,
            "success": False,
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
        } 