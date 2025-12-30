"""
File parsers for various document formats.
Supports: .txt, .md, .pdf, .xls, .xlsx, .csv, .doc, .docx
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
import io

logger = logging.getLogger(__name__)


def parse_text_file(file_path: str) -> str:
    """
    Parse plain text file.
    
    Args:
        file_path: Path to the text file
    
    Returns:
        File content as string
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # Try with different encoding
        with open(file_path, 'r', encoding='latin-1') as f:
            return f.read()


def parse_markdown_file(file_path: str) -> str:
    """
    Parse markdown file.
    
    Args:
        file_path: Path to the markdown file
    
    Returns:
        File content as string
    """
    return parse_text_file(file_path)


def parse_pdf_file(file_path: str) -> str:
    """
    Parse PDF file and extract text.
    
    Args:
        file_path: Path to the PDF file
    
    Returns:
        Extracted text content
    """
    try:
        import pdfplumber
        
        text_content = []
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    text_content.append(f"--- Page {page_num} ---\n{text}")
        
        return "\n\n".join(text_content)
    
    except ImportError:
        logger.error("pdfplumber not installed. Install with: pip install pdfplumber")
        raise ImportError("PDF parsing requires pdfplumber. Install with: pip install pdfplumber")
    except Exception as e:
        logger.error(f"Failed to parse PDF {file_path}: {e}")
        raise


def parse_excel_file(file_path: str) -> str:
    """
    Parse Excel file (.xls, .xlsx) and convert to text.
    
    Args:
        file_path: Path to the Excel file
    
    Returns:
        Formatted text representation of Excel data
    """
    try:
        import pandas as pd
        
        # Read all sheets
        excel_file = pd.ExcelFile(file_path)
        text_content = []
        
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            text_content.append(f"=== Sheet: {sheet_name} ===\n")
            
            # Convert DataFrame to formatted string
            # Option 1: CSV-like format
            text_content.append(df.to_csv(index=False, sep='\t'))
            
            # Option 2: More readable format
            # text_content.append(df.to_string(index=False))
            
            text_content.append("\n")
        
        return "\n".join(text_content)
    
    except ImportError:
        logger.error("pandas and openpyxl not installed. Install with: pip install pandas openpyxl")
        raise ImportError("Excel parsing requires pandas and openpyxl. Install with: pip install pandas openpyxl")
    except Exception as e:
        logger.error(f"Failed to parse Excel {file_path}: {e}")
        raise


def parse_csv_file(file_path: str) -> str:
    """
    Parse CSV file and convert to text.
    
    Args:
        file_path: Path to the CSV file
    
    Returns:
        Formatted text representation of CSV data
    """
    try:
        import pandas as pd
        
        # Read CSV
        df = pd.read_csv(file_path)
        
        # Convert to formatted string
        text_content = [f"=== CSV File: {Path(file_path).name} ===\n"]
        text_content.append(f"Rows: {len(df)}, Columns: {len(df.columns)}\n")
        text_content.append(f"Columns: {', '.join(df.columns)}\n\n")
        
        # Add data
        text_content.append(df.to_string(index=False))
        
        return "\n".join(text_content)
    
    except ImportError:
        logger.error("pandas not installed. Install with: pip install pandas")
        raise ImportError("CSV parsing requires pandas. Install with: pip install pandas")
    except Exception as e:
        logger.error(f"Failed to parse CSV {file_path}: {e}")
        raise


def parse_word_file(file_path: str) -> str:
    """
    Parse Word document (.docx) and extract text.
    
    Args:
        file_path: Path to the Word document
    
    Returns:
        Extracted text content
    """
    try:
        from docx import Document
        
        doc = Document(file_path)
        text_content = []
        
        # Extract paragraphs
        for para in doc.paragraphs:
            if para.text.strip():
                text_content.append(para.text)
        
        # Extract tables
        for table_num, table in enumerate(doc.tables, 1):
            text_content.append(f"\n--- Table {table_num} ---\n")
            for row in table.rows:
                row_text = []
                for cell in row.cells:
                    row_text.append(cell.text.strip())
                text_content.append("\t".join(row_text))
            text_content.append("")
        
        return "\n".join(text_content)
    
    except ImportError:
        logger.error("python-docx not installed. Install with: pip install python-docx")
        raise ImportError("Word document parsing requires python-docx. Install with: pip install python-docx")
    except Exception as e:
        logger.error(f"Failed to parse Word document {file_path}: {e}")
        raise


def parse_old_word_file(file_path: str) -> str:
    """
    Parse old Word document (.doc) and extract text.
    Note: .doc files require additional libraries like antiword or LibreOffice.
    This is a fallback that tries to extract what it can.
    
    Args:
        file_path: Path to the .doc file
    
    Returns:
        Extracted text content
    """
    try:
        # Try using python-docx2txt or textract
        try:
            import docx2txt
            return docx2txt.process(file_path)
        except ImportError:
            pass
        
        try:
            import textract
            return textract.process(file_path).decode('utf-8')
        except ImportError:
            pass
        
        # If neither is available, try antiword command (Linux)
        import subprocess
        try:
            result = subprocess.run(
                ['antiword', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Last resort: try LibreOffice conversion
        try:
            import subprocess
            import tempfile
            import os
            
            with tempfile.TemporaryDirectory() as tmpdir:
                output_file = os.path.join(tmpdir, 'converted.txt')
                result = subprocess.run(
                    ['libreoffice', '--headless', '--convert-to', 'txt', '--outdir', tmpdir, file_path],
                    capture_output=True,
                    timeout=60
                )
                if result.returncode == 0 and os.path.exists(output_file):
                    with open(output_file, 'r', encoding='utf-8') as f:
                        return f.read()
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass
        
        raise ImportError(
            "No suitable library found for .doc files. Options:\n"
            "1. Install python-docx2txt: pip install docx2txt\n"
            "2. Install textract: pip install textract\n"
            "3. Install antiword (Linux): sudo apt-get install antiword\n"
            "4. Install LibreOffice: sudo apt-get install libreoffice\n"
            "5. Convert .doc to .docx manually"
        )
    
    except Exception as e:
        logger.error(f"Failed to parse old Word document {file_path}: {e}")
        raise


def parse_document(file_path: str) -> tuple[str, Dict[str, Any]]:
    """
    Parse document based on file extension.
    
    Args:
        file_path: Path to the document
    
    Returns:
        Tuple of (content, metadata)
    """
    path = Path(file_path)
    extension = path.suffix.lower()
    
    metadata = {
        "file_name": path.name,
        "file_extension": extension,
        "file_size_bytes": path.stat().st_size,
    }
    
    try:
        if extension in ['.txt', '.text']:
            content = parse_text_file(file_path)
            metadata["file_type"] = "text"
        
        elif extension in ['.md', '.markdown']:
            content = parse_markdown_file(file_path)
            metadata["file_type"] = "markdown"
        
        elif extension == '.pdf':
            content = parse_pdf_file(file_path)
            metadata["file_type"] = "pdf"
        
        elif extension in ['.xls', '.xlsx']:
            content = parse_excel_file(file_path)
            metadata["file_type"] = "excel"
        
        elif extension == '.csv':
            content = parse_csv_file(file_path)
            metadata["file_type"] = "csv"
        
        elif extension == '.docx':
            content = parse_word_file(file_path)
            metadata["file_type"] = "word"
        
        elif extension == '.doc':
            content = parse_old_word_file(file_path)
            metadata["file_type"] = "word"
        
        else:
            logger.warning(f"Unsupported file type: {extension}")
            raise ValueError(f"Unsupported file type: {extension}")
        
        metadata["parsed_successfully"] = True
        return content, metadata
    
    except Exception as e:
        logger.error(f"Failed to parse {file_path}: {e}")
        metadata["parsed_successfully"] = False
        metadata["error"] = str(e)
        raise


def get_supported_extensions() -> list:
    """Get list of supported file extensions."""
    return ['.txt', '.text', '.md', '.markdown', '.pdf', '.xls', '.xlsx', '.csv', '.doc', '.docx']


def is_supported_file(file_path: str) -> bool:
    """
    Check if file type is supported.
    
    Args:
        file_path: Path to the file
    
    Returns:
        True if supported, False otherwise
    """
    extension = Path(file_path).suffix.lower()
    return extension in get_supported_extensions()

