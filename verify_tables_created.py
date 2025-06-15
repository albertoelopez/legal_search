#!/usr/bin/env python3
"""
Verify Tables Created Successfully

Run this after executing the SQL script in Supabase dashboard
to confirm everything is set up correctly.
"""

import os
from supabase import create_client

def verify_setup():
    """Verify that Supabase tables are created and ready."""
    print("🔍 VERIFYING SUPABASE SETUP")
    print("=" * 40)
    
    # Connect to Supabase
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        supabase = create_client(supabase_url, supabase_key)
        print("✅ Connected to Supabase")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    # Check tables exist and are accessible
    tables_status = {}
    
    print("\n📊 CHECKING TABLES:")
    
    # Check sources table
    try:
        result = supabase.table('sources').select('*').execute()
        tables_status['sources'] = True
        print(f"   ✅ sources: {len(result.data)} records")
        
        # Check if our default source exists
        default_source = supabase.table('sources').select('*').eq('source_id', 'california_courts_comprehensive').execute()
        if default_source.data:
            print(f"   ✅ Default source found: {default_source.data[0]['summary']}")
        else:
            print("   ⚠️  Default source not found")
            
    except Exception as e:
        tables_status['sources'] = False
        print(f"   ❌ sources: {e}")
    
    # Check crawled_pages table
    try:
        result = supabase.table('crawled_pages').select('*').limit(1).execute()
        tables_status['crawled_pages'] = True
        count_result = supabase.table('crawled_pages').select('id', count='exact').execute()
        count = count_result.count if hasattr(count_result, 'count') else len(count_result.data)
        print(f"   ✅ crawled_pages: {count} records")
        
    except Exception as e:
        tables_status['crawled_pages'] = False
        print(f"   ❌ crawled_pages: {e}")
    
    # Test insert capability
    print("\n🧪 TESTING INSERT CAPABILITY:")
    
    if tables_status.get('crawled_pages', False):
        try:
            # Test insert
            test_data = {
                'url': 'https://test.example.com/test',
                'chunk_number': 0,
                'content': 'Test content for verification',
                'metadata': {'test': True, 'topic': 'verification'},
                'source_id': 'california_courts_comprehensive',
                'embedding': [0.0] * 384  # Zero vector for testing
            }
            
            result = supabase.table('crawled_pages').insert(test_data).execute()
            
            if result.data:
                print("   ✅ Insert test successful")
                
                # Clean up test record
                test_id = result.data[0]['id']
                supabase.table('crawled_pages').delete().eq('id', test_id).execute()
                print("   ✅ Test record cleaned up")
                
            else:
                print("   ❌ Insert test failed - no data returned")
                
        except Exception as e:
            print(f"   ❌ Insert test failed: {e}")
    
    # Overall status
    all_tables_ready = all(tables_status.values())
    
    print(f"\n🎯 OVERALL STATUS:")
    if all_tables_ready:
        print("🎉 SUCCESS! Supabase is fully set up and ready!")
        print("\n📋 NEXT STEPS:")
        print("1. Run: python run_full_crawler.py")
        print("   This will crawl all 26 legal topics and store in Supabase")
        print("2. Wait for crawling to complete (10-15 minutes)")
        print("3. Verify data with: python quick_supabase_check.py")
        print("4. Then enhance the frontend to use the stored data")
        return True
    else:
        print("❌ Setup incomplete. Please check the errors above.")
        print("\n🔧 TROUBLESHOOTING:")
        print("1. Make sure you ran the SQL script in Supabase dashboard")
        print("2. Check that the vector extension is enabled")
        print("3. Verify your Supabase permissions")
        return False

if __name__ == "__main__":
    success = verify_setup()
    exit(0 if success else 1) 