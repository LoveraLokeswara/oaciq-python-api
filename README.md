# OACIQ Python API

This repository contains a FastAPI implementation for analyzing real estate documents against compliance checklists. The API offers two types of analyses:

1. **Specialized Analysis**: Provides detailed information in JSON format
2. **Standard Analysis**: Provides a text report with compliance information

## Setup

1. Clone this repository:
```bash
git clone https://github.com/yourusername/oaciq-python-api.git
cd oaciq-python-api
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Create a `.env` file with your API keys:
```
OPENROUTER_API_KEY=your_openrouter_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

## Running the API

Start the API server:
```bash
python api.py
```

The API will be available at http://localhost:8000

## API Endpoints

### 1. Analyze Document - POST /analyze

#### Request:
```json
{
  "pdf_content": "URL_or_base64_encoded_PDF_content",
  "checklist_content": "URL_or_base64_encoded_Excel_content",
  "api_key": "your_openrouter_api_key"
}
```

#### Response:
```json
{
  "json_output": {
    "summary": "Summary of the analysis",
    "recommended_actions": [
      {
        "section": "Section identifier",
        "action_required": "Action to take",
        "priority": "Priority level",
        "timeline": "Timeline for action"
      }
    ],
    "warnings": [
      {
        "risk_level": "Risk level",
        "issue": "Issue description",
        "potential_consequences": "Potential consequences",
        "mitigation": "Mitigation approach"
      }
    ],
    "vendor": "Vendor name",
    "buyers": "Buyer names",
    "date": "Document date",
    "property_type": "Property type",
    "overall_score": "Overall score"
  },
  "standard_report": "Detailed text report of the analysis"
}
```

### 2. Convert Text to PDF - POST /convert

#### Request:
```json
{
  "text": "Text to convert to PDF"
}
```

#### Response:
A downloadable PDF file.

### 3. Health Check - GET /health

Returns the status of the API.

#### Response:
```json
{
  "status": "ok"
}
```

## Testing

You can use the included `supabase_file_download.py` script to test the API with files stored in a Supabase bucket.

## License

This project is proprietary and confidential. 