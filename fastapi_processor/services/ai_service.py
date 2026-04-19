"""
AI Processing Service
Handles: Text extraction from files + OpenAI API calls
Supports: .txt, .pdf, .docx
"""
import os
import io
import aiofiles
from pathlib import Path
from openai import AsyncOpenAI
from config import settings

# Lazy imports for optional file parsers
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from docx import Document as DocxDocument
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False


client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


TASK_PROMPTS = {
    "summarize": (
        "You are a professional document summarizer. "
        "Provide a clear, concise summary of the following document in 3-5 sentences. "
        "Focus on the key points and main takeaways.\n\nDocument:\n{text}"
    ),
    "extract_keywords": (
        "Extract the top 10-15 most important keywords and key phrases from the following document. "
        "Return them as a comma-separated list.\n\nDocument:\n{text}"
    ),
    "sentiment": (
        "Analyze the sentiment of the following document. "
        "Provide: (1) Overall sentiment (Positive/Negative/Neutral/Mixed), "
        "(2) Confidence score (0-100%), (3) Key emotional indicators found.\n\nDocument:\n{text}"
    ),
    "translate": (
        "Translate the following document to English. "
        "If it is already in English, improve its clarity and grammar.\n\nDocument:\n{text}"
    ),
    "qa": (
        "Read the following document carefully and provide: "
        "(1) The main question or problem being addressed, "
        "(2) The answer or solution provided, "
        "(3) Three follow-up questions a reader might have.\n\nDocument:\n{text}"
    ),
}


async def extract_text_from_file(file_path: str, filename: str) -> str:
    """Extract raw text content from uploaded file."""
    ext = Path(filename).suffix.lower()

    if ext == ".txt":
        async with aiofiles.open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return await f.read()

    elif ext == ".pdf":
        if not PDF_SUPPORT:
            raise ValueError("PDF processing not available. Install PyPDF2.")
        async with aiofiles.open(file_path, "rb") as f:
            content = await f.read()
        reader = PyPDF2.PdfReader(io.BytesIO(content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text.strip()

    elif ext in (".docx", ".doc"):
        if not DOCX_SUPPORT:
            raise ValueError("DOCX processing not available. Install python-docx.")
        async with aiofiles.open(file_path, "rb") as f:
            content = await f.read()
        doc = DocxDocument(io.BytesIO(content))
        return "\n".join([para.text for para in doc.paragraphs if para.text]).strip()

    else:
        # Fallback: try to read as plain text
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return await f.read()
        except Exception:
            raise ValueError(f"Unsupported file type: {ext}. Supported: .txt, .pdf, .docx")


async def process_with_ai(text: str, task_type: str) -> str:
    """
    Send extracted text to OpenAI for AI processing.
    Streams the file content to the AI model.
    """
    if not text.strip():
        raise ValueError("File appears to be empty or unreadable.")

    # Truncate to avoid token limits (~12k chars ≈ ~3000 tokens)
    max_chars = 12000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[... document truncated for processing ...]"

    prompt_template = TASK_PROMPTS.get(task_type, TASK_PROMPTS["summarize"])
    prompt = prompt_template.format(text=text)

    response = await client.chat.completions.create(
        model=settings.AI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful AI assistant specialized in document analysis.",
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=1024,
        temperature=0.3,
    )

    return response.choices[0].message.content.strip()


async def run_full_pipeline(file_path: str, filename: str, task_type: str) -> str:
    """
    Full pipeline: Extract text → Send to AI → Return result.
    This is called inside FastAPI BackgroundTasks.
    """
    text = await extract_text_from_file(file_path, filename)
    result = await process_with_ai(text, task_type)
    return result
