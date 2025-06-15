#!/usr/bin/env python3
"""
Check what tables exist in Supabase and their structure.
"""

import os
from supabase import create_client, Client

def check_supabase():
    """Check what's available in Supabase."""
    
    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment variables")
        return False
    
    try:
        # Create Supabase client
        supabase: Client = create_client(supabase_url, supabase_key)
        print("✅ Connected to Supabase")
        print(f"🔗 URL: {supabase_url}")
        
        # List of tables to check
        tables_to_check = ['documents', 'crawled_pages', 'sources', 'code_examples']
        
        for table_name in tables_to_check:
            print(f"\n🔍 Checking table: {table_name}")
            try:
                result = supabase.table(table_name).select('*').limit(1).execute()
                print(f"✅ {table_name} exists and accessible")
                print(f"   Records found: {len(result.data)}")
                if result.data:
                    print(f"   Sample keys: {list(result.data[0].keys())}")
            except Exception as e:
                print(f"❌ {table_name} not accessible: {e}")
        
        # Try to create a simple test record in any available table
        print(f"\n🧪 Testing write access...")
        
        # Try with a simple structure that might work
        test_data = {
            'url': 'https://test.com',
            'chunk_number': 0,
            'content': 'Test content for California legal forms',
            'metadata': {'test': True, 'source': 'test_script'}
        }
        
        for table_name in ['documents', 'crawled_pages']:
            try:
                print(f"   Testing insert into {table_name}...")
                
                if table_name == 'crawled_pages':
                    # Add source_id for crawled_pages
                    test_data['source_id'] = 'test'
                
                result = supabase.table(table_name).insert(test_data).execute()
                print(f"✅ Successfully inserted test record into {table_name}")
                
                # Clean up
                if result.data:
                    record_id = result.data[0]['id']
                    supabase.table(table_name).delete().eq('id', record_id).execute()
                    print(f"✅ Cleaned up test record from {table_name}")
                
                return True
                
            except Exception as e:
                print(f"❌ Cannot insert into {table_name}: {e}")
                continue
        
        print("❌ No writable tables found")
        return False
        
    except Exception as e:
        print(f"❌ Failed to check Supabase: {e}")
        return False

if __name__ == "__main__":
    success = check_supabase()
    exit(0 if success else 1) 