"""
Compliance Law Document Processor
Specialized for processing FINRA, SEC, and compliance law documents with link preservation.
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class ComplianceDocumentProcessor:
    """Process compliance law documents with link and reference preservation."""
    
    def __init__(self, reference_map_path: Optional[str] = None):
        """
        Initialize compliance processor.
        
        Args:
            reference_map_path: Path to reference_map.json containing URLs and metadata
        """
        self.reference_map = self._load_reference_map(reference_map_path)
        self.case_regex = re.compile(r'\b(\d{4,}[0-9]{6,})\b')  # FINRA case ID pattern
        self.rule_regex = re.compile(r'\b(FINRA Rule \d+[\.\d]*|SEC Rule [\d\-]+)\b', re.IGNORECASE)
    
    def _load_reference_map(self, path: Optional[str]) -> Dict[str, Any]:
        """Load reference map for looking up URLs and metadata."""
        if path and os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load reference map: {e}")
        
        # Try default path
        default_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'data',
            'reference_map.json'
        )
        
        if os.path.exists(default_path):
            try:
                with open(default_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load reference map from default path: {e}")
        
        return {}
    
    def extract_metadata(self, content: str, source_path: str) -> Dict[str, Any]:
        """
        Extract metadata from compliance document.
        
        Args:
            content: Document content
            source_path: Source file path
        
        Returns:
            Metadata dictionary with extracted information
        """
        metadata = {
            "source_path": source_path,
            "processed_at": datetime.now().isoformat(),
            "document_type": self._identify_document_type(source_path),
            "compliance_areas": self._extract_compliance_areas(content),
            "case_ids": self._extract_case_ids(content),
            "rule_references": self._extract_rule_references(content),
            "extracted_links": self._extract_embedded_links(content)
        }
        
        return metadata
    
    def _identify_document_type(self, source_path: str) -> str:
        """Identify document type from path."""
        path_lower = source_path.lower()
        
        if 'finra' in path_lower and 'rule' in path_lower:
            return 'FINRA_Rulebook'
        elif 'finra' in path_lower and 'case' in path_lower:
            return 'FINRA_Case'
        elif '606' in path_lower or 'nms' in path_lower:
            return 'FINRA_606_NMS'
        elif 'sec' in path_lower and 'rule' in path_lower:
            return 'SEC_Rules_Regulations'
        elif 'charter' in path_lower:
            return 'SEC_Charter'
        elif 'glossary' in path_lower or 'investopedia' in path_lower:
            return 'Glossary'
        elif 'book' in path_lower:
            return 'Book'
        
        return 'Unknown'
    
    def _extract_compliance_areas(self, content: str) -> List[str]:
        """Extract compliance areas mentioned in document."""
        areas = []
        
        compliance_keywords = {
            'market_conduct': ['market conduct', 'manipulation', 'fraud', 'insider trading'],
            'investor_protection': ['customer protection', 'suitability', 'best execution'],
            'reporting': ['reporting requirement', 'disclosure', 'form', 'filing'],
            'supervision': ['supervision', 'supervisory', 'compliance review'],
            'trading': ['trading practice', 'order', 'execution', 'clearing'],
            'compensation': ['compensation', 'commissions', 'fees', 'rebate'],
        }
        
        content_lower = content.lower()
        for area, keywords in compliance_keywords.items():
            for keyword in keywords:
                if keyword in content_lower:
                    areas.append(area)
                    break
        
        return list(set(areas))
    
    def _extract_case_ids(self, content: str) -> List[Dict[str, Any]]:
        """Extract FINRA case IDs and their URLs from content."""
        cases = []
        found_ids = self.case_regex.findall(content)
        
        for case_id in found_ids:
            # Look up in reference map
            url = None
            metadata = {}
            
            if 'FINRA_Cases' in self.reference_map:
                case_data = self.reference_map['FINRA_Cases'].get(case_id, {})
                if case_data:
                    url = case_data.get('url')
                    metadata = case_data
            
            cases.append({
                'id': case_id,
                'url': url,
                'metadata': metadata
            })
        
        return cases
    
    def _extract_rule_references(self, content: str) -> List[Dict[str, str]]:
        """Extract rule references from content."""
        rules = []
        found_rules = self.rule_regex.findall(content)
        
        for rule in set(found_rules):
            rules.append({
                'rule': rule,
                'type': 'FINRA_Rule' if 'FINRA' in rule else 'SEC_Rule'
            })
        
        return rules
    
    def _extract_embedded_links(self, content: str) -> List[Dict[str, str]]:
        """Extract URLs embedded in document content."""
        url_pattern = re.compile(
            r'https?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        
        links = []
        for url in set(url_pattern.findall(content)):
            links.append({
                'url': url,
                'context': 'embedded'
            })
        
        return links
    
    def enrich_chunk_with_links(
        self,
        chunk_content: str,
        chunk_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enrich a chunk with relevant links and references.
        
        Args:
            chunk_content: Chunk text content
            chunk_metadata: Existing chunk metadata
        
        Returns:
            Enhanced metadata with links
        """
        enhanced_metadata = chunk_metadata.copy()
        
        # Extract case IDs and rules from this specific chunk
        chunk_cases = []
        chunk_rules = []
        chunk_links = []
        
        # Find case IDs in chunk
        for case_match in self.case_regex.finditer(chunk_content):
            case_id = case_match.group(0)
            if 'FINRA_Cases' in self.reference_map:
                case_data = self.reference_map['FINRA_Cases'].get(case_id, {})
                if case_data:
                    chunk_cases.append({
                        'id': case_id,
                        'url': case_data.get('url'),
                        'title': case_data.get('title'),
                        'summary': case_data.get('summary')
                    })
        
        # Find rules in chunk
        for rule_match in self.rule_regex.finditer(chunk_content):
            rule = rule_match.group(0)
            chunk_rules.append({
                'rule': rule,
                'type': 'FINRA_Rule' if 'FINRA' in rule else 'SEC_Rule'
            })
        
        # Find URLs in chunk
        url_pattern = re.compile(
            r'https?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        
        for url_match in url_pattern.finditer(chunk_content):
            chunk_links.append({
                'url': url_match.group(0),
                'position': url_match.start()
            })
        
        # Add to metadata
        enhanced_metadata['related_cases'] = chunk_cases
        enhanced_metadata['related_rules'] = chunk_rules
        enhanced_metadata['embedded_links'] = chunk_links
        enhanced_metadata['has_references'] = bool(chunk_cases or chunk_rules or chunk_links)
        
        return enhanced_metadata
    
    def generate_reference_summary(self, chunk_metadata: Dict[str, Any]) -> str:
        """Generate a summary of all references in a chunk."""
        summary_parts = []
        
        if chunk_metadata.get('related_cases'):
            cases_str = ', '.join([f"{c['id']}" for c in chunk_metadata['related_cases']])
            summary_parts.append(f"Related Cases: {cases_str}")
        
        if chunk_metadata.get('related_rules'):
            rules_str = ', '.join([r['rule'] for r in chunk_metadata['related_rules']])
            summary_parts.append(f"Relevant Rules: {rules_str}")
        
        if chunk_metadata.get('embedded_links'):
            summary_parts.append(f"External Links: {len(chunk_metadata['embedded_links'])} found")
        
        return ' | '.join(summary_parts) if summary_parts else 'No specific references'
    
    def create_chunk_with_context(
        self,
        chunk_content: str,
        chunk_metadata: Dict[str, Any],
        document_title: str,
        document_source: str
    ) -> Dict[str, Any]:
        """
        Create a rich chunk with full context and references for compliance law.
        
        Args:
            chunk_content: The actual chunk text
            chunk_metadata: Chunk metadata
            document_title: Title of source document
            document_source: Path to source document
        
        Returns:
            Rich chunk with all context
        """
        enriched_metadata = self.enrich_chunk_with_links(chunk_content, chunk_metadata)
        
        return {
            'content': chunk_content,
            'metadata': enriched_metadata,
            'document_title': document_title,
            'document_source': document_source,
            'references_summary': self.generate_reference_summary(enriched_metadata),
            'indexed_at': datetime.now().isoformat()
        }


# Helper function to create a global processor instance
_processor_instance: Optional[ComplianceDocumentProcessor] = None


def get_compliance_processor() -> ComplianceDocumentProcessor:
    """Get or create a global compliance processor instance."""
    global _processor_instance
    
    if _processor_instance is None:
        _processor_instance = ComplianceDocumentProcessor()
    
    return _processor_instance
