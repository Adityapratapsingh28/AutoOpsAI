"""
AutoOps AI — Data Summarizer Tool.

Reads any uploaded file (CSV, XLSX, JSON, TXT, PDF, DOCX, etc.),
extracts a text representation, and uses the Groq LLM to produce
a structured summary. Also powers the "Ask about file" Q&A feature.

This is a lightweight tool — no multi-agent orchestration required.
"""

import os
import logging
from typing import Any, Dict

from .base_tool import BaseTool

logger = logging.getLogger("autoops.tools.data_summarizer")

# Max characters of file content to send to LLM (token budget ~4k)
MAX_CONTENT_CHARS = 12_000


def extract_file_content(file_path: str) -> Dict[str, Any]:
    """Extract text content from any supported file format.

    Returns:
        {"content": str, "format": str, "rows": int|None, "cols": int|None}
    """
    ext = os.path.splitext(file_path)[1].lower()

    # ── CSV / Excel ──
    if ext in (".csv", ".xlsx", ".xls", ".xlsm", ".tsv"):
        try:
            from .csv_tool import read_csv_safe
            df, encoding = read_csv_safe(file_path)

            # Build a text snapshot: column info + sample rows
            lines = []
            lines.append(f"File: {os.path.basename(file_path)}")
            lines.append(f"Format: {'Excel' if ext in ('.xlsx', '.xls', '.xlsm') else 'CSV'}")
            lines.append(f"Rows: {len(df)}, Columns: {len(df.columns)}")
            lines.append(f"Columns: {', '.join(df.columns.tolist())}")
            lines.append(f"Data types: {dict(df.dtypes.astype(str))}")
            lines.append(f"Missing values: {int(df.isnull().sum().sum())}")
            lines.append(f"Duplicate rows: {int(df.duplicated().sum())}")

            # Numeric summary
            numeric = df.select_dtypes(include=["number"])
            if not numeric.empty:
                lines.append(f"\nNumeric Statistics:\n{numeric.describe().to_string()}")

            # Sample rows
            sample_count = min(20, len(df))
            lines.append(f"\nFirst {sample_count} rows:\n{df.head(sample_count).to_string()}")

            return {
                "content": "\n".join(lines),
                "format": "tabular",
                "rows": len(df),
                "cols": len(df.columns),
            }
        except Exception as e:
            logger.warning(f"Could not parse as tabular: {e}")
            # Fall through to text extraction

    # ── JSON ──
    if ext == ".json":
        import json
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            content = json.dumps(data, indent=2)[:MAX_CONTENT_CHARS]
            item_count = len(data) if isinstance(data, list) else None
            return {
                "content": f"File: {os.path.basename(file_path)}\nFormat: JSON\n"
                           + (f"Items: {item_count}\n" if item_count else "")
                           + f"\n{content}",
                "format": "json",
                "rows": item_count,
                "cols": None,
            }
        except Exception as e:
            logger.warning(f"JSON parse failed: {e}")

    # ── PDF ──
    if ext == ".pdf":
        try:
            import subprocess
            # Try pdftotext (poppler) first
            result = subprocess.run(
                ["pdftotext", file_path, "-"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return {
                    "content": f"File: {os.path.basename(file_path)}\nFormat: PDF\n\n"
                               + result.stdout[:MAX_CONTENT_CHARS],
                    "format": "pdf",
                    "rows": None,
                    "cols": None,
                }
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Fallback: try PyPDF2
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            pages = []
            for i, page in enumerate(reader.pages[:20]):  # Cap at 20 pages
                text = page.extract_text()
                if text:
                    pages.append(f"--- Page {i+1} ---\n{text}")
            content = "\n".join(pages)
            return {
                "content": f"File: {os.path.basename(file_path)}\nFormat: PDF ({len(reader.pages)} pages)\n\n"
                           + content[:MAX_CONTENT_CHARS],
                "format": "pdf",
                "rows": None,
                "cols": None,
            }
        except Exception:
            pass

    # ── Plain Text / Markdown / Code ──
    text_exts = {".txt", ".md", ".log", ".py", ".js", ".html", ".css",
                 ".yaml", ".yml", ".xml", ".ini", ".cfg", ".toml", ".env", ".sh"}
    if ext in text_exts or ext == "":
        try:
            encodings = ["utf-8", "latin-1", "cp1252"]
            for enc in encodings:
                try:
                    with open(file_path, "r", encoding=enc) as f:
                        content = f.read(MAX_CONTENT_CHARS)
                    line_count = content.count("\n") + 1
                    return {
                        "content": f"File: {os.path.basename(file_path)}\nFormat: Text ({ext or 'plain'})\n"
                                   f"Lines: {line_count}\n\n{content}",
                        "format": "text",
                        "rows": line_count,
                        "cols": None,
                    }
                except UnicodeDecodeError:
                    continue
        except Exception:
            pass

    # ── DOCX ──
    if ext == ".docx":
        try:
            from docx import Document
            doc = Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            content = "\n".join(paragraphs)
            return {
                "content": f"File: {os.path.basename(file_path)}\nFormat: Word Document\n"
                           f"Paragraphs: {len(paragraphs)}\n\n{content[:MAX_CONTENT_CHARS]}",
                "format": "docx",
                "rows": None,
                "cols": None,
            }
        except Exception:
            pass

    # ── Fallback: try reading as text ──
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(MAX_CONTENT_CHARS)
        return {
            "content": f"File: {os.path.basename(file_path)}\nFormat: Unknown ({ext})\n\n{content}",
            "format": "unknown",
            "rows": None,
            "cols": None,
        }
    except Exception:
        return {
            "content": f"File: {os.path.basename(file_path)}\nFormat: Binary ({ext})\n\n[Cannot extract text from this file format]",
            "format": "binary",
            "rows": None,
            "cols": None,
        }


def _call_groq_llm(system_prompt: str, user_prompt: str) -> str:
    """Call Groq LLM for summarization/Q&A."""
    import httpx
    from ..core.config import settings

    if not settings.GROQ_API_KEY:
        return "[LLM unavailable — GROQ_API_KEY not configured]"

    try:
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 2048,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Groq LLM call failed: {e}")
        return f"[LLM error: {e}]"


class DataSummarizerTool(BaseTool):
    name = "data_summarizer_tool"
    description = "Summarizes any file format using LLM — CSV, Excel, JSON, TXT, PDF, etc."

    def run(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Summarize an uploaded file.

        input_data:
            - file_path: Path to the file
            - llm_summary: Agent's reasoning summary
            - input_text: User's prompt
        """
        file_path = input_data.get("file_path", "")

        if not file_path or not os.path.exists(file_path):
            return {"status": "failed", "error": f"File not found: {file_path}"}

        try:
            # 1. Extract file content
            extracted = extract_file_content(file_path)
            content = extracted["content"][:MAX_CONTENT_CHARS]

            # 2. Send to LLM for summary
            system_prompt = """You are a data analyst assistant. Analyze the provided file data and generate a clear, structured summary. Include:
1. **Overview**: What the file contains and its purpose
2. **Key Statistics**: Row count, column count, data types, missing values
3. **Data Insights**: Patterns, distributions, notable values, outliers
4. **Recommendations**: What actions could be taken with this data

Be concise but thorough. Use bullet points and sections."""

            user_prompt = f"Summarize this file data:\n\n{content}"

            llm_summary = _call_groq_llm(system_prompt, user_prompt)

            return {
                "status": "completed",
                "message": f"File summarized: {os.path.basename(file_path)}",
                "summary": llm_summary,
                "file_info": {
                    "name": os.path.basename(file_path),
                    "format": extracted["format"],
                    "rows": extracted.get("rows"),
                    "cols": extracted.get("cols"),
                },
            }

        except Exception as e:
            logger.error(f"Data summarizer failed: {e}", exc_info=True)
            return {"status": "failed", "error": str(e)}


def ask_about_file(file_path: str, question: str) -> Dict[str, Any]:
    """Standalone function for the /files/{id}/ask endpoint.

    Reads the file, sends content + question to LLM, returns answer.
    """
    if not file_path or not os.path.exists(file_path):
        return {"status": "failed", "error": f"File not found: {file_path}"}

    try:
        extracted = extract_file_content(file_path)
        content = extracted["content"][:MAX_CONTENT_CHARS]

        system_prompt = """You are a helpful data assistant. The user has uploaded a file and wants to ask questions about it. 
Answer based ONLY on the actual data provided. If the answer is not in the data, say so.
Be precise and cite specific values from the data when possible."""

        user_prompt = f"File data:\n{content}\n\n---\nUser question: {question}"

        answer = _call_groq_llm(system_prompt, user_prompt)

        return {
            "status": "completed",
            "answer": answer,
            "file_info": {
                "name": os.path.basename(file_path),
                "format": extracted["format"],
            },
        }
    except Exception as e:
        logger.error(f"Ask about file failed: {e}")
        return {"status": "failed", "error": str(e)}
