# 📄 AI File Reader and Summarizer (MCP)

This project is an **AI Document Summarizer** that allows users to seamlessly upload PDF files, extract text using a robust reader, and instantly generate AI summaries using Large Language Models. 

It implements the cutting-edge **Model Context Protocol (MCP)** architecture to integrate the PDF parsing logic (PyPDF) securely as a sub-process tool that the main application coordinates.

## 🌟 Key Features
- **Modern UI** - Sleek, dynamic web interface with drag-and-drop capabilities, loaders, and markdown parsing.
- **FastAPI Backend** - High-performance backend routing to manage API calls and document storage.
- **MCP Extracted Tooling** - The PDF Reader runs as a distinct MCP process with standard I/O (StdioServerParameters), completely abstracting the parsing implementation details.
- **Powered by LLMs** - Connected directly to Google Gemini 2.5 Flash to summarize the documents and support custom query prompts.

## 🏗️ Architecture Stack
* **Frontend**: HTML / CSS / Vanilla JavaScript / Marked (for Markdown rendering)
* **Backend Framework**: `FastAPI` + `Uvicorn`
* **MCP Context Layer**: `mcp` Official Python SDK Framework
* **File Parser Engine**: `pypdf`
* **AI Provider**: `google-generativeai`

## 🚀 Quick Setup

### 1. Requirements Setting
Make sure you have `Python 3.10+` installed on your machine.
Clone or navigate to the repository, create a virtual environment, and install all dependencies:
```bash
# Set up a clean environment
python -m venv venv

# Activate it (Windows)
.\venv\Scripts\activate
# Activate it (Mac/Linux)
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
You will need a Gemini API Key to process the document summaries. You can pick one up for free at [Google AI Studio](https://aistudio.google.com/).

Set the key as an environment variable in your terminal:

**Windows (PowerShell)**:
```powershell
$env:GEMINI_API_KEY="your-gemini-api-key-here"
```

**Mac/Linux (Bash)**:
```bash
export GEMINI_API_KEY="your-gemini-api-key-here"
```

### 3. Run the Application
Start the Uvicorn web server. The backend will automatically spawn the required MCP server natively for tool utilization.
```bash
uvicorn main:app --reload
```

### 4. Open in Browser
Visit **[http://127.0.0.1:8000](http://127.0.0.1:8000)** to interact with the web interface. 

---
> *This tool was built collaboratively under the Product Requirements defined in `PRD.md` showcasing architectural separation with the Model Context Protocol.*
