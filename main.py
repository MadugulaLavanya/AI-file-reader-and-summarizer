import asyncio
import os
import shutil
import sys
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

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


# Global variables to hold the MCP client connection
mcp_client = None
mcp_session = None

async def init_mcp():
    global mcp_client, mcp_session
    # Point to the current python executable and the mcp_server.py file
    # We use python -u to unbuffer stdout/stderr which helps with MCP
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-u", "mcp_server.py"],
        env=os.environ.copy()
    )
    
    mcp_client = stdio_client(server_params)
    read, write = await mcp_client.__aenter__()
    
    mcp_session = ClientSession(read, write)
    await mcp_session.__aenter__()
    await mcp_session.initialize()
    print("✓ MCP Server (PDF Reader Tool) initialized and connected.")

async def cleanup_mcp():
    global mcp_client, mcp_session
    if mcp_session:
        await mcp_session.__aexit__(None, None, None)
    if mcp_client:
        await mcp_client.__aexit__(None, None, None)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    print("Starting up application...")
    if not API_KEY:
        print("WARNING: GROQ_API_KEY environment variable is not set. Summarization will fail.")
    try:
        await init_mcp()
    except Exception as e:
        print(f"Error initializing MCP: {e}")
        traceback.print_exc()
    yield
    # Shutdown sequence
    print("Shutting down application...")
    await cleanup_mcp()

app = FastAPI(lifespan=lifespan)

# Add CORS Middleware just in case, though we'll serve static files directly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Upload directory setup
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class SummaryRequest(BaseModel):
    filename: str
    prompt: str = "Summarize this document"

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    # Save the file to the local uploads directory
    file_path = os.path.abspath(os.path.join(UPLOAD_DIR, file.filename))
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
    return {"filename": file.filename, "message": "File uploaded successfully."}

@app.post("/summarize")
async def summarize(request: SummaryRequest):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY environment variable is not set on the server. Please restarting the server with a valid key.")
        
    file_path = os.path.abspath(os.path.join(UPLOAD_DIR, request.filename))
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found. Please upload it first.")
        
    if not mcp_session:
         raise HTTPException(status_code=500, detail="MCP Server is not running. Check server logs.")

    try:
        # Step 1: Tell the MCP Server to extract text from the PDF tool
        print(f"[MCP Client] Calling tool 'extract_text' for {file_path}")
        result = await mcp_session.call_tool("extract_text", arguments={"file_path": file_path})
        
        extracted_text = result.content[0].text
        
        if extracted_text.startswith("Error"):
             raise HTTPException(status_code=500, detail=f"PDF extraction failed via MCP: {extracted_text}")
             
        if not extracted_text.strip():
             raise HTTPException(status_code=400, detail="No readable text found in the PDF.")
             
        # Step 2: Use AI to Summarize the extracted text
        print(f"[AI] Generating summary using Groq... (Extracted {len(extracted_text)} characters)")
        # Limit text length to avoid token limits. Llama models on Groq support up to 128k natively, to be perfectly safe we preview at 50,000
        text_preview = extracted_text[:50000] 
        prompt = f"{request.prompt}\n\nDocument Text:\n{text_preview}"
        
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile"
        )
        print("[AI] Summary generated successfully.")
        
        return {"summary": response.choices[0].message.content}
        
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

# Mount static files to serve the frontend UI
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Typically run via: uvicorn main:app --reload
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
