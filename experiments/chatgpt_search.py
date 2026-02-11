"""
Enhanced ChatGPT web search agent for CFIA compliance - Independent execution with structured results.
Features:
- Accepts queries with key-value pairs (key identifies query, value is the query text)
- Independent execution with context awareness
- Structured results with citations
- Enhanced formatting with source attribution
"""

import json
import os
from typing import Any, Dict, List, Optional
from openai import OpenAI


# Default allowed sources for CFIA information
DEFAULT_ALLOWED_SOURCES = [
    "inspection.canada.ca",
    "cfia.gc.ca",
    "canada.ca/food",
    "laws-lois.justice.gc.ca",
    "gazette.gc.ca",
]


class CFIASearchResult:
    """Structured result from CFIA search query."""
    
    def __init__(self, query_key: str, query_text: str):
        self.query_key = query_key
        self.query_text = query_text
        self.rules: List[Dict[str, Any]] = []
        self.citations: List[str] = []
        self.error: Optional[str] = None
        self.raw_response: str = ""
    
    def add_rule(self, rule: str, requirement: str = "", source: str = "unknown"):
        """Add a rule to the result."""
        self.rules.append({
            "rule": rule,
            "requirement": requirement,
            "source": source
        })
        if source not in self.citations and source != "unknown":
            self.citations.append(source)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "query_key": self.query_key,
            "query_text": self.query_text,
            "rules_count": len(self.rules),
            "citations": self.citations,
            "rules": self.rules,
            "error": self.error
        }
    
    def to_formatted_string(self) -> str:
        """Format result as readable string."""
        output = f"\n{'=' * 80}\n"
        output += f"Query: [{self.query_key}] {self.query_text}\n"
        output += f"{'=' * 80}\n"
        
        if self.error:
            output += f"❌ Error: {self.error}\n"
            return output
        
        output += f"✓ Found {len(self.rules)} rule(s)\n"
        output += f"✓ Sources: {', '.join(self.citations) if self.citations else 'Unknown'}\n"
        output += f"\n{'Rules:'}\n"
        
        for i, rule in enumerate(self.rules, 1):
            output += f"\n  {i}. {rule['rule']}\n"
            if rule['requirement']:
                output += f"     Requirement: {rule['requirement']}\n"
            output += f"     Citation: {rule['source']}\n"
        
        return output


def execute_query(
    query_key: str,
    query_text: str,
    context: Optional[str] = None,
    api_key: Optional[str] = None,
    allowed_sources: Optional[List[str]] = None,
) -> CFIASearchResult:
    """
    Execute a single search query independently with context.
    
    Args:
        query_key: Unique identifier for the query (e.g., "allergen_labeling")
        query_text: The actual query text to search for
        context: Additional context to include in the search (e.g., product type, regulations)
        api_key: OpenAI API key (uses OPENAI_API_KEY env var if not provided)
        allowed_sources: List of allowed source domains
    
    Returns:
        CFIASearchResult with structured findings and citations
    """
    if allowed_sources is None:
        allowed_sources = DEFAULT_ALLOWED_SOURCES
    
    result = CFIASearchResult(query_key, query_text)
    
    try:
        client = OpenAI(api_key=api_key)
        sources_str = ", ".join(allowed_sources)
        
        # Build context-aware prompt
        context_part = f"\nContext: {context}\n" if context else ""
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": f"You are a CFIA (Canadian Food Inspection Agency) compliance expert. "
                               f"Your role is to provide accurate, authoritative information about food labeling regulations. "
                               f"Search ONLY from these authorized sources: {sources_str}. "
                               f"Return results in this exact JSON format:\n"
                               f'{{"rules": [{{"rule": "specific_rule", "requirement": "detailed_requirement", "source": "exact_url"}}]}}\n'
                               f"CRITICAL: Every result MUST include a 'source' field with the exact URL where the information was found."
                },
                {
                    "role": "user",
                    "content": f"Query: {query_text}{context_part}\n\n"
                               f"Find all applicable CFIA compliance rules and regulations for this query.\n"
                               f"Sources to use: {sources_str}\n"
                               f"Include the exact source URL for each rule found."
                }
            ],
            temperature=0,
        )
        
        response_text = response.choices[0].message.content
        result.raw_response = response_text
        
        # Parse JSON response
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                parsed = json.loads(json_str)
                
                for rule_item in parsed.get("rules", []):
                    source = rule_item.get("source", "unknown")
                    if not source or source == "":
                        source = "unknown"
                    result.add_rule(
                        rule=rule_item.get("rule", ""),
                        requirement=rule_item.get("requirement", ""),
                        source=source
                    )
            else:
                result.error = "Could not parse response as JSON"
                result.add_rule(response_text, source="unparsed_response")
                
        except json.JSONDecodeError as e:
            result.error = f"JSON parse error: {str(e)}"
            result.add_rule(response_text, source="unparsed_response")
        
    except Exception as e:
        result.error = str(e)
    
    return result


def execute_queries(
    queries: Dict[str, str],
    context: Optional[str] = None,
    api_key: Optional[str] = None,
    allowed_sources: Optional[List[str]] = None,
) -> List[CFIASearchResult]:
    """
    Execute multiple search queries with key-value structure.
    
    Args:
        queries: Dictionary where key identifies the query and value is the query text
                 Example: {"allergens": "What are CFIA requirements for allergen labeling?"}
        context: Optional shared context for all queries
        api_key: OpenAI API key
        allowed_sources: List of allowed source domains
    
    Returns:
        List of CFIASearchResult objects
    """
    results = []
    for query_key, query_text in queries.items():
        result = execute_query(
            query_key=query_key,
            query_text=query_text,
            context=context,
            api_key=api_key,
            allowed_sources=allowed_sources,
        )
        results.append(result)
    
    return results


def format_results_json(results: List[CFIASearchResult]) -> str:
    """
    Format results as structured JSON.
    
    Args:
        results: List of search results
    
    Returns:
        JSON string with all results
    """
    formatted = {
        "summary": {
            "total_queries": len(results),
            "successful": len([r for r in results if not r.error]),
            "failed": len([r for r in results if r.error])
        },
        "results": [r.to_dict() for r in results]
    }
    return json.dumps(formatted, indent=2, ensure_ascii=False)


def format_results_text(results: List[CFIASearchResult]) -> str:
    """
    Format results as human-readable text with citations.
    
    Args:
        results: List of search results
    
    Returns:
        Formatted text string
    """
    output = f"\n{'#' * 80}\n"
    output += "CFIA COMPLIANCE SEARCH RESULTS\n"
    output += f"{'#' * 80}\n"
    output += f"Total queries: {len(results)}\n"
    
    for result in results:
        output += result.to_formatted_string()
    
    # Add bibliography
    all_citations = set()
    for result in results:
        all_citations.update(result.citations)
    
    if all_citations:
        output += f"\n{'=' * 80}\n"
        output += "CITATIONS AND SOURCES\n"
        output += f"{'=' * 80}\n"
        for i, citation in enumerate(sorted(all_citations), 1):
            output += f"{i}. {citation}\n"
    
    return output


def get_allowed_sources_env() -> List[str]:
    """
    Get allowed sources from environment variable CFIA_ALLOWED_SOURCES.
    Expected format: comma-separated list of domains.
    Falls back to DEFAULT_ALLOWED_SOURCES if not set.
    
    Returns:
        List of allowed source domains
    """
    env_sources = os.environ.get("CFIA_ALLOWED_SOURCES", "")
    if env_sources:
        return [s.strip() for s in env_sources.split(",")]
    return DEFAULT_ALLOWED_SOURCES


# Backward compatibility with cfia_search_chatgpt_agent
def cfia_search_chatgpt_agent(
    project_id: Optional[str] = None,
    location: Optional[str] = None,
    datastore_id: Optional[str] = None,
    serving_config: Optional[str] = None,
    label_facts: Dict[str, Any] = None,
    product_metadata: Dict[str, Any] = None,
    api_key: Optional[str] = None,
    allowed_sources: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Legacy interface for backward compatibility with main.py.
    Normalized interface to retrieve CFIA compliance evidence using ChatGPT web search.
    """
    if label_facts is None:
        label_facts = {}
    if product_metadata is None:
        product_metadata = {}
    
    # Extract queries from label_facts fields
    queries = {}
    for field_name, field_data in label_facts.get("fields", {}).items():
        field_value = field_data.get("value", "") if isinstance(field_data, dict) else str(field_data)
        if field_value:
            queries[field_name] = f"CFIA compliance requirements for {field_name}: {field_value}"
    
    # If no queries extracted, use product info
    if not queries and product_metadata:
        product_name = product_metadata.get("product_name", "product")
        product_category = product_metadata.get("category", "")
        query = f"CFIA compliance rules for {product_category} {product_name}".strip()
        queries["product"] = query
    
    if not queries:
        queries = {"general": "CFIA food labeling compliance rules"}
    
    # Get allowed sources
    if allowed_sources is None:
        allowed_sources = get_allowed_sources_env()
    
    # Run search and collect results
    search_results = execute_queries(
        queries=queries,
        api_key=api_key,
        allowed_sources=allowed_sources,
    )
    
    # Normalize to cfia_retrieve_snippets format
    evidence = {
        "search_results": [r.to_dict() for r in search_results],
        "snippets": [],
        "sources": set(),
        "rules": []
    }
    
    for result in search_results:
        for rule in result.rules:
            source = rule.get("source", "unknown")
            evidence["sources"].add(source)
            evidence["snippets"].append({
                "text": rule.get("rule", ""),
                "requirement": rule.get("requirement", ""),
                "source": source,
                "query": result.query_text
            })
            evidence["rules"].append(rule)
    
    # Convert set to list for JSON serialization
    evidence["sources"] = list(evidence["sources"])
    
    return evidence
