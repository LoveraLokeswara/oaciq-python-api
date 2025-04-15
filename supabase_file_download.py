# from supabase import create_client
# import os
# import requests
# from dotenv import load_dotenv
# import base64   
# import json

# # Load environment variables
# load_dotenv()
# url = os.getenv("SUPABASE_URL")
# key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # or anon key if public bucket

# # Initialize Supabase client
# supabase = create_client(url, key)

# # Get public URL
# # Get the filename from the public URL
# # local_file_path = os.path.join("/Users/a1/Documents/GitHub/da-oaciq-revised-version/python/test", file_name)
# file_name = "20250409110534908_1469e90f-7c25-472e-9130-87c97a67f189.pdf"
# pdf_url = supabase.storage.from_("documents").get_public_url(file_name)

# # local_file_path = os.path.join("/Users/a1/Documents/GitHub/da-oaciq-revised-version/python/test", excel_name)
# excel_name = "formulaires-analyse-vt-(DV).xlsx"
# excel_url = supabase.storage.from_("compliance-files").get_public_url(excel_name)

# # print(public_url)
# # print(excel_url)

# # Construct payload
# payload = {
#     "pdf_content": pdf_url,
#     "checklist_content": excel_url,
#     "api_key": "isi-api-key"
# }

# # Send request
# response = requests.post("http://0.0.0.0:8000/analyze", json=payload)

# # Handle response
# print("Status code:", response.status_code)
# print("Response:", response.json()) 