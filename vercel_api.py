from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# URL of your full API hosted elsewhere (could be a cloud VM, Heroku, etc.)
PROCESSING_API_URL = os.getenv("PROCESSING_API_URL", "https://your-full-api-url.com")

@app.post("/analyze")
async def analyze_document(request: dict):
    """
    Proxy endpoint that forwards requests to the full API implementation
    """
    try:
        # Forward the request to the full API
        response = requests.post(f"{PROCESSING_API_URL}/analyze", json=request)
        
        # Check if the request was successful
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        # Return the response from the full API
        return response.json()
        
    except Exception as e:
        # Handle errors
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/convert")
async def convert_text_to_pdf(request: Request):
    """
    Proxy endpoint that forwards requests to the full API implementation
    """
    try:
        # Get the raw request body
        body = await request.body()
        
        # Get the content type
        content_type = request.headers.get("content-type", "")
        
        # Forward the request to the full API
        response = requests.post(
            f"{PROCESSING_API_URL}/convert", 
            data=body,
            headers={"Content-Type": content_type}
        )
        
        # Check if the request was successful
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        # Return the response from the full API
        return Response(
            content=response.content,
            media_type=response.headers.get("Content-Type", "application/pdf"),
            headers=dict(response.headers)
        )
        
    except Exception as e:
        # Handle errors
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "ok", "vercel": True}

# This is required for Vercel deployment
# The app object needs to be directly accessible at the module level 