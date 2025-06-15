#!/usr/bin/env python3
"""
Simple Robust Legal Forms Crawler

Fixes the main issues from the complex crawler:
1. No Playwright (avoids async issues)
2. No PDF storage (avoids header errors)  
3. Better duplicate handling
4. Focus on core data collection
"""

import os
import json
import time
import requests
import re
from typing import List, Dict, Any
from urllib.parse import urljoin, quote_plus
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from supabase import create_client

class SimpleRobustCrawler:
    def __init__(self):
        self.base_domain = "https://selfhelp.courts.ca.gov"
        self.popular_topics = [
            "adoption", "appeals", "child custody and visitation", "child support",
            "civil", "civil harassment", "cleaning criminal record", "conservatorship",
            "discovery and subpoenas", "divorce", "domestic violence", "elder abuse",
            "enforcement of judgment", "eviction", "fee waivers", "gender change",
            "guardianship", "juvenile", "language access", "name change",
            "parentage", "probate", "proof of service", "remote appearance",
            "small claims", "traffic"
        ]
        
        print("🤖 Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Model loaded!")
        
        self.init_supabase()
        self.stats = {"topics_processed": 0, "forms_found": 0, "documents_stored": 0, "errors": []}
    
    def init_supabase(self):
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase_client = create_client(supabase_url, supabase_key)
        print("✅ Supabase connected!")
    
    def crawl_topic_forms(self, topic: str) -> List[Dict[str, Any]]:
        print(f"\n🔍 Crawling: {topic}")
        query = quote_plus(topic)
        search_url = f"{self.base_domain}/find-forms?query={query}"
        
        try:
            response = requests.get(search_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            forms = []
            form_links = soup.find_all('a', href=True)
            
            for link in form_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                form_code_match = re.search(r'\b([A-Z]{2,4}-\d{3}[A-Z]?(?:-[A-Z]+)?)\b', text)
                
                if form_code_match and ('/jcc-form/' in href or 'form' in href.lower()):
                    form_code = form_code_match.group(1)
                    form_url = urljoin(self.base_domain, href)
                    
                    parent = link.parent
                    context = parent.get_text(strip=True) if parent else text
                    
                    form_data = {
                        "form_code": form_code,
                        "title": text,
                        "url": form_url,
                        "topic": topic,
                        "context": context,
                        "search_url": search_url
                    }
                    forms.append(form_data)
            
            # Remove duplicates
            unique_forms = {}
            for form in forms:
                code = form["form_code"]
                if code not in unique_forms:
                    unique_forms[code] = form
            
            forms_list = list(unique_forms.values())
            print(f"✅ Found {len(forms_list)} forms for: {topic}")
            return forms_list
            
        except Exception as e:
            error_msg = f"Error crawling {topic}: {e}"
            print(f"❌ {error_msg}")
            self.stats["errors"].append(error_msg)
            return []
    
    def store_forms_in_supabase(self, forms: List[Dict[str, Any]], topic: str) -> bool:
        if not forms:
            return True
        
        print(f"🗄️  Storing {len(forms)} forms for: {topic}")
        
        try:
            documents = []
            texts_for_embedding = []
            
            for i, form in enumerate(forms):
                content = f"Form: {form['form_code']} | Title: {form['title']} | Topic: {form['topic']} | Context: {form['context']}"
                texts_for_embedding.append(content)
                
                doc = {
                    "url": f"{form['search_url']}#{form['form_code']}",  # Unique URL per form
                    "chunk_number": 0,
                    "content": content,
                    "metadata": {
                        "form_code": form["form_code"],
                        "title": form["title"],
                        "topic": topic,
                        "form_url": form["url"],
                        "context": form["context"]
                    },
                    "source_id": "california_courts_comprehensive"
                }
                documents.append(doc)
            
            # Create embeddings
            print(f"🔢 Creating embeddings for {len(texts_for_embedding)} texts...")
            embeddings = self.embedding_model.encode(texts_for_embedding, convert_to_tensor=False)
            
            # Add embeddings to documents
            for doc, embedding in zip(documents, embeddings.tolist()):
                doc["embedding"] = embedding
            
            # Store in batches
            batch_size = 5
            stored_count = 0
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                
                try:
                    result = self.supabase_client.table('crawled_pages').insert(batch).execute()
                    if result.data:
                        stored_count += len(result.data)
                        print(f"   ✅ Stored batch {i//batch_size + 1}: {len(result.data)} documents")
                    
                except Exception as batch_error:
                    print(f"   ⚠️  Batch failed, trying individual inserts...")
                    for doc in batch:
                        try:
                            result = self.supabase_client.table('crawled_pages').insert(doc).execute()
                            if result.data:
                                stored_count += 1
                        except Exception as doc_error:
                            if "duplicate key" not in str(doc_error):
                                print(f"   ❌ Error: {doc_error}")
            
            print(f"✅ Stored {stored_count} documents for: {topic}")
            self.stats["documents_stored"] += stored_count
            return True
            
        except Exception as e:
            error_msg = f"Error storing {topic}: {e}"
            print(f"❌ {error_msg}")
            self.stats["errors"].append(error_msg)
            return False
    
    def save_to_json(self, forms: List[Dict[str, Any]], topic: str):
        filename = f"legal_forms_{topic.replace(' ', '_').replace(' and ', '_')}.json"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(forms, f, indent=2, ensure_ascii=False)
            print(f"💾 Saved: {filename}")
        except Exception as e:
            print(f"❌ JSON save error: {e}")
    
    def crawl_all_topics(self):
        print("🚀 Starting Simple Robust Crawler")
        print("=" * 50)
        
        start_time = time.time()
        successful_topics = 0
        
        for i, topic in enumerate(self.popular_topics, 1):
            print(f"\n📍 Progress: {i}/{len(self.popular_topics)} - {topic}")
            
            try:
                forms = self.crawl_topic_forms(topic)
                
                if forms:
                    self.stats["forms_found"] += len(forms)
                    self.save_to_json(forms, topic)
                    
                    if self.store_forms_in_supabase(forms, topic):
                        successful_topics += 1
                        print(f"✅ Completed: {topic}")
                    else:
                        print(f"⚠️  Partial success: {topic}")
                else:
                    print(f"⚠️  No forms found: {topic}")
                
                self.stats["topics_processed"] += 1
                
                print(f"📊 Progress: {self.stats['topics_processed']} topics, {self.stats['forms_found']} forms, {self.stats['documents_stored']} stored")
                time.sleep(1)
                
            except KeyboardInterrupt:
                print(f"\n⏹️  Interrupted at: {topic}")
                break
            except Exception as e:
                print(f"❌ Fatal error in {topic}: {e}")
                self.stats["errors"].append(f"Fatal error in {topic}: {e}")
        
        duration = time.time() - start_time
        
        print(f"\n🎉 COMPLETED!")
        print(f"⏱️  Duration: {duration:.1f}s ({duration/60:.1f}m)")
        print(f"✅ Topics: {self.stats['topics_processed']}")
        print(f"📄 Forms: {self.stats['forms_found']}")
        print(f"🗄️  Stored: {self.stats['documents_stored']}")
        print(f"❌ Errors: {len(self.stats['errors'])}")
        
        return {"success": True, "duration": duration, "stats": self.stats}

def main():
    try:
        crawler = SimpleRobustCrawler()
        results = crawler.crawl_all_topics()
        
        with open('simple_crawler_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to: simple_crawler_results.json")
        return True
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 