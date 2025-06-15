#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sys
import os
import json
import urllib.request
import urllib.parse

# Add parent directory to path to import the legal agent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our updated court forms agent
from court_forms_agent import CourtFormsAgent

app = Flask(__name__)
CORS(app)

MCP_BASE_URL = "http://localhost:8052"

class LegalAgentAPI:
    def __init__(self):
        self.mcp_session_id = None
        # Initialize our updated court forms agent
        self.court_agent = CourtFormsAgent()

    def get_mcp_session_id(self):
        """Get session ID from MCP server SSE endpoint."""
        if self.mcp_session_id:
            return self.mcp_session_id
        
        try:
            with urllib.request.urlopen(f"{MCP_BASE_URL}/sse") as response:
                for line in response:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: /messages/?session_id='):
                        self.mcp_session_id = line.split('session_id=')[1]
                        break
        except Exception as e:
            print(f"Error getting session ID: {e}")
            self.mcp_session_id = "fallback-session-123"
        
        return self.mcp_session_id

    def call_mcp_tool(self, tool_name, arguments, tool_id=1):
        """Call an MCP tool using JSON-RPC 2.0 format."""
        payload = {
            "jsonrpc": "2.0",
            "id": tool_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        data = json.dumps(payload).encode('utf-8')
        headers = {'Content-Type': 'application/json'}
        
        try:
            req = urllib.request.Request(MCP_BASE_URL, data=data, headers=headers)
            with urllib.request.urlopen(req) as response:
                result = response.read().decode('utf-8')
                try:
                    return json.loads(result)
                except json.JSONDecodeError:
                    return {"error": "Invalid response format", "raw_response": result}
        except Exception as e:
            return {"error": str(e)}

    def search_forms(self, query, limit=5):
        """Search for forms using our vector database agent."""
        try:
            # Use our updated court forms agent for vector search
            results = self.court_agent.search_vector_database(query, limit=limit, similarity_threshold=0.0)
            
            # Format results for frontend
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "code": result.get('form_code', 'Unknown'),
                    "title": result.get('title', 'Unknown Form'),
                    "topic": result.get('topic', 'Unknown'),
                    "similarity": result.get('similarity', 0.0),
                    "url": result.get('url', ''),
                    "content": result.get('content', '')[:200] + "..." if len(result.get('content', '')) > 200 else result.get('content', '')
                })
            
            return {
                "status": "success",
                "forms": formatted_results,
                "total_found": len(formatted_results),
                "source": "vector_database"
            }
            
        except Exception as e:
            print(f"Error in vector search: {e}")
            # Fallback to MCP if vector search fails
            result = self.call_mcp_tool("search_legal_forms", {
                "query": query,
                "limit": limit
            })
            return {
                "status": "fallback_mcp",
                "result": result,
                "source": "mcp_fallback"
            }

    def get_guidance_for_question(self, question):
        """Provide specific guidance based on the question."""
        question_lower = question.lower()
        
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
                    {"code": "FL-100", "name": "Petition for Dissolution", "purpose": "Initial filing to start divorce process", "url": "https://selfhelp.courts.ca.gov/find-forms?query=divorce#FL-100"},
                    {"code": "FL-110", "name": "Summons", "purpose": "Legal notice to spouse", "url": "https://selfhelp.courts.ca.gov/find-forms?query=divorce#FL-110"},
                    {"code": "FL-140", "name": "Declaration of Disclosure", "purpose": "Financial information disclosure", "url": "https://selfhelp.courts.ca.gov/find-forms?query=divorce#FL-140"},
                    {"code": "FL-180", "name": "Settlement Agreement", "purpose": "If divorce is uncontested", "url": "https://selfhelp.courts.ca.gov/find-forms?query=divorce#FL-180"}
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
        
        elif any(keyword in question_lower for keyword in ["adoption", "adopt"]) and not any(word in question_lower for word in ["custody", "visitation"]):
            guidance.update({
                "description": "Adoption in California involves legal procedures to establish a parent-child relationship. Different types of adoption have different requirements and forms.",
                "forms": [
                    {"code": "ADOPT-200", "name": "Petition for Adoption", "purpose": "Initial petition to request adoption", "url": "https://selfhelp.courts.ca.gov/find-forms?query=adoption#ADOPT-200"},
                    {"code": "ADOPT-210", "name": "Contact After Adoption Agreement", "purpose": "Agreement for ongoing contact after adoption", "url": "https://selfhelp.courts.ca.gov/find-forms?query=adoption#ADOPT-210"},
                    {"code": "ADOPT-215", "name": "Adoption Request", "purpose": "Request for adoption order", "url": "https://selfhelp.courts.ca.gov/find-forms?query=adoption#ADOPT-215"},
                    {"code": "ADOPT-220", "name": "Adoption Order", "purpose": "Court order finalizing adoption", "url": "https://selfhelp.courts.ca.gov/find-forms?query=adoption#ADOPT-220"}
                ],
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
                    "File ADOPT-200 Petition for Adoption",
                    "Serve required parties with adoption papers",
                    "Complete home study and background checks",
                    "Attend adoption hearing",
                    "Receive final adoption order"
                ],
                "links": [
                    {"text": "Adoption Self-Help", "url": "https://courts.ca.gov/selfhelp-adoption"},
                    {"text": "Adoption Forms", "url": "https://courts.ca.gov/forms/adoption"},
                    {"text": "Find Your Local Court", "url": "https://courts.ca.gov/find-my-court.htm"}
                ]
            })
        
        elif "custody" in question_lower or ("child" in question_lower and not any(word in question_lower for word in ["adoption", "adopt"])):
            guidance.update({
                "description": "Child custody matters in California prioritize the child's best interests above all else.",
                "forms": [
                    {"code": "FL-300", "name": "Request for Order", "purpose": "To request custody/visitation orders", "url": "https://selfhelp.courts.ca.gov/find-forms?query=child+custody+and+visitation#FL-300"},
                    {"code": "FL-311", "name": "Declaration", "purpose": "Your statement to the court", "url": "https://selfhelp.courts.ca.gov/find-forms?query=child+custody+and+visitation#FL-311"},
                    {"code": "FL-341E", "name": "Parenting Plan", "purpose": "Detailed custody arrangement", "url": "https://selfhelp.courts.ca.gov/find-forms?query=child+custody+and+visitation#FL-341E"}
                ],
                "requirements": [
                    "Child's best interests are paramount",
                    "Consider child's health, safety, and welfare",
                    "History of abuse or violence affects decisions",
                    "Parent's ability to care for child"
                ],
                "steps": [
                    "Complete FL-300 Request for Order",
                    "Write detailed FL-311 Declaration",
                    "Create comprehensive parenting plan",
                    "Attend mediation if required",
                    "Present case at court hearing"
                ],
                "links": [
                    {"text": "Child Custody Self-Help", "url": "https://courts.ca.gov/selfhelp-custody"},
                    {"text": "Mediation Information", "url": "https://courts.ca.gov/programs-mediation.htm"}
                ]
            })
        
        elif "support" in question_lower:
            guidance.update({
                "description": "Child and spousal support in California is calculated based on specific guidelines and factors.",
                "forms": [
                    {"code": "FL-150", "name": "Income and Expense Declaration", "purpose": "Financial information for support calculation", "url": "https://selfhelp.courts.ca.gov/find-forms?query=child+support#FL-150"},
                    {"code": "FL-300", "name": "Request for Order", "purpose": "To request support orders", "url": "https://selfhelp.courts.ca.gov/find-forms?query=child+support#FL-300"},
                    {"code": "FL-191", "name": "Child Support Case Registry Form", "purpose": "Register case for support enforcement", "url": "https://selfhelp.courts.ca.gov/find-forms?query=child+support#FL-191"}
                ],
                "requirements": [
                    "Both parents' income information",
                    "Time spent with each parent",
                    "Number of children",
                    "Health insurance and childcare costs"
                ],
                "steps": [
                    "Gather all income documentation",
                    "Complete FL-150 financial declaration",
                    "File FL-300 request for support",
                    "Attend court hearing",
                    "Set up payment through DCSS if ordered"
                ],
                "links": [
                    {"text": "Child Support Self-Help", "url": "https://courts.ca.gov/selfhelp-support"},
                    {"text": "Support Calculator", "url": "https://www.courts.ca.gov/selfhelp-support.htm"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["restraining", "protection", "harassment", "abuse", "domestic violence"]):
            guidance.update({
                "description": "Restraining orders (also called protective orders) are court orders that help protect you from harassment, abuse, stalking, or threats.",
                "forms": [
                    {"code": "DV-100", "name": "Request for Domestic Violence Restraining Order", "purpose": "Initial petition for domestic violence protection", "url": "https://selfhelp.courts.ca.gov/find-forms?query=domestic+violence#DV-100"},
                    {"code": "DV-110", "name": "Temporary Restraining Order", "purpose": "Immediate temporary protection", "url": "https://selfhelp.courts.ca.gov/find-forms?query=domestic+violence#DV-110"},
                    {"code": "DV-120", "name": "Response to Request for Domestic Violence Restraining Order", "purpose": "Respondent's response to the request", "url": "https://selfhelp.courts.ca.gov/find-forms?query=domestic+violence#DV-120"},
                    {"code": "CH-100", "name": "Request for Civil Harassment Restraining Order", "purpose": "Protection from non-domestic harassment", "url": "https://selfhelp.courts.ca.gov/find-forms?query=civil+harassment#CH-100"},
                    {"code": "SV-100", "name": "Request for Sexual Violence Restraining Order", "purpose": "Protection from sexual violence", "url": "https://selfhelp.courts.ca.gov/find-forms?query=domestic+violence#SV-100"}
                ],
                "requirements": [
                    "Evidence of harassment, abuse, or threats",
                    "Relationship to the person (for domestic violence orders)",
                    "Specific incidents with dates and details",
                    "Any police reports or medical records",
                    "Witness statements if available"
                ],
                "steps": [
                    "Choose the correct type of restraining order",
                    "Complete the appropriate request form (DV-100, CH-100, or SV-100)",
                    "File the forms with the court clerk",
                    "Serve the papers on the other person",
                    "Attend the court hearing",
                    "If granted, ensure the order is served and filed with local law enforcement"
                ],
                "links": [
                    {"text": "Restraining Orders Self-Help", "url": "https://courts.ca.gov/selfhelp-restraining-orders"},
                    {"text": "Domestic Violence Resources", "url": "https://courts.ca.gov/selfhelp-domestic-violence"},
                    {"text": "Find Your Local Court", "url": "https://courts.ca.gov/find-my-court.htm"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["probate", "estate", "will", "executor", "administrator", "deceased", "inheritance"]):
            guidance.update({
                "description": "Probate is the court process for handling a deceased person's estate. In California, probate may be required depending on the value and type of assets.",
                "forms": [
                    {"code": "DE-111", "name": "Petition for Probate", "purpose": "Initial petition to open probate case"},
                    {"code": "DE-121", "name": "Letters Testamentary/Administration", "purpose": "Court authorization to act as executor/administrator"},
                    {"code": "DE-140", "name": "Order for Probate", "purpose": "Court order granting probate"},
                    {"code": "DE-160", "name": "Inventory and Appraisal", "purpose": "List and value all estate assets"},
                    {"code": "DE-165", "name": "Notice of Administration", "purpose": "Notice to creditors and beneficiaries"}
                ],
                "requirements": [
                    "Death certificate of the deceased",
                    "Original will (if one exists)",
                    "List of all assets and debts",
                    "Names and addresses of heirs/beneficiaries",
                    "Filing fee (varies by county, typically $435-$465)"
                ],
                "steps": [
                    "Determine if probate is required (assets over $184,500 in 2024)",
                    "File DE-111 Petition for Probate with the court",
                    "Publish notice in local newspaper for 3 weeks",
                    "Mail notices to all interested parties",
                    "Attend probate hearing (usually 6-8 weeks after filing)",
                    "Receive Letters Testamentary/Administration (DE-121)",
                    "Complete inventory and appraisal of assets (DE-160)",
                    "Pay debts and taxes",
                    "Distribute remaining assets to beneficiaries",
                    "File final accounting and petition for discharge"
                ],
                "links": [
                    {"text": "California Probate Self-Help", "url": "https://courts.ca.gov/selfhelp-probate"},
                    {"text": "Probate Forms", "url": "https://courts.ca.gov/forms/probate"},
                    {"text": "Small Estate Procedures", "url": "https://courts.ca.gov/selfhelp-probate-small-estate"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["small claims", "money", "debt", "collection", "sue"]):
            guidance.update({
                "description": "Small claims court handles disputes involving small amounts of money (up to $12,500 for individuals, $6,250 for businesses in California).",
                "forms": [
                    {"code": "SC-100", "name": "Plaintiff's Claim and ORDER to Go to Small Claims Court", "purpose": "Initial filing to start small claims case"},
                    {"code": "SC-104", "name": "Proof of Service", "purpose": "Proof that defendant was properly served"},
                    {"code": "SC-130", "name": "Defendant's Claim and ORDER to Go to Small Claims Court", "purpose": "Defendant's counter-claim"},
                    {"code": "SC-200", "name": "Notice of Motion to Vacate Judgment", "purpose": "Request to set aside judgment"}
                ],
                "requirements": [
                    "Amount must be $12,500 or less (individuals) or $6,250 or less (businesses)",
                    "Must have tried to resolve the dispute outside of court",
                    "Must sue in the correct county",
                    "Must serve the defendant properly"
                ],
                "steps": [
                    "Try to resolve the dispute without court",
                    "Complete SC-100 Plaintiff's Claim form",
                    "File the form and pay filing fee",
                    "Serve the defendant with court papers",
                    "Prepare for your court hearing",
                    "Attend the hearing and present your case"
                ],
                "links": [
                    {"text": "Small Claims Self-Help", "url": "https://courts.ca.gov/selfhelp-small-claims"},
                    {"text": "Small Claims Forms", "url": "https://courts.ca.gov/forms/small-claims"},
                    {"text": "Small Claims Advisor", "url": "https://courts.ca.gov/selfhelp-small-claims-advisor"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["eviction", "unlawful detainer", "tenant", "landlord", "rent"]):
            guidance.update({
                "description": "Unlawful detainer (eviction) cases involve removing tenants who have violated their lease or failed to pay rent.",
                "forms": [
                    {"code": "UD-100", "name": "Complaint—Unlawful Detainer", "purpose": "Landlord's initial filing to start eviction"},
                    {"code": "UD-105", "name": "Answer—Unlawful Detainer", "purpose": "Tenant's response to eviction complaint"},
                    {"code": "UD-110", "name": "Summons—Unlawful Detainer", "purpose": "Legal notice to tenant"},
                    {"code": "UD-115", "name": "Prejudgment Claim of Right to Possession", "purpose": "Notice to unknown occupants"}
                ],
                "requirements": [
                    "Proper notice must be given before filing (3-day, 30-day, or 60-day notice)",
                    "Landlord must follow specific legal procedures",
                    "Tenant has right to respond and defend",
                    "Court hearing required before eviction"
                ],
                "steps": [
                    "Serve proper notice to tenant (3-day, 30-day, or 60-day)",
                    "Wait for notice period to expire",
                    "File UD-100 Complaint with court",
                    "Serve tenant with summons and complaint",
                    "Tenant may file UD-105 Answer",
                    "Attend court hearing",
                    "If judgment granted, sheriff enforces eviction"
                ],
                "links": [
                    {"text": "Eviction Self-Help", "url": "https://courts.ca.gov/selfhelp-eviction"},
                    {"text": "Unlawful Detainer Forms", "url": "https://courts.ca.gov/forms/unlawful-detainer"},
                    {"text": "Tenant Rights", "url": "https://courts.ca.gov/selfhelp-eviction-tenant"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["jury", "jury duty", "juror", "jury service"]):
            guidance.update({
                "description": "Jury service is a civic duty in California. You may be summoned to serve on a jury in civil or criminal cases.",
                "forms": [
                    {"code": "JUR-505", "name": "Request for Excuse from Jury Service", "purpose": "Request to be excused from jury duty"},
                    {"code": "JUR-510", "name": "Request for Postponement", "purpose": "Request to postpone jury service to a later date"},
                    {"code": "JUR-515", "name": "Hardship Excuse Request", "purpose": "Request excuse due to financial or personal hardship"}
                ],
                "requirements": [
                    "Must be 18 years or older",
                    "Must be a U.S. citizen",
                    "Must be a resident of the county",
                    "Must be able to understand English",
                    "Cannot have been convicted of a felony (unless rights restored)"
                ],
                "steps": [
                    "Receive jury summons in the mail",
                    "Check if you qualify for automatic exemption",
                    "If requesting excuse, complete appropriate form",
                    "Submit excuse request with supporting documentation",
                    "If not excused, report on assigned date",
                    "Complete jury selection process if called"
                ],
                "links": [
                    {"text": "Jury Service Information", "url": "https://courts.ca.gov/jury"},
                    {"text": "Jury Duty Exemptions", "url": "https://courts.ca.gov/jury/exemptions"},
                    {"text": "Find Your Local Court", "url": "https://courts.ca.gov/find-my-court.htm"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["appeal", "appeals", "appellate"]):
            guidance.update({
                "description": "Appeals allow you to ask a higher court to review a lower court's decision. Strict deadlines and procedures must be followed.",
                "forms": [
                    {"code": "APP-101", "name": "Notice of Appeal", "purpose": "Initial filing to start appeal process"},
                    {"code": "APP-103", "name": "Abandonment of Appeal", "purpose": "To withdraw an appeal"},
                    {"code": "APP-104", "name": "Request for Extension of Time", "purpose": "Request more time for appeal deadlines"},
                    {"code": "APP-109", "name": "Notice of Election", "purpose": "Election to proceed with appeal"}
                ],
                "requirements": [
                    "Must file within 60 days of judgment (30 days for some cases)",
                    "Must have a final judgment or appealable order",
                    "Must pay filing fees or request fee waiver",
                    "Must follow strict procedural rules"
                ],
                "steps": [
                    "File APP-101 Notice of Appeal within deadline",
                    "Pay filing fees or request fee waiver",
                    "Order transcripts of trial proceedings",
                    "Prepare and file appellant's brief",
                    "Respond to respondent's brief",
                    "Attend oral argument (if scheduled)",
                    "Await appellate court decision"
                ],
                "links": [
                    {"text": "Appeals Self-Help", "url": "https://courts.ca.gov/selfhelp-appeals"},
                    {"text": "Appellate Forms", "url": "https://courts.ca.gov/forms/appellate"},
                    {"text": "Appellate Courts", "url": "https://courts.ca.gov/courts/appeal"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["conservatorship", "conservator"]):
            guidance.update({
                "description": "Conservatorship is a legal arrangement where a court appoints someone to manage the personal care and/or finances of an adult who cannot do so themselves.",
                "forms": [
                    {"code": "GC-110", "name": "Petition for Appointment of Probate Conservator", "purpose": "Initial petition for conservatorship"},
                    {"code": "GC-140", "name": "Order Appointing Probate Conservator", "purpose": "Court order appointing conservator"},
                    {"code": "GC-248", "name": "Duties of Conservator", "purpose": "Information about conservator responsibilities"},
                    {"code": "GC-340", "name": "Conservator's Inventory and Appraisal", "purpose": "List of conservatee's assets"}
                ],
                "requirements": [
                    "Conservatee must be unable to care for themselves or manage finances",
                    "Less restrictive alternatives must be considered",
                    "Medical evidence of incapacity required",
                    "Background check for proposed conservator",
                    "Court investigation required"
                ],
                "steps": [
                    "File GC-110 Petition for Conservatorship",
                    "Serve conservatee and interested parties",
                    "Complete court investigation",
                    "Attend conservatorship hearing",
                    "If granted, complete conservator duties training",
                    "File required ongoing reports"
                ],
                "links": [
                    {"text": "Conservatorship Self-Help", "url": "https://courts.ca.gov/selfhelp-conservatorship"},
                    {"text": "Conservatorship Forms", "url": "https://courts.ca.gov/forms/conservatorship"},
                    {"text": "Guardianship vs Conservatorship", "url": "https://courts.ca.gov/selfhelp-guardianship"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["gender change", "gender marker", "gender identity"]):
            guidance.update({
                "description": "California allows individuals to petition the court to change their gender marker on official documents and records.",
                "forms": [
                    {"code": "NC-200", "name": "Petition for Change of Gender and Issuance of New Birth Certificate", "purpose": "Request to change gender marker"},
                    {"code": "NC-210", "name": "Order for Change of Gender and Issuance of New Birth Certificate", "purpose": "Court order approving gender change"},
                    {"code": "NC-220", "name": "Supplemental Attachment", "purpose": "Additional information for gender change petition"}
                ],
                "requirements": [
                    "Must be 18 years or older (or have parent/guardian petition)",
                    "No requirement for medical treatment or surgery",
                    "Must provide sworn statement of gender identity",
                    "Filing fee required (fee waiver available)"
                ],
                "steps": [
                    "Complete NC-200 Petition for Change of Gender",
                    "File petition with superior court",
                    "Pay filing fee or request fee waiver",
                    "Attend court hearing (if required)",
                    "Receive NC-210 Order from court",
                    "Use court order to update other documents"
                ],
                "links": [
                    {"text": "Gender Change Information", "url": "https://courts.ca.gov/selfhelp-name-change"},
                    {"text": "Name and Gender Change Forms", "url": "https://courts.ca.gov/forms/name-change"},
                    {"text": "LGBTQ+ Resources", "url": "https://courts.ca.gov/selfhelp-legal-resources"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["parentage", "paternity", "parent", "father"]):
            guidance.update({
                "description": "Parentage cases establish the legal parent-child relationship, including paternity, custody, visitation, and support.",
                "forms": [
                    {"code": "FL-200", "name": "Petition to Establish Parental Relationship", "purpose": "Initial filing to establish parentage"},
                    {"code": "FL-220", "name": "Response to Petition", "purpose": "Response to parentage petition"},
                    {"code": "FL-235", "name": "Order After Hearing", "purpose": "Court order establishing parentage"},
                    {"code": "FL-260", "name": "Statement of Decision", "purpose": "Court's written decision on parentage"}
                ],
                "requirements": [
                    "Genetic testing may be required",
                    "Best interests of the child considered",
                    "Financial support obligations established",
                    "Custody and visitation arrangements determined"
                ],
                "steps": [
                    "File FL-200 Petition to Establish Parental Relationship",
                    "Serve other parent with petition",
                    "Complete genetic testing if ordered",
                    "Attend mediation for custody/visitation",
                    "Attend court hearing",
                    "Receive court order establishing parentage"
                ],
                "links": [
                    {"text": "Parentage Information", "url": "https://courts.ca.gov/selfhelp-parentage"},
                    {"text": "Family Law Forms", "url": "https://courts.ca.gov/forms/family"},
                    {"text": "Child Support Services", "url": "https://courts.ca.gov/selfhelp-support"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["elder abuse", "elder", "abuse of elderly"]):
            guidance.update({
                "description": "Elder abuse includes physical, emotional, financial abuse or neglect of adults 65 and older. California has specific legal protections and remedies.",
                "forms": [
                    {"code": "EA-100", "name": "Request for Elder or Dependent Adult Abuse Restraining Order", "purpose": "Request protection from elder abuse"},
                    {"code": "EA-110", "name": "Temporary Restraining Order", "purpose": "Immediate temporary protection"},
                    {"code": "EA-120", "name": "Response to Request", "purpose": "Response to elder abuse restraining order request"},
                    {"code": "EA-130", "name": "Elder or Dependent Adult Abuse Restraining Order", "purpose": "Final restraining order"},
                    {"code": "EA-140", "name": "Notice of Court Hearing", "purpose": "Notice of hearing date"}
                ],
                "requirements": [
                    "Victim must be 65 years or older (or dependent adult)",
                    "Evidence of abuse, neglect, or financial exploitation",
                    "Specific incidents with dates and details",
                    "Medical records or witness statements if available"
                ],
                "steps": [
                    "Complete EA-100 Request for Restraining Order",
                    "File forms with court clerk",
                    "Attend court hearing",
                    "If granted, ensure order is served on abuser",
                    "Report abuse to Adult Protective Services",
                    "Consider criminal charges if appropriate"
                ],
                "links": [
                    {"text": "Elder Abuse Restraining Orders", "url": "https://courts.ca.gov/selfhelp-elder-abuse"},
                    {"text": "Elder Abuse Forms", "url": "https://courts.ca.gov/forms/elder-abuse"},
                    {"text": "Adult Protective Services", "url": "https://courts.ca.gov/selfhelp-legal-resources"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["discovery", "subpoena", "subpoenas", "deposition"]):
            guidance.update({
                "description": "Discovery allows parties in a lawsuit to obtain information and evidence from each other and third parties through various legal procedures.",
                "forms": [
                    {"code": "DISC-001", "name": "Subpoena", "purpose": "Command someone to appear in court or produce documents"},
                    {"code": "DISC-002", "name": "Subpoena for Production of Business Records", "purpose": "Obtain business records from third parties"},
                    {"code": "DISC-003", "name": "Subpoena (Personal Appearance)", "purpose": "Require someone to appear and testify"},
                    {"code": "DISC-004", "name": "Proof of Service", "purpose": "Proof that subpoena was properly served"}
                ],
                "requirements": [
                    "Must be part of pending litigation",
                    "Information sought must be relevant to the case",
                    "Proper service required",
                    "Reasonable time for compliance must be given"
                ],
                "steps": [
                    "Determine what information is needed",
                    "Complete appropriate discovery form",
                    "Serve discovery requests on opposing party or third party",
                    "Allow time for response",
                    "File motion to compel if no response",
                    "Use obtained information in court proceedings"
                ],
                "links": [
                    {"text": "Discovery Information", "url": "https://courts.ca.gov/selfhelp-discovery"},
                    {"text": "Civil Forms", "url": "https://courts.ca.gov/forms/civil"},
                    {"text": "Subpoena Information", "url": "https://courts.ca.gov/selfhelp-subpoenas"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["enforcement", "judgment", "collect", "collection"]):
            guidance.update({
                "description": "After winning a court case, you may need to take additional steps to collect the money or enforce the court's judgment.",
                "forms": [
                    {"code": "EJ-001", "name": "Abstract of Judgment", "purpose": "Create a lien on debtor's real property"},
                    {"code": "EJ-130", "name": "Writ of Execution", "purpose": "Authorize sheriff to seize debtor's property"},
                    {"code": "EJ-150", "name": "Application and Order for Appearance and Examination", "purpose": "Require debtor to appear and answer questions about assets"},
                    {"code": "EJ-160", "name": "Earnings Withholding Order", "purpose": "Garnish debtor's wages"}
                ],
                "requirements": [
                    "Must have a valid court judgment",
                    "Judgment must not be stayed or under appeal",
                    "Must know debtor's assets or income sources",
                    "Must follow proper legal procedures"
                ],
                "steps": [
                    "Obtain certified copy of judgment",
                    "Locate debtor's assets or income",
                    "Choose appropriate enforcement method",
                    "Complete and file enforcement forms",
                    "Serve required parties",
                    "Collect money through legal process"
                ],
                "links": [
                    {"text": "Collecting Your Judgment", "url": "https://courts.ca.gov/selfhelp-enforcement"},
                    {"text": "Enforcement Forms", "url": "https://courts.ca.gov/forms/enforcement"},
                    {"text": "Small Claims Collection", "url": "https://courts.ca.gov/selfhelp-small-claims"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["remote appearance", "remote", "video", "zoom", "virtual"]):
            guidance.update({
                "description": "California courts allow remote appearances for many types of hearings using video or audio technology, especially since COVID-19.",
                "forms": [
                    {"code": "RA-010", "name": "Request for Remote Appearance", "purpose": "Request to appear remotely at hearing"},
                    {"code": "RA-020", "name": "Order on Remote Appearance", "purpose": "Court order allowing or denying remote appearance"},
                    {"code": "RA-030", "name": "Remote Appearance Information", "purpose": "Instructions for remote appearance technology"}
                ],
                "requirements": [
                    "Court must allow remote appearances for the hearing type",
                    "Must have reliable internet connection and device",
                    "Must request remote appearance in advance (usually)",
                    "Must follow court's technology requirements"
                ],
                "steps": [
                    "Check if your hearing type allows remote appearance",
                    "File RA-010 Request for Remote Appearance (if required)",
                    "Receive court approval and technology instructions",
                    "Test technology before hearing date",
                    "Join hearing at scheduled time",
                    "Follow court's remote appearance rules"
                ],
                "links": [
                    {"text": "Remote Appearance Information", "url": "https://courts.ca.gov/selfhelp-remote"},
                    {"text": "Technology Requirements", "url": "https://courts.ca.gov/technology"},
                    {"text": "COVID-19 Court Changes", "url": "https://courts.ca.gov/covid19"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["cleaning criminal record", "expunge", "expungement", "seal record"]):
            guidance.update({
                "description": "California allows certain criminal records to be sealed, dismissed, or expunged under specific circumstances to help with employment and housing.",
                "forms": [
                    {"code": "CR-180", "name": "Petition to Dismiss Misdemeanor", "purpose": "Request dismissal of misdemeanor conviction"},
                    {"code": "CR-181", "name": "Order to Dismiss", "purpose": "Court order dismissing conviction"},
                    {"code": "CR-409", "name": "Petition to Seal and Destroy Arrest Records", "purpose": "Seal arrest records when not convicted"},
                    {"code": "CR-410", "name": "Order to Seal and Destroy Records", "purpose": "Court order to seal records"}
                ],
                "requirements": [
                    "Must have completed probation successfully",
                    "Cannot have pending criminal charges",
                    "Certain serious crimes are not eligible",
                    "Must not be currently serving a sentence"
                ],
                "steps": [
                    "Determine eligibility for record relief",
                    "Obtain certified copies of court records",
                    "Complete appropriate petition form",
                    "File petition with court",
                    "Serve district attorney if required",
                    "Attend court hearing if scheduled"
                ],
                "links": [
                    {"text": "Criminal Record Relief", "url": "https://courts.ca.gov/selfhelp-criminal-record"},
                    {"text": "Criminal Forms", "url": "https://courts.ca.gov/forms/criminal"},
                    {"text": "Expungement Information", "url": "https://courts.ca.gov/selfhelp-expungement"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["language access", "interpreter", "translation"]):
            guidance.update({
                "description": "California courts provide free interpreters for parties and witnesses who need language assistance in court proceedings.",
                "forms": [
                    {"code": "INT-100", "name": "Request for Interpreter", "purpose": "Request court-provided interpreter"},
                    {"code": "INT-110", "name": "Notice of Availability of Interpreter", "purpose": "Court notice about interpreter services"},
                    {"code": "INT-120", "name": "Interpreter Information", "purpose": "Information about interpreter services"}
                ],
                "requirements": [
                    "Must demonstrate need for language assistance",
                    "Available for all court proceedings",
                    "Free of charge for parties and witnesses",
                    "Must request in advance when possible"
                ],
                "steps": [
                    "Complete INT-100 Request for Interpreter",
                    "File request with court clerk",
                    "Specify language needed",
                    "Provide advance notice when possible",
                    "Confirm interpreter availability before hearing",
                    "Arrive early on hearing date"
                ],
                "links": [
                    {"text": "Court Interpreters", "url": "https://courts.ca.gov/programs-interpreters"},
                    {"text": "Language Access Services", "url": "https://courts.ca.gov/programs-language"},
                    {"text": "Interpreter Request Forms", "url": "https://courts.ca.gov/forms/interpreters"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["proof of service", "service", "serving papers"]):
            guidance.update({
                "description": "Proof of service shows the court that legal documents were properly delivered to all required parties in a case.",
                "forms": [
                    {"code": "POS-010", "name": "Proof of Service of Summons", "purpose": "Prove summons was served on defendant"},
                    {"code": "POS-020", "name": "Proof of Personal Service", "purpose": "Prove documents were personally served"},
                    {"code": "POS-030", "name": "Proof of Service by Mail", "purpose": "Prove documents were served by mail"},
                    {"code": "FL-335", "name": "Proof of Service by Mail (Family Law)", "purpose": "Family law proof of service by mail"}
                ],
                "requirements": [
                    "Must serve all required parties",
                    "Must use proper method of service",
                    "Server must be over 18 and not a party to the case",
                    "Must file proof of service with court"
                ],
                "steps": [
                    "Determine who must be served",
                    "Choose appropriate method of service",
                    "Have documents served by qualified person",
                    "Complete proof of service form",
                    "File proof of service with court",
                    "Keep copies for your records"
                ],
                "links": [
                    {"text": "Service of Process", "url": "https://courts.ca.gov/selfhelp-service"},
                    {"text": "Proof of Service Forms", "url": "https://courts.ca.gov/forms/service"},
                    {"text": "How to Serve Papers", "url": "https://courts.ca.gov/selfhelp-serving-papers"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["juvenile", "minor", "youth court"]):
            guidance.update({
                "description": "Juvenile court handles cases involving minors under 18, including delinquency, dependency, and status offense cases.",
                "forms": [
                    {"code": "JV-100", "name": "Juvenile Petition", "purpose": "Initial petition in juvenile case"},
                    {"code": "JV-110", "name": "Notice of Hearing", "purpose": "Notice of juvenile court hearing"},
                    {"code": "JV-120", "name": "Juvenile Court Order", "purpose": "Court order in juvenile case"},
                    {"code": "JV-130", "name": "Juvenile Disposition Report", "purpose": "Report for juvenile disposition hearing"}
                ],
                "requirements": [
                    "Minor must be under 18 years old",
                    "Parent or guardian involvement required",
                    "Right to attorney (appointed if needed)",
                    "Confidential proceedings in most cases"
                ],
                "steps": [
                    "Petition filed by prosecutor or probation",
                    "Detention hearing (if minor in custody)",
                    "Arraignment and plea",
                    "Adjudication hearing (trial)",
                    "Disposition hearing (sentencing)",
                    "Follow-up hearings as needed"
                ],
                "links": [
                    {"text": "Juvenile Court Information", "url": "https://courts.ca.gov/selfhelp-juvenile"},
                    {"text": "Juvenile Forms", "url": "https://courts.ca.gov/forms/juvenile"},
                    {"text": "Youth Rights in Court", "url": "https://courts.ca.gov/selfhelp-youth-rights"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["civil", "civil case", "civil lawsuit", "civil court"]) and not any(word in question_lower for word in ["harassment", "domestic"]):
            guidance.update({
                "description": "Civil cases involve disputes between individuals, businesses, or organizations seeking money damages or other remedies (not criminal penalties).",
                "forms": [
                    {"code": "CM-010", "name": "Civil Case Cover Sheet", "purpose": "Required cover sheet for civil cases"},
                    {"code": "SUM-100", "name": "Summons", "purpose": "Official notice to defendant of lawsuit"},
                    {"code": "PLD-C-001", "name": "Complaint", "purpose": "Document stating your claims against defendant"},
                    {"code": "PLD-050", "name": "General Denial", "purpose": "Defendant's response denying allegations"}
                ],
                "requirements": [
                    "Must have legal basis for claim",
                    "Must serve defendant properly",
                    "Must file within statute of limitations",
                    "Must pay filing fees or request fee waiver"
                ],
                "steps": [
                    "Determine if you have a valid legal claim",
                    "Complete CM-010 Civil Case Cover Sheet",
                    "Prepare and file complaint",
                    "Serve defendant with summons and complaint",
                    "Await defendant's response",
                    "Proceed with discovery and trial preparation"
                ],
                "links": [
                    {"text": "Civil Case Information", "url": "https://courts.ca.gov/selfhelp-civil"},
                    {"text": "Civil Forms", "url": "https://courts.ca.gov/forms/civil"},
                    {"text": "Small Claims vs Civil Court", "url": "https://courts.ca.gov/selfhelp-small-claims"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["fee waiver", "fee waivers", "waive fees", "cannot afford"]):
            guidance.update({
                "description": "California courts provide fee waivers for people who cannot afford court filing fees and other court costs.",
                "forms": [
                    {"code": "FW-001", "name": "Request to Waive Court Fees", "purpose": "Request waiver of court fees"},
                    {"code": "FW-002", "name": "Order on Court Fee Waiver", "purpose": "Court order granting or denying fee waiver"},
                    {"code": "FW-003", "name": "Additional Information for Fee Waiver", "purpose": "Additional financial information if needed"}
                ],
                "requirements": [
                    "Must meet income guidelines (usually 125% of federal poverty level)",
                    "Must provide financial information",
                    "Must be unable to pay fees without hardship",
                    "Must update court if financial situation changes"
                ],
                "steps": [
                    "Complete FW-001 Request to Waive Court Fees",
                    "Gather financial documents (pay stubs, benefits statements)",
                    "File fee waiver request with court",
                    "Wait for court decision",
                    "If denied, you can request hearing",
                    "If granted, keep order for your records"
                ],
                "links": [
                    {"text": "Fee Waiver Information", "url": "https://courts.ca.gov/selfhelp-fee-waiver"},
                    {"text": "Fee Waiver Forms", "url": "https://courts.ca.gov/forms/fee-waiver"},
                    {"text": "Income Guidelines", "url": "https://courts.ca.gov/selfhelp-fee-waiver-income"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["guardianship", "guardian", "minor guardianship"]):
            guidance.update({
                "description": "Guardianship gives an adult legal authority to care for a minor child when parents cannot provide care or have died.",
                "forms": [
                    {"code": "GC-210", "name": "Petition for Appointment of Guardian of Minor", "purpose": "Initial petition for guardianship"},
                    {"code": "GC-240", "name": "Order Appointing Guardian of Minor", "purpose": "Court order appointing guardian"},
                    {"code": "GC-248", "name": "Duties of Guardian", "purpose": "Information about guardian responsibilities"},
                    {"code": "GC-255", "name": "Confidential Guardian Screening Form", "purpose": "Background information for proposed guardian"}
                ],
                "requirements": [
                    "Child must be under 18 years old",
                    "Parents unable to care for child or consent to guardianship",
                    "Guardianship must be in child's best interests",
                    "Background check for proposed guardian required"
                ],
                "steps": [
                    "File GC-210 Petition for Guardianship",
                    "Complete background check and screening",
                    "Serve parents and interested parties",
                    "Attend court hearing",
                    "If granted, complete guardian duties training",
                    "File required ongoing reports"
                ],
                "links": [
                    {"text": "Guardianship Information", "url": "https://courts.ca.gov/selfhelp-guardianship"},
                    {"text": "Guardianship Forms", "url": "https://courts.ca.gov/forms/guardianship"},
                    {"text": "Guardianship vs Adoption", "url": "https://courts.ca.gov/selfhelp-guardianship-adoption"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["name change", "change name", "legal name"]):
            guidance.update({
                "description": "California allows adults and minors to petition the court to legally change their name for various reasons.",
                "forms": [
                    {"code": "NC-100", "name": "Petition for Change of Name", "purpose": "Request to change legal name"},
                    {"code": "NC-110", "name": "Order to Show Cause for Change of Name", "purpose": "Court order setting hearing date"},
                    {"code": "NC-120", "name": "Decree Changing Name", "purpose": "Final court order approving name change"},
                    {"code": "NC-125", "name": "Supplemental Attachment", "purpose": "Additional information for name change petition"}
                ],
                "requirements": [
                    "Must be California resident",
                    "Cannot change name to defraud creditors",
                    "Cannot change name for illegal purposes",
                    "Must publish notice in newspaper (unless waived)"
                ],
                "steps": [
                    "Complete NC-100 Petition for Change of Name",
                    "File petition with superior court",
                    "Pay filing fee or request fee waiver",
                    "Publish notice in newspaper (if required)",
                    "Attend court hearing",
                    "Receive NC-120 Decree Changing Name"
                ],
                "links": [
                    {"text": "Name Change Information", "url": "https://courts.ca.gov/selfhelp-name-change"},
                    {"text": "Name Change Forms", "url": "https://courts.ca.gov/forms/name-change"},
                    {"text": "Name Change for Minors", "url": "https://courts.ca.gov/selfhelp-name-change-minor"}
                ]
            })
        
        elif any(keyword in question_lower for keyword in ["traffic", "traffic court", "traffic ticket", "citation"]):
            guidance.update({
                "description": "Traffic court handles violations of vehicle and traffic laws, including speeding tickets, parking violations, and driving infractions.",
                "forms": [
                    {"code": "TR-100", "name": "Notice to Appear", "purpose": "Citation requiring court appearance"},
                    {"code": "TR-110", "name": "Request for Trial by Written Declaration", "purpose": "Contest ticket without appearing in court"},
                    {"code": "TR-120", "name": "Request for New Trial", "purpose": "Request new trial after written declaration"},
                    {"code": "TR-130", "name": "Ability to Pay Application", "purpose": "Request payment plan or community service"}
                ],
                "requirements": [
                    "Must respond to citation by due date",
                    "Must pay fines or contest citation",
                    "May need to complete traffic school",
                    "License may be suspended for non-compliance"
                ],
                "steps": [
                    "Read citation carefully for due date and options",
                    "Decide whether to pay fine or contest citation",
                    "If contesting, file TR-110 for trial by declaration",
                    "Submit evidence and written statement",
                    "Await court decision",
                    "If found guilty, pay fine or request payment plan"
                ],
                "links": [
                    {"text": "Traffic Court Information", "url": "https://courts.ca.gov/selfhelp-traffic"},
                    {"text": "Traffic Forms", "url": "https://courts.ca.gov/forms/traffic"},
                    {"text": "Traffic School Information", "url": "https://courts.ca.gov/selfhelp-traffic-school"}
                ]
            })
        
        else:
            guidance.update({
                "description": "For general legal matters in California courts, follow these basic steps.",
                "steps": [
                    "Identify the correct court (family, civil, criminal, etc.)",
                    "Determine required forms for your specific situation",
                    "Gather necessary documentation",
                    "Consider if you need legal representation",
                    "Check filing fees and fee waiver options"
                ],
                "links": [
                    {"text": "California Courts Self-Help", "url": "https://courts.ca.gov/selfhelp"},
                    {"text": "Find Court Forms", "url": "https://courts.ca.gov/rules-forms/find-your-court-forms"}
                ]
            })
        
        return guidance

# Initialize the legal agent API
legal_agent = LegalAgentAPI()

@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')

@app.route('/api/ask', methods=['POST'])
def ask_question():
    """Handle legal questions from the frontend."""
    try:
        data = request.get_json()
        question = data.get('question', '')
        
        if not question:
            return jsonify({"error": "No question provided"}), 400
        
        # Get guidance based on question
        guidance = legal_agent.get_guidance_for_question(question)
        
        # Search for relevant forms using our vector database agent
        search_result = legal_agent.search_forms(question, limit=5)
        
        # Try to enhance guidance with vector search results
        if search_result and search_result.get("status") == "success":
            guidance["vector_enhanced"] = True
            guidance["search_performed"] = True
            guidance["relevant_forms"] = search_result.get("forms", [])
        else:
            guidance["vector_enhanced"] = False
            guidance["search_performed"] = False
            guidance["relevant_forms"] = []
        
        response = {
            "question": question,
            "guidance": guidance,
            "search_status": search_result.get("status", "unknown"),
            "vector_response": search_result
        }
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/search', methods=['POST'])
def search_forms():
    """Search for specific forms or topics."""
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({"error": "No search query provided"}), 400
        
        # Search using our vector database agent
        result = legal_agent.search_forms(query, limit=10)
        
        # Extract forms from vector search result
        forms = []
        if result and result.get("status") == "success":
            forms = result.get("forms", [])
        
        return jsonify({
            "query": query,
            "forms": forms,
            "total_found": len(forms),
            "raw_result": result
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/crawl', methods=['POST'])
def crawl_forms():
    """Trigger crawling of court forms."""
    try:
        data = request.get_json()
        crawl_type = data.get('type', 'single')  # 'single', 'smart', or 'popular'
        
        if crawl_type == 'popular':
            # Crawl all 26 popular topics using correct search URLs
            popular_topics = [
                "adoption", "appeals", "child custody and visitation", "child support", 
                "civil", "civil harassment", "cleaning criminal record", "conservatorship",
                "discovery and subpoenas", "divorce", "domestic violence", "elder abuse",
                "enforcement of judgment", "eviction", "fee waivers", "gender change",
                "guardianship", "juvenile", "language access", "name change",
                "parentage", "probate", "proof of service", "remote appearance",
                "small claims", "traffic"
            ]
            
            results = []
            for topic in popular_topics:
                search_url = f"https://selfhelp.courts.ca.gov/find-forms?query={topic.replace(' ', '+')}"
                result = legal_agent.call_mcp_tool("crawl_single_page", {
                    "url": search_url
                })
                results.append({
                    "topic": topic,
                    "url": search_url,
                    "result": result
                })
            
            return jsonify({
                "crawl_type": "popular_topics",
                "topics_crawled": len(popular_topics),
                "results": results
            })
            
        elif crawl_type == 'smart':
            # Use the correct base URL for smart crawling
            result = legal_agent.call_mcp_tool("smart_crawl_url", {
                "url": "https://selfhelp.courts.ca.gov/find-forms",
                "max_depth": 2,
                "max_concurrent": 5
            })
        else:
            # Single page crawl of the main forms page
            result = legal_agent.call_mcp_tool("crawl_single_page", {
                "url": "https://selfhelp.courts.ca.gov/find-forms"
            })
        
        return jsonify({
            "crawl_type": crawl_type,
            "result": result
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/sources', methods=['GET'])
def get_sources():
    """Get available data sources."""
    try:
        result = legal_agent.call_mcp_tool("get_available_sources", {})
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_database_stats():
    """Get vector database statistics."""
    try:
        stats = legal_agent.court_agent.get_database_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/topics', methods=['GET'])
def get_topics():
    """Get available topics from the vector database."""
    try:
        topics = legal_agent.court_agent.get_available_topics()
        return jsonify({
            "topics": topics,
            "total_topics": len(topics)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/search_by_topic', methods=['POST'])
def search_by_topic():
    """Search forms by specific topic."""
    try:
        data = request.get_json()
        topic = data.get('topic', '')
        limit = data.get('limit', 10)
        
        if not topic:
            return jsonify({"error": "No topic provided"}), 400
        
        # Search by topic using our vector database agent
        results = legal_agent.court_agent.search_by_topic(topic, limit=limit)
        
        # Format results for frontend
        formatted_results = []
        for result in results:
            formatted_results.append({
                "code": result.get('form_code', 'Unknown'),
                "title": result.get('title', 'Unknown Form'),
                "topic": result.get('topic', 'Unknown'),
                "url": result.get('url', ''),
                "content": result.get('content', '')[:200] + "..." if len(result.get('content', '')) > 200 else result.get('content', '')
            })
        
        return jsonify({
            "topic": topic,
            "forms": formatted_results,
            "total_found": len(formatted_results)
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🏛️  Starting California Legal Forms Assistant Web Server")
    print("📱 Frontend will be available at: http://localhost:5000")
    print("🗄️  Using Vector Database with 718 forms across 26 topics")
    print("🔌 MCP server fallback available on localhost:8051")
    app.run(debug=True, host='0.0.0.0', port=5000) 