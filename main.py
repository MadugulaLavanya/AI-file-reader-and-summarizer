import asyncio
import os
import shutil
import sys
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import tempfile


from groq import Groq
from dotenv import load_dotenv

load_dotenv()

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Environment variable for Groq API Key
# The user needs to supply the key via a .env file or environment variable.
API_KEY = os.environ.get("GROQ_API_KEY", "")
client = None
if API_KEY:
    client = Groq(api_key=API_KEY)


# In Vercel serverless, background processes and ASGI lifespan hooks are unreliable.
# We will spin up the MCP connection cleanly per-request.
app = FastAPI()

# Add CORS Middleware just in case, though we'll serve static files directly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serverless deployment doesn't support writing to an uploads directory persistently.
# RapidAPI also requires a single endpoint. We merge Upload and Summarize here using /tmp/.

@app.post("/api/analyze")
async def analyze_document(
    file: UploadFile = File(...), 
    prompt: str = Form("Summarize this document")
):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY environment variable is not set on the server.")
        
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    # Save to a Vercel-friendly /tmp folder temporarily
    file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(file.file, tmp)
            file_path = tmp.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save temporary file: {str(e)}")

    try:
        # Step 1: Tell the MCP Server to extract text from the PDF tool
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        mcp_script = os.path.join(BASE_DIR, "mcp_server.py")
        
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-u", mcp_script],
            env=os.environ.copy()
        )
        
        # Spin up MCP locally per-request for Vercel 
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print(f"[MCP Client] Calling tool 'extract_text' for {file_path}")
                result = await session.call_tool("extract_text", arguments={"file_path": file_path})
                extracted_text = result.content[0].text
        
        if extracted_text.startswith("Error"):
             raise HTTPException(status_code=500, detail=f"PDF extraction failed via MCP: {extracted_text}")
             
        if not extracted_text.strip():
             raise HTTPException(status_code=400, detail="No readable text found in the PDF.")
             
        # Step 2: Use AI to Summarize the extracted text
        print(f"[AI] Generating summary using Groq... (Extracted {len(extracted_text)} characters)")
        text_preview = extracted_text[:50000] 
        full_prompt = f"{prompt}\n\nDocument Text:\n{text_preview}"
        
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": full_prompt}],
            model="llama-3.3-70b-versatile"
        )
        print("[AI] Summary generated successfully.")
        
        return {"summary": response.choices[0].message.content}
        
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")
    finally:
        # Always clean up the temp file to stay under Vercel limits
        if os.path.exists(file_path):
            os.remove(file_path)

# Mount static files to serve the frontend UI
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Typically run via: uvicorn main:app --reload
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
