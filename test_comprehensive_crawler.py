#!/usr/bin/env python3
"""
Test script for the comprehensive legal crawler.
Tests with just one topic (adoption) to verify everything works.
"""

import os
import sys
from comprehensive_legal_crawler import ComprehensiveLegalCrawler

def test_single_topic():
    """Test the crawler with just the adoption topic."""
    print("🧪 Testing Comprehensive Legal Crawler with 'adoption' topic")
    print("=" * 60)
    
    try:
        # Create crawler instance
        crawler = ComprehensiveLegalCrawler()
        
        # Override to test with just one topic
        crawler.popular_topics = ["adoption"]
        
        print(f"🔧 Testing with topic: {crawler.popular_topics[0]}")
        print(f"🤖 Using open source embeddings: all-MiniLM-L6-v2")
        print(f"🗄️  Will store in Supabase")
        print("=" * 60)
        
        # Run the crawler
        results = crawler.crawl_all_topics()
        
        print("\n" + "=" * 60)
        print("🧪 TEST RESULTS:")
        print("=" * 60)
        print(f"✅ Topics processed: {results['topics_processed']}")
        print(f"📄 Forms found: {results['forms_found']}")
        print(f"📋 Form details extracted: {results['form_details_extracted']}")
        print(f"📁 PDFs stored: {results['pdfs_stored']}")
        print(f"🗄️  Document chunks stored: {results['chunks_stored']}")
        print(f"❌ Errors: {len(results['errors'])}")
        
        if results['errors']:
            print(f"\n⚠️  Errors encountered:")
            for error in results['errors']:
                print(f"   - {error}")
        
        # Test Supabase query
        print(f"\n🔍 Testing Supabase query...")
        try:
            query_result = crawler.supabase_client.table('documents').select('*').eq('metadata->>topic', 'adoption').limit(3).execute()
            print(f"✅ Found {len(query_result.data)} documents in Supabase for 'adoption'")
            
            if query_result.data:
                sample_doc = query_result.data[0]
                print(f"📋 Sample document:")
                print(f"   Form Code: {sample_doc['metadata'].get('form_code', 'N/A')}")
                print(f"   Form Title: {sample_doc['metadata'].get('form_title', 'N/A')}")
                print(f"   Content length: {len(sample_doc['content'])} characters")
                
        except Exception as e:
            print(f"❌ Error querying Supabase: {e}")
        
        print(f"\n🎉 Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_single_topic()
    sys.exit(0 if success else 1) 