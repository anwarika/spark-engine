"""
Content-Addressable Generation (CAG) Service

Provides deduplication and reuse of micro-apps based on semantic intent.
Instead of regenerating identical components, we return existing ones when:
- The normalized prompt is semantically similar
- The template/component type matches
- The data profile is compatible
"""

import hashlib
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class ContentFingerprint:
    """Represents the normalized content hash of a generation request"""
    content_hash: str
    normalized_prompt: str
    template_name: Optional[str]
    data_profile: str
    metadata: Dict[str, Any]


class CAGService:
    """Content-Addressable Generation service for component deduplication"""
    
    @staticmethod
    def normalize_prompt(prompt: str) -> str:
        """
        Normalize a user prompt for comparison.
        
        - Convert to lowercase
        - Remove extra whitespace
        - Remove punctuation at end
        - Canonicalize common synonyms
        """
        # Lowercase
        normalized = prompt.lower().strip()
        
        # Remove trailing punctuation
        normalized = re.sub(r'[.!?]+$', '', normalized)
        
        # Normalize whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Canonicalize common synonyms (expand as needed)
        synonyms = {
            r'\bchart\b': 'chart',
            r'\bgraph\b': 'chart',
            r'\bvisualization\b': 'chart',
            r'\bdashboard\b': 'dashboard',
            r'\btable\b': 'table',
            r'\blist\b': 'list',
            r'\bshow me\b': 'show',
            r'\bdisplay\b': 'show',
            r'\bcreate\b': 'create',
            r'\bgenerate\b': 'create',
            r'\bmake\b': 'create',
            r'\bbuild\b': 'create',
        }
        
        for pattern, replacement in synonyms.items():
            normalized = re.sub(pattern, replacement, normalized)
        
        return normalized
    
    @staticmethod
    def compute_content_hash(
        prompt: str,
        template_name: Optional[str] = None,
        data_profile: str = "ecommerce"
    ) -> str:
        """
        Compute a content-addressable hash for a generation request.
        
        This hash represents the *intent* of the generation, not the actual code.
        Same intent = same hash = reuse existing component.
        
        Args:
            prompt: User's natural language prompt
            template_name: Template to use (if specified by LLM)
            data_profile: Data profile (ecommerce, saas, etc.)
            
        Returns:
            SHA256 hash as hex string
        """
        normalized_prompt = CAGService.normalize_prompt(prompt)
        
        # Build canonical string for hashing
        parts = [
            f"prompt:{normalized_prompt}",
            f"template:{template_name or 'auto'}",
            f"profile:{data_profile}",
        ]
        canonical = "|".join(parts)
        
        # Compute SHA256
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    
    @staticmethod
    def create_fingerprint(
        prompt: str,
        template_name: Optional[str] = None,
        data_profile: str = "ecommerce",
        metadata: Optional[Dict[str, Any]] = None
    ) -> ContentFingerprint:
        """
        Create a complete content fingerprint for a generation request.
        
        Returns:
            ContentFingerprint with hash and normalized components
        """
        normalized_prompt = CAGService.normalize_prompt(prompt)
        content_hash = CAGService.compute_content_hash(prompt, template_name, data_profile)
        
        return ContentFingerprint(
            content_hash=content_hash,
            normalized_prompt=normalized_prompt,
            template_name=template_name,
            data_profile=data_profile,
            metadata=metadata or {}
        )
    
    @staticmethod
    def should_reuse(
        existing_component: Dict[str, Any],
        requested_template: Optional[str] = None
    ) -> bool:
        """
        Determine if an existing component can be reused.
        
        Checks:
        - Component is active
        - Component compiled successfully
        - Template matches (if specified)
        
        Args:
            existing_component: Component dict from database
            requested_template: Template name requested (if any)
            
        Returns:
            True if component can be reused
        """
        if existing_component.get('status') != 'active':
            return False
        
        if not existing_component.get('compiled'):
            return False
        
        # If template was specified, check it matches
        if requested_template:
            gen_metadata = existing_component.get('generation_metadata', {})
            if isinstance(gen_metadata, str):
                import json
                try:
                    gen_metadata = json.loads(gen_metadata)
                except:
                    gen_metadata = {}
            
            existing_template = gen_metadata.get('template_name')
            if existing_template and existing_template != requested_template:
                return False
        
        return True


def increment_reuse_count(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Increment the reuse count in generation metadata.
    
    Args:
        metadata: Existing generation_metadata dict
        
    Returns:
        Updated metadata with incremented reuse_count
    """
    updated = metadata.copy()
    updated['reuse_count'] = updated.get('reuse_count', 0) + 1
    return updated
