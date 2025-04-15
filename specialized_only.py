import os
import fitz  # PyMuPDF for PDF handling
import pandas as pd
from dotenv import load_dotenv
import requests
import json
from io import BytesIO
from datetime import datetime
import re

# Load API key from environment variables
load_dotenv()
MODEL = "google/gemini-2.0-flash-001"  # Model to be used for API calls

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

# Function to parse the specialized report into JSON format
def parse_specialized_report_to_json(report_text):
    """
    Parse the specialized report into a structured JSON format with summary, 
    recommended_actions, and warnings sections
    
    Args:
        report_text (str): The specialized report text from the AI
        
    Returns:
        dict: A structured dictionary with the parsed content
    """
    result = {
        "summary": "",
        "recommended_actions": [],
        "warnings": [],
        "vendor": "",
        "buyers": "",
        "date": "",
        "property_type": "",
        "overall_score": ""
    }
    
    # Extract document overview and summary
    summary_match = re.search(r'## (?:Évaluation Sommaire|Summary Evaluation|Résumé de l\'Analyse)\s*(.*?)(?=##|\Z)', report_text, re.DOTALL)
    if summary_match:
        result["summary"] = summary_match.group(1).strip()
        
        # Extract buyer information from summary if present
        buyers_match = re.search(r"acheteurs? (.*?)(?:est|sont) (.*?)\.?$", result["summary"], re.IGNORECASE | re.MULTILINE)
        if buyers_match:
            result["buyers"] = buyers_match.group(2).strip()
        else:
            # Alternative pattern to find buyers in the summary
            buyers_match = re.search(r"celle des acheteurs (.*?)(?:est|sont)? (.*?)\.?$", result["summary"], re.IGNORECASE | re.MULTILINE)
            if buyers_match:
                result["buyers"] = buyers_match.group(1).strip()
            else:
                # Try one more pattern
                buyers_match = re.search(r"acheteurs? (.*?)\.?$", result["summary"], re.IGNORECASE | re.MULTILINE)
                if buyers_match:
                    result["buyers"] = buyers_match.group(1).strip()
    
    # Extract recommended actions - handle both English and French headers
    actions_section = re.search(r'## (?:RECOMMANDATIONS|RECOMMENDED ACTIONS|Actions Recommandées)(.*?)(?=##|\Z)', report_text, re.DOTALL)
    if actions_section and actions_section.group(1):
        actions_text = actions_section.group(1)
        
        # Find all actions with the proper pattern
        action_patterns = re.finditer(r'\*\*Section\*\*:\s*(.*?)\s*\*\*Action Requise\*\*:\s*(.*?)\s*\*\*Priorité\*\*:\s*(.*?)\s*\*\*(?:Échéancier|Délai)\*\*:\s*(.*?)(?=\n\n\*\*Section|\n\n##|\Z)',
                                    actions_text, re.DOTALL)
        
        for match in action_patterns:
            action = {
                "section": match.group(1).strip(),
                "action_required": match.group(2).strip(),
                "priority": match.group(3).strip(),
                "timeline": match.group(4).strip()
            }
            result["recommended_actions"].append(action)
            
        # If no actions found with the pattern above, try alternative pattern
        if not result["recommended_actions"]:
            action_patterns = re.finditer(r'(?:\*\*)?Section(?:\*\*)?\s*:\s*(.*?)\s*(?:\*\*)?Action (?:Requise|Required)(?:\*\*)?\s*:\s*(.*?)\s*(?:\*\*)?(?:Priorité|Priority)(?:\*\*)?\s*:\s*(.*?)\s*(?:\*\*)?(?:Échéancier|Délai|Timeline)(?:\*\*)?\s*:\s*(.*?)(?=\n\n(?:\*\*)?Section|\n\n##|\Z)',
                                         actions_text, re.DOTALL)
            
            for match in action_patterns:
                action = {
                    "section": match.group(1).strip(),
                    "action_required": match.group(2).strip(),
                    "priority": match.group(3).strip(),
                    "timeline": match.group(4).strip()
                }
                result["recommended_actions"].append(action)
    
    # Extract warnings - handle both English and French headers
    warnings_section = re.search(r'## (?:AVERTISSEMENTS|WARNINGS|Avertissements)(.*?)(?=##|\Z)', report_text, re.DOTALL)
    if warnings_section:
        warnings_text = warnings_section.group(1)
        
        # Find all warnings with the proper pattern
        warning_patterns = re.finditer(r'\*\*(?:Niveau de Risque|Risque Level)\*\*:\s*(.*?)\s*\*\*(?:Problème|Issue)\*\*:\s*(.*?)\s*\*\*(?:Conséquences Potentielles|Potential Consequences)\*\*:\s*(.*?)\s*\*\*(?:Atténuation|Mitigation)\*\*:\s*(.*?)(?=\n\n\*\*(?:Niveau de Risque|Risque Level)|\n\n##|\Z)',
                                     warnings_text, re.DOTALL)
        
        for match in warning_patterns:
            warning = {
                "risk_level": match.group(1).strip(),
                "issue": match.group(2).strip(),
                "potential_consequences": match.group(3).strip(),
                "mitigation": match.group(4).strip()
            }
            result["warnings"].append(warning)
            
        # If no warnings found with the pattern above, try alternative pattern
        if not result["warnings"]:
            warning_patterns = re.finditer(r'(?:\*\*)?(?:Niveau de Risque|Risque Level)(?:\*\*)?\s*:\s*(.*?)\s*(?:\*\*)?(?:Problème|Issue)(?:\*\*)?\s*:\s*(.*?)\s*(?:\*\*)?(?:Conséquences Potentielles|Potential Consequences)(?:\*\*)?\s*:\s*(.*?)\s*(?:\*\*)?(?:Atténuation|Mitigation)(?:\*\*)?\s*:\s*(.*?)(?=\n\n(?:\*\*)?(?:Niveau de Risque|Risque Level)|\n\n##|\Z)',
                                         warnings_text, re.DOTALL)
            
            for match in warning_patterns:
                warning = {
                    "risk_level": match.group(1).strip(),
                    "issue": match.group(2).strip(),
                    "potential_consequences": match.group(3).strip(),
                    "mitigation": match.group(4).strip()
                }
                result["warnings"].append(warning)
    
    # Add overview information - handle both English and French
    overview_section = re.search(r'## (?:Aperçu du Document|Document Overview)(.*?)(?=##|\Z)', report_text, re.DOTALL)
    if overview_section:
        overview_text = overview_section.group(1)
        
        # Extract vendor names
        vendor_match = re.search(r'\*\*(?:Vendeur\(s\)|Vendor\(s\))\*\*:\s*(.*?)(?=\n\-|\Z)', overview_text, re.DOTALL)
        if vendor_match:
            result["vendor"] = vendor_match.group(1).strip()
        
        # Extract date
        date_match = re.search(r'\*\*Date\*\*:\s*(.*?)(?=\n\-|\Z)', overview_text, re.DOTALL)
        if date_match:
            result["date"] = date_match.group(1).strip()
        
        # Extract property type
        property_match = re.search(r'\*\*(?:Type de Propriété|Property Type)\*\*:\s*(.*?)(?=\n\-|\Z)', overview_text, re.DOTALL)
        if property_match:
            result["property_type"] = property_match.group(1).strip()
        
        # Extract overall score
        score_match = re.search(r'\*\*(?:Score Global|Overall Score)\*\*:\s*(.*?)%', overview_text)
        if score_match:
            result["overall_score"] = score_match.group(1).strip()
    
    return result

def analyze_real_estate_document_json(pdf_file_content, checklist_file_content, api_key=None):
    """
    Analyze a real estate document and output only the specialized analysis in JSON format
    
    Args:
        pdf_file_content (bytes or str): Content of the PDF file to analyze or URL to the PDF
        checklist_file_content (bytes or str): Content of the Excel checklist file or URL to the Excel file
        api_key (str, optional): API key for OpenRouter. Defaults to environment variable.
        
    Returns:
        dict: A dictionary containing:
            - json_output (dict): The specialized analysis in JSON format
            - success (bool): Whether the analysis was successful
    """
    try:
        # print(f"Starting analysis. PDF type: {type(pdf_file_content)}, Checklist type: {type(checklist_file_content)}")
        
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
        
        # Define specialized prompt
        specialized_prompt = """<Instruction> You are an expert real estate assistant specializing in form validation and compliance analysis. Your task is to analyze a "Déclarations du vendeur" (DV) form based on a detailed validation table that outlines expected responses, required documents, and critical checks for each section (DV1 to DV16).  The first pdf document is the report to analyze. The second xlsx document is the validation table/checklist that provides the criteria for analysis.  You must: Evaluate conformity of each section (DV1 to DV16) by comparing the form content with the validation table.  Find also the name of the person who's selling and who's buying the estate in the signature part. Identify issues and provide specialized guidance formatted specifically in two key areas: 1. Recommended Actions - Specific steps to take to resolve issues 2. Warnings - Critical issues that need immediate attention  </Instruction>  Format your output in the following specialized format: # RAPPORT D'ANALYSE: [form number]  </br> ## Aperçu du Document - **Vendeur(s)**: [Names] - **Date**: [Date] - **Type de Propriété**: [Type] - **Score Global**: [score]%  </br> ## Actions Recommandées **Section**: [Section] **Action Requise**: [Specific action] **Priorité**: [High/Medium/Low] **Échéancier**: [Immediate/Within X days]</br> </br>  ## Avertissements **Risque Level**: [Critical/High/Medium] **Issue**: [Issue description] **Conséquences Potentielles**: [Consequences] **Atténuation**: [Mitigation approach]</br> </br>  ## Résumé de l\'Analyse [Brief summary paragraph with overall assessment]
    Give the output in French language only!!
    """
        
        # Full prompt with analysis data
        full_prompt = specialized_prompt + f"""\n\n Analyse:{pdf_text} \n\n Using: {checklist}"""
        
        print("Sending prompt to AI service...")
        
        # Call the AI agent for specialized report
        specialized_report = call_agent(full_prompt, api_key=api_key)
        
        print(f"Received AI response, length: {len(specialized_report)} characters")
        print(specialized_report)
        
        # Convert specialized report to JSON structure
        json_output = parse_specialized_report_to_json(specialized_report)
        print(json_output)
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Return the results in format expected by API
        return {
            "json_output": json_output,
            "timestamp": timestamp,
            "success": True
        }
        
    except Exception as e:
        print(f"Error analyzing document: {str(e)}")
        return {
            "error": str(e),
            "success": False,
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
        } 