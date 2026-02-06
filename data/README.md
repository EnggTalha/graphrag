# Data Directory

This directory contains sample documents for ingestion into Graph-RAG.

## 📁 Structure

Place your documents here organized by category:

```
data/
├── README.md              # This file
├── 01_Documentation/      # API docs, technical specs
├── 02_Knowledge_Base/     # General knowledge articles
├── 03_Research_Papers/    # Academic papers, whitepapers
├── 04_Code_Examples/      # Code snippets and examples
└── 05_FAQ/                # Frequently asked questions
```

## 📄 Supported Formats

- **Text**: `.txt`, `.md`, `.markdown`, `.rst`
- **Documents**: `.pdf`, `.doc`, `.docx`
- **Data**: `.json`, `.csv`, `.xlsx`
- **Code**: `.py`, `.js`, `.ts`, etc.

## 🚀 Getting Started

1. **Place your documents** in the appropriate subdirectories
2. **Run the ingestion pipeline**:
   ```bash
   python -m ingestion.ingest --documents ./data --watch --verbose
   ```
3. **The system will**:
   - Automatically process all files
   - Extract entities and relationships
   - Build a knowledge graph
   - Create vector embeddings
   - Watch for new files and auto-ingest them

## 💡 Tips

- **File Naming**: Use descriptive names for better context (e.g., `Python_AsyncIO_Guide.md`)
- **Organization**: Group related documents in subdirectories
- **Content Size**: Start with smaller documents to verify setup works
- **Metadata**: Include headers/titles - they help with context

## 📊 Example Structure for Your Domain

```
data/
├── 01_Technical_Specs/
│   ├── API_Reference.md
│   ├── Architecture_Guide.pdf
│   └── Configuration.txt
├── 02_Tutorials/
│   ├── Getting_Started.md
│   ├── Advanced_Features.md
│   └── Troubleshooting.md
├── 03_Examples/
│   ├── basic_example.py
│   ├── advanced_example.json
│   └── use_cases.md
└── 04_Reference/
    ├── Glossary.txt
    ├── FAQ.md
    └── Best_Practices.md
```

## ⚙️ Configuration

Ingestion behavior can be controlled via `.env`:

```bash
CHUNKING_STRATEGY=semantic    # or: fixed, paragraph
CHUNK_SIZE=1000              # characters per chunk
CHUNK_OVERLAP=200            # overlap between chunks
EXTRACT_RELATIONSHIPS=true   # extract entities and relationships
```

## 📝 Notes

- The ingestion system automatically handles duplicate detection
- Large documents are chunked for better retrieval
- Metadata is preserved for context in responses
- Knowledge graph relationships are extracted automatically
