"""
File parsers for various document formats.
Supports: .txt, .md, .pdf, .xls, .xlsx, .csv
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
    return ['.txt', '.text', '.md', '.markdown', '.pdf', '.xls', '.xlsx', '.csv']


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

