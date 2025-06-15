#!/usr/bin/env python3
"""
Comprehensive Legal Forms Crawler for California Courts

This crawler enhances the existing hardcoded responses by:
1. Extracting structured form listings from search results
2. Following "See form info" links to get detailed information
3. Storing PDF download links and files in Supabase Storage
4. Using open source embeddings (all-MiniLM-L6-v2) for vector search
5. Keeping all links for user reference
6. Verifying storage before proceeding
7. Working with existing MCP server table structure
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus, urljoin, urlparse
from playwright.sync_api import sync_playwright
from sentence_transformers import SentenceTransformer
from supabase import create_client, Client
import re

class ComprehensiveLegalCrawler:
    def __init__(self):
        """Initialize the comprehensive legal crawler."""
        
        # 26 Popular Topics from California Courts
        self.popular_topics = [
            "adoption", "appeals", "child custody and visitation", "child support", 
            "civil", "civil harassment", "cleaning criminal record", "conservatorship",
            "discovery and subpoenas", "divorce", "domestic violence", "elder abuse",
            "enforcement of judgment", "eviction", "fee waivers", "gender change",
            "guardianship", "juvenile", "language access", "name change",
            "parentage", "probate", "proof of service", "remote appearance",
            "small claims", "traffic"
        ]
        
        # URLs and configuration
        self.base_search_url = "https://selfhelp.courts.ca.gov/find-forms?query="
        self.base_domain = "https://selfhelp.courts.ca.gov"
        
        # Initialize open source embedding model
        print("🤖 Loading open source embedding model (all-MiniLM-L6-v2)...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Open source embedding model loaded successfully!")
        
        # Initialize Supabase client
        self.supabase_client = None
        self.init_supabase()
        
        # Storage configuration
        self.pdf_storage_bucket = "legal-forms-pdfs"
        self.create_storage_bucket()
        
        # Progress tracking
        self.stats = {
            "topics_processed": 0,
            "forms_found": 0,
            "form_details_extracted": 0,
            "pdfs_stored": 0,
            "chunks_stored": 0,
            "errors": []
        }
    
    def init_supabase(self):
        """Initialize Supabase client and create tables if needed."""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("❌ SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment variables")
        
        try:
            self.supabase_client = create_client(supabase_url, supabase_key)
            print("✅ Supabase connection established!")
            
            # Try to create tables if they don't exist
            self.ensure_tables_exist()
            
        except Exception as e:
            print(f"❌ Failed to initialize Supabase client: {e}")
            raise
    
    def ensure_tables_exist(self):
        """Ensure required tables exist, create them if they don't."""
        print("🔧 Ensuring required tables exist...")
        
        # First, create sources table (required for foreign key)
        try:
            # Test if sources table exists
            result = self.supabase_client.table('sources').select('source_id').limit(1).execute()
            print("✅ sources table exists")
        except:
            print("📄 Creating sources table...")
            # Create a simple source record
            try:
                source_data = {
                    'source_id': 'california_courts_comprehensive',
                    'summary': 'California Courts comprehensive legal forms database',
                    'total_word_count': 0
                }
                # This will fail if table doesn't exist, but that's expected
                result = self.supabase_client.table('sources').insert(source_data).execute()
                print("✅ sources table created and populated")
            except Exception as e:
                print(f"⚠️  Could not create sources table: {e}")
        
        # Try to use crawled_pages table (compatible with MCP server)
        try:
            result = self.supabase_client.table('crawled_pages').select('id').limit(1).execute()
            print("✅ crawled_pages table exists and accessible")
            self.table_name = 'crawled_pages'
        except:
            print("⚠️  crawled_pages table not accessible")
            # Try documents table as fallback
            try:
                result = self.supabase_client.table('documents').select('id').limit(1).execute()
                print("✅ documents table exists and accessible")
                self.table_name = 'documents'
            except:
                print("❌ No accessible tables found")
                print("🔧 You may need to create tables manually in Supabase dashboard")
                print("📋 Required schema:")
                print("""
                CREATE TABLE sources (
                    source_id TEXT PRIMARY KEY,
                    summary TEXT,
                    total_word_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                
                CREATE TABLE crawled_pages (
                    id BIGSERIAL PRIMARY KEY,
                    url VARCHAR NOT NULL,
                    chunk_number INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    source_id TEXT NOT NULL,
                    embedding VECTOR(384),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(url, chunk_number),
                    FOREIGN KEY (source_id) REFERENCES sources(source_id)
                );
                """)
                # For now, let's continue and store data in memory
                self.table_name = None
                print("⚠️  Will store data in memory only for this run")
    
    def create_storage_bucket(self):
        """Create storage bucket for PDFs if it doesn't exist."""
        try:
            # Try to get bucket info
            self.supabase_client.storage.get_bucket(self.pdf_storage_bucket)
            print(f"✅ Storage bucket '{self.pdf_storage_bucket}' already exists")
        except:
            try:
                # Create bucket if it doesn't exist
                self.supabase_client.storage.create_bucket(
                    self.pdf_storage_bucket,
                    options={"public": True}
                )
                print(f"✅ Created storage bucket '{self.pdf_storage_bucket}'")
            except Exception as e:
                print(f"⚠️  Could not create storage bucket: {e}")
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings using open source sentence-transformers model."""
        try:
            print(f"🔢 Creating embeddings for {len(texts)} texts using open source model...")
            embeddings = self.embedding_model.encode(texts, convert_to_tensor=False)
            return embeddings.tolist()
        except Exception as e:
            print(f"❌ Error creating embeddings: {e}")
            return [[0.0] * 384] * len(texts)  # all-MiniLM-L6-v2 has 384 dimensions
    
    def extract_form_details(self, form_info_url: str, form_code: str) -> Dict[str, Any]:
        """Extract detailed information from 'See form info' page."""
        try:
            print(f"📋 Extracting details for {form_code} from: {form_info_url}")
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                page.goto(form_info_url)
                page.wait_for_load_state("networkidle")
                
                # Extract detailed information
                details = {
                    "form_code": form_code,
                    "form_info_url": form_info_url,
                    "description": "",
                    "purpose": "",
                    "instructions": "",
                    "requirements": [],
                    "related_forms": [],
                    "download_links": [],
                    "full_content": ""
                }
                
                # Get the full page content
                full_content = page.inner_text("body")
                details["full_content"] = full_content
                
                # Extract description/purpose (usually in the first paragraph or section)
                description_selectors = [
                    "p:first-of-type",
                    ".form-description",
                    ".description",
                    "div:has-text('Purpose')",
                    "div:has-text('Description')"
                ]
                
                for selector in description_selectors:
                    try:
                        element = page.query_selector(selector)
                        if element:
                            text = element.inner_text().strip()
                            if len(text) > 20:  # Only use substantial text
                                details["description"] = text
                                break
                    except:
                        continue
                
                # Extract download links
                download_links = page.query_selector_all("a[href*='.pdf'], a:has-text('Download'), a:has-text('PDF')")
                for link in download_links:
                    try:
                        href = link.get_attribute("href")
                        text = link.inner_text().strip()
                        if href:
                            full_url = urljoin(self.base_domain, href) if not href.startswith("http") else href
                            details["download_links"].append({
                                "text": text,
                                "url": full_url,
                                "is_pdf": ".pdf" in href.lower()
                            })
                    except:
                        continue
                
                # Extract related forms (look for other form codes mentioned)
                form_code_pattern = r'\b[A-Z]{2,}-\d{3}[A-Z]?\b'
                related_codes = re.findall(form_code_pattern, full_content)
                details["related_forms"] = list(set(related_codes))
                
                browser.close()
                
                print(f"✅ Extracted details for {form_code}: {len(details['download_links'])} download links")
                return details
                
        except Exception as e:
            print(f"❌ Error extracting details for {form_code}: {e}")
            return {
                "form_code": form_code,
                "form_info_url": form_info_url,
                "error": str(e)
            }
    
    def store_pdf_in_storage(self, pdf_url: str, form_code: str, topic: str) -> Optional[str]:
        """Store PDF file in Supabase storage and return public URL."""
        try:
            print(f"📁 Storing PDF for {form_code}...")
            
            # Download PDF
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()
            
            # Create file path
            file_name = f"{topic.replace(' ', '_')}/{form_code}.pdf"
            
            # Upload to Supabase storage
            result = self.supabase_client.storage.from_(self.pdf_storage_bucket).upload(
                file_name, 
                response.content,
                file_options={"content-type": "application/pdf", "upsert": True}
            )
            
            # Get public URL
            storage_url = self.supabase_client.storage.from_(self.pdf_storage_bucket).get_public_url(file_name)
            print(f"✅ PDF stored: {file_name}")
            self.stats["pdfs_stored"] += 1
            return storage_url
                
        except Exception as e:
            print(f"❌ Error storing PDF for {form_code}: {e}")
            return None
    
    def crawl_topic_forms(self, topic: str) -> List[Dict[str, Any]]:
        """Crawl forms for a specific topic and extract comprehensive information."""
        search_url = f"{self.base_search_url}{quote_plus(topic)}"
        print(f"\n🔍 Crawling topic: {topic}")
        print(f"📍 Search URL: {search_url}")
        
        forms_data = []
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Navigate to search results
                page.goto(search_url)
                page.wait_for_load_state("networkidle")
                
                # Extract the search results content
                search_content = page.inner_text("body")
                
                # Wait for forms to load
                page.wait_for_selector("ul li", timeout=10000)
                
                # Extract form information from the structured listing
                form_elements = page.query_selector_all("ul li")
                
                for form_element in form_elements:
                    try:
                        form_text = form_element.inner_text().strip()
                        
                        # Skip if this doesn't look like a form entry
                        if not any(char.isalpha() for char in form_text[:20]):
                            continue
                        
                        # Extract form code (first word that looks like a form code)
                        form_code = ""
                        lines = form_text.split('\n')
                        for line in lines:
                            line = line.strip()
                            if re.match(r'^[A-Z]{2,}-\d{3}[A-Z]?', line):
                                form_code = line.split()[0]
                                break
                        
                        if not form_code:
                            continue
                        
                        # Extract form title (usually the line after the form code)
                        form_title = ""
                        for i, line in enumerate(lines):
                            if form_code in line and i + 1 < len(lines):
                                form_title = lines[i + 1].strip()
                                break
                        
                        # Extract effective date
                        effective_date = ""
                        effective_match = re.search(r'Effective:\s*([^\n]+)', form_text)
                        if effective_match:
                            effective_date = effective_match.group(1).strip()
                        
                        # Extract available languages
                        languages = []
                        language_indicators = ["汉语", "한국어", "español", "Tiếng Việt"]
                        for lang in language_indicators:
                            if lang in form_text:
                                languages.append(lang)
                        
                        # Check if mandatory
                        mandatory = "*" in form_text and form_code in form_text
                        
                        # Find "See form info" and "Download" links
                        form_info_url = ""
                        download_url = ""
                        
                        links = form_element.query_selector_all("a")
                        for link in links:
                            link_text = link.inner_text().strip().lower()
                            href = link.get_attribute("href")
                            
                            if href:
                                full_url = urljoin(self.base_domain, href) if not href.startswith("http") else href
                                
                                if "form info" in link_text or "see form" in link_text:
                                    form_info_url = full_url
                                elif "download" in link_text or ".pdf" in href.lower():
                                    download_url = full_url
                        
                        # Create form data structure
                        form_data = {
                            "topic": topic,
                            "form_code": form_code,
                            "form_title": form_title,
                            "effective_date": effective_date,
                            "languages": languages,
                            "mandatory": mandatory,
                            "search_url": search_url,
                            "form_info_url": form_info_url,
                            "download_url": download_url,
                            "raw_text": form_text,
                            "search_content": search_content  # Include full search page content
                        }
                        
                        # Extract detailed information from "See form info" page
                        if form_info_url:
                            try:
                                details = self.extract_form_details(form_info_url, form_code)
                                form_data.update(details)
                                self.stats["form_details_extracted"] += 1
                            except Exception as e:
                                print(f"⚠️  Could not extract details for {form_code}: {e}")
                        
                        forms_data.append(form_data)
                        
                    except Exception as e:
                        print(f"⚠️  Error processing form element: {e}")
                        continue
                
                browser.close()
                
        except Exception as e:
            print(f"❌ Error crawling topic '{topic}': {e}")
            self.stats["errors"].append(f"Topic '{topic}': {str(e)}")
            return []
        
        print(f"✅ Found {len(forms_data)} forms for topic: {topic}")
        self.stats["forms_found"] += len(forms_data)
        return forms_data
    
    def process_and_store_forms(self, forms_data: List[Dict[str, Any]], topic: str) -> bool:
        """Process forms data and store in Supabase with embeddings."""
        if not forms_data:
            return True
        
        print(f"\n📦 Processing {len(forms_data)} forms for topic: {topic}")
        
        documents_to_store = []
        
        for form in forms_data:
            try:
                # Store PDF if available
                pdf_storage_url = ""
                if form.get('download_url') and '.pdf' in form['download_url'].lower():
                    pdf_storage_url = self.store_pdf_in_storage(
                        form['download_url'], 
                        form['form_code'], 
                        form['topic']
                    ) or ""
                
                # Create comprehensive content for embedding
                content_parts = [
                    f"Topic: {form['topic']}",
                    f"Form Code: {form['form_code']}",
                    f"Form Title: {form['form_title']}",
                    f"Effective Date: {form['effective_date']}",
                    f"Languages Available: {', '.join(form['languages'])}",
                    f"Mandatory: {'Yes' if form['mandatory'] else 'No'}"
                ]
                
                # Add detailed information if available
                if form.get('description'):
                    content_parts.append(f"Description: {form['description']}")
                
                if form.get('purpose'):
                    content_parts.append(f"Purpose: {form['purpose']}")
                
                if form.get('related_forms'):
                    content_parts.append(f"Related Forms: {', '.join(form['related_forms'])}")
                
                # Add raw text content
                if form.get('raw_text'):
                    content_parts.append(f"Form Details: {form['raw_text']}")
                
                # Add full content from form info page if available
                if form.get('full_content'):
                    content_parts.append(f"Additional Information: {form['full_content'][:2000]}")  # Limit to 2000 chars
                
                full_content = "\n\n".join(content_parts)
                
                # Create document for storage
                doc = {
                    'url': form['search_url'],
                    'chunk_number': 0,
                    'content': full_content,
                    'metadata': {
                        'topic': form['topic'],
                        'form_code': form['form_code'],
                        'form_title': form['form_title'],
                        'form_info_url': form.get('form_info_url', ''),
                        'download_url': form.get('download_url', ''),
                        'pdf_storage_url': pdf_storage_url,
                        'effective_date': form['effective_date'],
                        'languages': form['languages'],
                        'mandatory': form['mandatory'],
                        'related_forms': form.get('related_forms', []),
                        'download_links': form.get('download_links', []),
                        'source': 'california_courts_comprehensive',
                        'word_count': len(full_content.split()),
                        'char_count': len(full_content)
                    }
                }
                
                # Add source_id if using crawled_pages table
                if hasattr(self, 'table_name') and self.table_name == 'crawled_pages':
                    doc['source_id'] = 'california_courts_comprehensive'
                
                documents_to_store.append(doc)
                
            except Exception as e:
                print(f"❌ Error processing form {form.get('form_code', 'unknown')}: {e}")
                self.stats["errors"].append(f"Form {form.get('form_code', 'unknown')}: {str(e)}")
                continue
        
        # Store documents with embeddings
        return self.store_documents_with_embeddings(documents_to_store, topic)
    
    def store_documents_with_embeddings(self, documents: List[Dict[str, Any]], topic: str) -> bool:
        """Store documents in Supabase with open source embeddings."""
        if not documents:
            return True
        
        print(f"🗄️  Storing {len(documents)} documents for topic: {topic}")
        
        # If no table is available, just save to JSON file
        if not hasattr(self, 'table_name') or self.table_name is None:
            print("💾 No database table available, saving to JSON file...")
            filename = f"legal_forms_{topic.replace(' ', '_')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(documents, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved {len(documents)} documents to {filename}")
            self.stats["chunks_stored"] += len(documents)
            return True
        
        try:
            # Create embeddings for all content
            contents = [doc['content'] for doc in documents]
            embeddings = self.create_embeddings(contents)
            
            # Add embeddings to documents
            for doc, embedding in zip(documents, embeddings):
                doc['embedding'] = embedding
            
            # Store in batches
            batch_size = 10  # Smaller batches for reliability
            stored_count = 0
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                
                try:
                    result = self.supabase_client.table(self.table_name).insert(batch).execute()
                    stored_count += len(batch)
                    print(f"✅ Stored batch {i//batch_size + 1}: {len(batch)} documents")
                    
                    # Small delay between batches
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"❌ Error storing batch {i//batch_size + 1}: {e}")
                    self.stats["errors"].append(f"Batch storage error for {topic}: {str(e)}")
                    continue
            
            self.stats["chunks_stored"] += stored_count
            
            # Verify storage
            if self.verify_storage(stored_count, topic):
                print(f"✅ Successfully stored and verified {stored_count} documents for topic: {topic}")
                return True
            else:
                print(f"⚠️  Storage verification failed for topic: {topic}")
                return False
                
        except Exception as e:
            print(f"❌ Error storing documents for topic {topic}: {e}")
            self.stats["errors"].append(f"Storage error for {topic}: {str(e)}")
            return False
    
    def verify_storage(self, expected_count: int, topic: str) -> bool:
        """Verify that data was stored correctly before proceeding."""
        if not hasattr(self, 'table_name') or self.table_name is None:
            return True  # Can't verify if no table
            
        try:
            # Check the table
            result = self.supabase_client.table(self.table_name).select('id').eq('metadata->>topic', topic).execute()
            stored_count = len(result.data)
            
            print(f"📊 Verification for '{topic}': Expected {expected_count}, Found {stored_count}")
            
            if stored_count >= expected_count:
                print(f"✅ Storage verification passed for '{topic}'")
                return True
            else:
                print(f"⚠️  Storage verification failed for '{topic}'")
                return False
                
        except Exception as e:
            print(f"❌ Error verifying storage: {e}")
            return False
    
    def crawl_all_topics(self):
        """Crawl all 26 popular topics with comprehensive data collection."""
        print("🚀 Starting Comprehensive Legal Forms Crawler")
        print("=" * 70)
        print(f"📋 Topics to process: {len(self.popular_topics)}")
        print(f"🤖 Using open source embeddings: all-MiniLM-L6-v2")
        print(f"🗄️  Storing in Supabase with vector search")
        print(f"📄 Extracting form details and storing PDFs")
        print(f"🔗 Keeping all links for user reference")
        print("=" * 70)
        
        start_time = time.time()
        successful_topics = 0
        
        for i, topic in enumerate(self.popular_topics, 1):
            print(f"\n📍 Progress: {i}/{len(self.popular_topics)} - Processing '{topic}'")
            
            try:
                # Crawl forms for this topic
                forms_data = self.crawl_topic_forms(topic)
                
                if forms_data:
                    # Process and store with verification
                    if self.process_and_store_forms(forms_data, topic):
                        successful_topics += 1
                        self.stats["topics_processed"] += 1
                        print(f"✅ Successfully completed topic: {topic}")
                    else:
                        print(f"⚠️  Failed to store data for topic: {topic}")
                else:
                    print(f"⚠️  No forms found for topic: {topic}")
                
                # Progress update
                self.print_progress_stats()
                
                # Delay between topics to be respectful
                time.sleep(3)
                
            except Exception as e:
                print(f"❌ Failed to process topic '{topic}': {e}")
                self.stats["errors"].append(f"Topic '{topic}': {str(e)}")
                continue
        
        # Final summary
        end_time = time.time()
        duration = end_time - start_time
        
        self.print_final_summary(successful_topics, duration)
        
        return self.stats
    
    def print_progress_stats(self):
        """Print current progress statistics."""
        print(f"📊 Current Progress:")
        print(f"   Topics processed: {self.stats['topics_processed']}")
        print(f"   Forms found: {self.stats['forms_found']}")
        print(f"   Form details extracted: {self.stats['form_details_extracted']}")
        print(f"   PDFs stored: {self.stats['pdfs_stored']}")
        print(f"   Document chunks stored: {self.stats['chunks_stored']}")
        print(f"   Errors: {len(self.stats['errors'])}")
    
    def print_final_summary(self, successful_topics: int, duration: float):
        """Print final crawling summary."""
        print("\n" + "=" * 70)
        print("🎉 COMPREHENSIVE CRAWLING COMPLETE!")
        print("=" * 70)
        print(f"⏱️  Total Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        print(f"✅ Successful Topics: {successful_topics}/{len(self.popular_topics)}")
        print(f"📄 Total Forms Found: {self.stats['forms_found']}")
        print(f"📋 Form Details Extracted: {self.stats['form_details_extracted']}")
        print(f"📁 PDFs Stored: {self.stats['pdfs_stored']}")
        print(f"🗄️  Document Chunks Stored: {self.stats['chunks_stored']}")
        print(f"🤖 Using Open Source Embeddings: all-MiniLM-L6-v2")
        print(f"❌ Total Errors: {len(self.stats['errors'])}")
        
        if self.stats['errors']:
            print(f"\n⚠️  Error Summary (first 10):")
            for error in self.stats['errors'][:10]:
                print(f"   - {error}")
            if len(self.stats['errors']) > 10:
                print(f"   ... and {len(self.stats['errors']) - 10} more errors")
        
        print(f"\n🏛️  Enhanced California Legal Forms Database Ready!")
        print(f"🔍 Users can now get hardcoded responses + real Supabase data")
        print(f"🔗 All form links and PDFs are preserved for user access")
        print("=" * 70)

def main():
    """Main function to run the comprehensive crawler."""
    try:
        crawler = ComprehensiveLegalCrawler()
        results = crawler.crawl_all_topics()
        
        # Save results to JSON for backup
        with open('comprehensive_crawl_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: comprehensive_crawl_results.json")
        
        return results
        
    except KeyboardInterrupt:
        print("\n⏹️  Crawling interrupted by user")
        return None
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        return None

if __name__ == "__main__":
    main() 