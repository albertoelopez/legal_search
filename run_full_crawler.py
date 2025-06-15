#!/usr/bin/env python3
"""
Run the comprehensive legal crawler for all 26 popular topics.
This will collect all forms data and save it to JSON files.
"""

import os
import sys
import time
from comprehensive_legal_crawler import ComprehensiveLegalCrawler

def main():
    """Run the comprehensive crawler for all topics."""
    print("🚀 Starting Full Comprehensive Legal Forms Crawler")
    print("=" * 70)
    print("📋 Will crawl all 26 popular topics from California Courts")
    print("🤖 Using open source embeddings (all-MiniLM-L6-v2)")
    print("💾 Storing data in Supabase database with JSON backup")
    print("🔗 Preserving all form links and download URLs")
    print("=" * 70)
    
    # Ask user for confirmation
    response = input("\n🤔 This will take approximately 10-15 minutes. Continue? (y/N): ")
    if response.lower() not in ['y', 'yes']:
        print("❌ Cancelled by user")
        return False
    
    try:
        # Create crawler instance
        crawler = ComprehensiveLegalCrawler()
        
        print(f"\n🎯 Starting crawl of {len(crawler.popular_topics)} topics...")
        start_time = time.time()
        
        # Run the full crawler
        results = crawler.crawl_all_topics()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Save comprehensive results
        import json
        with open('all_legal_forms_data.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Comprehensive results saved to: all_legal_forms_data.json")
        
        # Create a summary report
        print(f"\n📊 FINAL SUMMARY REPORT")
        print("=" * 50)
        print(f"⏱️  Total Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        print(f"✅ Topics Processed: {results['topics_processed']}")
        print(f"📄 Total Forms Found: {results['forms_found']}")
        print(f"📋 Form Details Extracted: {results['form_details_extracted']}")
        print(f"📁 PDFs Stored: {results['pdfs_stored']}")
        print(f"🗄️  Document Chunks Stored: {results['chunks_stored']}")
        print(f"❌ Total Errors: {len(results['errors'])}")
        
        # List all JSON files created
        print(f"\n📁 JSON Files Created:")
        import glob
        json_files = glob.glob("legal_forms_*.json")
        for json_file in sorted(json_files):
            file_size = os.path.getsize(json_file)
            print(f"   📄 {json_file} ({file_size:,} bytes)")
        
        if results['errors']:
            print(f"\n⚠️  Errors Encountered:")
            for error in results['errors'][:10]:  # Show first 10
                print(f"   - {error}")
            if len(results['errors']) > 10:
                print(f"   ... and {len(results['errors']) - 10} more errors")
        
        print(f"\n🎉 Comprehensive crawling completed successfully!")
        print(f"🔧 Next step: Enhance frontend to use this data")
        
        return True
        
    except KeyboardInterrupt:
        print("\n⏹️  Crawling interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 