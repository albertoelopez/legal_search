#!/usr/bin/env python3
"""
Enhanced Frontend Integration for California Legal Forms

This module enhances the existing hardcoded responses with real data
from the comprehensive crawler, providing:
1. Hardcoded guidance (fast, reliable)
2. Real form links and download URLs
3. Actual form information from California Courts
4. Enhanced search capabilities
"""

import json
import os
import glob
from typing import Dict, List, Any, Optional

class EnhancedLegalFormsIntegration:
    def __init__(self):
        """Initialize the enhanced integration with crawled data."""
        self.forms_data = {}
        self.load_crawled_data()
    
    def load_crawled_data(self):
        """Load all crawled forms data from JSON files."""
        print("📄 Loading crawled forms data...")
        
        # Load individual topic files
        json_files = glob.glob("legal_forms_*.json")
        total_forms = 0
        
        for json_file in json_files:
            try:
                topic = json_file.replace("legal_forms_", "").replace(".json", "").replace("_", " ")
                
                with open(json_file, 'r', encoding='utf-8') as f:
                    forms_list = json.load(f)
                
                self.forms_data[topic] = forms_list
                total_forms += len(forms_list)
                print(f"   ✅ {topic}: {len(forms_list)} forms")
                
            except Exception as e:
                print(f"   ❌ Error loading {json_file}: {e}")
        
        print(f"📊 Total forms loaded: {total_forms} across {len(self.forms_data)} topics")
    
    def get_enhanced_guidance(self, question: str) -> Dict[str, Any]:
        """Get enhanced guidance combining hardcoded responses with real data."""
        question_lower = question.lower()
        
        # Start with base guidance structure
        guidance = {
            "forms": [],
            "steps": [],
            "links": [],
            "requirements": [],
            "description": "",
            "real_forms": [],  # New: actual forms from crawler
            "download_links": [],  # New: direct download links
            "form_info_links": []  # New: detailed form info links
        }
        
        # Determine topic and get hardcoded guidance
        topic = self.determine_topic(question_lower)
        
        if topic:
            # Get hardcoded guidance
            hardcoded_guidance = self.get_hardcoded_guidance(question_lower)
            guidance.update(hardcoded_guidance)
            
            # Enhance with real forms data
            real_forms_data = self.get_real_forms_for_topic(topic)
            if real_forms_data:
                guidance["real_forms"] = real_forms_data["forms"]
                guidance["download_links"] = real_forms_data["download_links"]
                guidance["form_info_links"] = real_forms_data["form_info_links"]
                
                # Add real forms to the forms list
                for real_form in real_forms_data["forms"]:
                    guidance["forms"].append({
                        "code": real_form["form_code"],
                        "name": real_form["form_title"] or real_form["description"],
                        "purpose": real_form["description"],
                        "effective_date": real_form["effective_date"],
                        "languages": real_form["languages"],
                        "mandatory": real_form["mandatory"],
                        "download_url": real_form["download_url"],
                        "info_url": real_form["form_info_url"]
                    })
        
        return guidance
    
    def determine_topic(self, question_lower: str) -> Optional[str]:
        """Determine the topic based on the question."""
        topic_keywords = {
            "adoption": ["adoption", "adopt"],
            "divorce": ["divorce", "dissolution"],
            "child custody and visitation": ["custody", "visitation", "child"],
            "child support": ["support", "child support"],
            "domestic violence": ["restraining", "protection", "harassment", "abuse", "domestic violence"],
            "probate": ["probate", "estate", "will", "executor", "administrator", "deceased", "inheritance"],
            "small claims": ["small claims", "money", "debt", "collection", "sue"],
            "eviction": ["eviction", "unlawful detainer", "tenant", "landlord"],
            "name change": ["name change", "change name"],
            "guardianship": ["guardianship", "guardian"],
            "conservatorship": ["conservatorship", "conservator"],
            "civil harassment": ["civil harassment", "harassment"],
            "traffic": ["traffic", "traffic ticket", "driving"],
            "appeals": ["appeal", "appeals"],
            "juvenile": ["juvenile", "minor"],
            "fee waivers": ["fee waiver", "waive fees", "cannot afford"],
            "proof of service": ["proof of service", "serve papers"],
            "remote appearance": ["remote", "video", "online hearing"]
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                return topic
        
        return None
    
    def get_real_forms_for_topic(self, topic: str) -> Optional[Dict[str, Any]]:
        """Get real forms data for a specific topic."""
        if topic not in self.forms_data:
            return None
        
        forms_list = self.forms_data[topic]
        
        result = {
            "forms": [],
            "download_links": [],
            "form_info_links": []
        }
        
        for form_data in forms_list:
            metadata = form_data.get("metadata", {})
            
            form_info = {
                "form_code": metadata.get("form_code", ""),
                "form_title": metadata.get("form_title", ""),
                "description": self.extract_description_from_content(form_data.get("content", "")),
                "effective_date": metadata.get("effective_date", ""),
                "languages": metadata.get("languages", []),
                "mandatory": metadata.get("mandatory", False),
                "download_url": metadata.get("download_url", ""),
                "form_info_url": metadata.get("form_info_url", ""),
                "related_forms": metadata.get("related_forms", [])
            }
            
            result["forms"].append(form_info)
            
            if form_info["download_url"]:
                result["download_links"].append({
                    "form_code": form_info["form_code"],
                    "url": form_info["download_url"],
                    "text": f"Download {form_info['form_code']}"
                })
            
            if form_info["form_info_url"]:
                result["form_info_links"].append({
                    "form_code": form_info["form_code"],
                    "url": form_info["form_info_url"],
                    "text": f"See {form_info['form_code']} info"
                })
        
        return result
    
    def extract_description_from_content(self, content: str) -> str:
        """Extract a meaningful description from the content."""
        lines = content.split('\n')
        for line in lines:
            if line.startswith("Form Details:") and len(line) > 20:
                # Extract the form name/description
                parts = line.replace("Form Details:", "").strip().split('\n')
                if len(parts) > 1:
                    return parts[1].strip()
        return ""
    
    def get_hardcoded_guidance(self, question_lower: str) -> Dict[str, Any]:
        """Get the original hardcoded guidance (simplified version)."""
        guidance = {
            "forms": [],
            "steps": [],
            "links": [],
            "requirements": [],
            "description": ""
        }
        
        if "divorce" in question_lower:
            guidance.update({
                "description": "For divorce proceedings in California, you typically need several forms and must meet specific requirements.",
                "forms": [
                    {"code": "FL-100", "name": "Petition for Dissolution", "purpose": "Initial filing to start divorce process"},
                    {"code": "FL-110", "name": "Summons", "purpose": "Legal notice to spouse"},
                    {"code": "FL-140/FL-142", "name": "Declaration of Disclosure", "purpose": "Financial information disclosure"},
                    {"code": "FL-180", "name": "Settlement Agreement", "purpose": "If divorce is uncontested"}
                ],
                "requirements": [
                    "6 months residency in California",
                    "3 months residency in the county where filing",
                    "California is a no-fault divorce state"
                ],
                "steps": [
                    "Gather all financial documents",
                    "Complete and file FL-100 petition",
                    "Serve spouse with FL-110 summons",
                    "Complete financial disclosures",
                    "Attend court hearings if contested"
                ],
                "links": [
                    {"text": "California Courts Divorce Self-Help", "url": "https://courts.ca.gov/selfhelp-divorce"},
                    {"text": "Find Your Local Court", "url": "https://courts.ca.gov/find-my-court.htm"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["adoption", "adopt"]):
            guidance.update({
                "description": "Adoption in California involves legal procedures to establish a parent-child relationship. Different types of adoption have different requirements and forms.",
                "requirements": [
                    "Home study and background check",
                    "Consent from birth parents (if required)",
                    "Termination of parental rights (if applicable)",
                    "Best interests of the child determination",
                    "Adoption agency approval (for agency adoptions)"
                ],
                "steps": [
                    "Determine type of adoption (stepparent, relative, agency, independent)",
                    "Complete required pre-adoption requirements",
                    "File adoption petition",
                    "Serve required parties with adoption papers",
                    "Complete home study and background checks",
                    "Attend adoption hearing",
                    "Receive final adoption order"
                ],
                "links": [
                    {"text": "Adoption Self-Help", "url": "https://courts.ca.gov/selfhelp-adoption"},
                    {"text": "Find Your Local Court", "url": "https://courts.ca.gov/find-my-court.htm"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["restraining", "protection", "harassment", "abuse", "domestic violence"]):
            guidance.update({
                "description": "Restraining orders (also called protective orders) are court orders that help protect you from harassment, abuse, stalking, or threats.",
                "requirements": [
                    "Evidence of harassment, abuse, or threats",
                    "Relationship to the person (for domestic violence orders)",
                    "Specific incidents with dates and details",
                    "Any police reports or medical records",
                    "Witness statements if available"
                ],
                "steps": [
                    "Choose the correct type of restraining order",
                    "Complete the appropriate request form",
                    "File the forms with the court clerk",
                    "Serve the papers on the other person",
                    "Attend the court hearing",
                    "If granted, ensure the order is served and filed with local law enforcement"
                ],
                "links": [
                    {"text": "Restraining Orders Self-Help", "url": "https://courts.ca.gov/selfhelp-restraining-orders"},
                    {"text": "Domestic Violence Resources", "url": "https://courts.ca.gov/selfhelp-domestic-violence"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["probate", "estate", "will", "executor", "administrator", "deceased", "inheritance"]):
            guidance.update({
                "description": "Probate is the court process for handling a deceased person's estate. In California, probate may be required depending on the value and type of assets.",
                "requirements": [
                    "Death certificate of the deceased",
                    "Original will (if one exists)",
                    "List of all assets and debts",
                    "Names and addresses of heirs/beneficiaries",
                    "Filing fee (varies by county, typically $435-$465)"
                ],
                "steps": [
                    "Determine if probate is required (assets over $184,500 in 2024)",
                    "File petition for probate with the court",
                    "Publish notice in local newspaper for 3 weeks",
                    "Mail notices to all interested parties",
                    "Attend probate hearing (usually 6-8 weeks after filing)",
                    "Receive Letters Testamentary/Administration",
                    "Complete inventory and appraisal of assets",
                    "Pay debts and taxes",
                    "Distribute remaining assets to beneficiaries",
                    "File final accounting and petition for discharge"
                ],
                "links": [
                    {"text": "California Probate Self-Help", "url": "https://courts.ca.gov/selfhelp-probate"},
                    {"text": "Small Estate Procedures", "url": "https://courts.ca.gov/selfhelp-probate-small-estate"}
                ]
            })
        
        return guidance
    
    def search_forms(self, query: str) -> List[Dict[str, Any]]:
        """Search through all forms data for relevant matches."""
        query_lower = query.lower()
        results = []
        
        for topic, forms_list in self.forms_data.items():
            for form_data in forms_list:
                metadata = form_data.get("metadata", {})
                content = form_data.get("content", "").lower()
                
                # Check if query matches form code, title, or content
                if (query_lower in content or 
                    query_lower in metadata.get("form_code", "").lower() or
                    query_lower in metadata.get("form_title", "").lower()):
                    
                    results.append({
                        "topic": topic,
                        "form_code": metadata.get("form_code", ""),
                        "form_title": metadata.get("form_title", ""),
                        "description": self.extract_description_from_content(content),
                        "download_url": metadata.get("download_url", ""),
                        "form_info_url": metadata.get("form_info_url", ""),
                        "effective_date": metadata.get("effective_date", ""),
                        "languages": metadata.get("languages", []),
                        "mandatory": metadata.get("mandatory", False)
                    })
        
        return results[:20]  # Limit to top 20 results

def test_enhanced_integration():
    """Test the enhanced integration."""
    print("🧪 Testing Enhanced Legal Forms Integration")
    print("=" * 50)
    
    integration = EnhancedLegalFormsIntegration()
    
    # Test adoption query
    print("\n📋 Testing adoption query...")
    adoption_guidance = integration.get_enhanced_guidance("I want to adopt a child")
    print(f"   Hardcoded forms: {len(adoption_guidance['forms'])}")
    print(f"   Real forms: {len(adoption_guidance['real_forms'])}")
    print(f"   Download links: {len(adoption_guidance['download_links'])}")
    
    # Test search
    print("\n🔍 Testing form search...")
    search_results = integration.search_forms("ADOPT-200")
    print(f"   Search results: {len(search_results)}")
    if search_results:
        print(f"   First result: {search_results[0]['form_code']} - {search_results[0]['description']}")
    
    print("\n✅ Enhanced integration test completed!")

if __name__ == "__main__":
    test_enhanced_integration() 