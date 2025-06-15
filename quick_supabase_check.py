#!/usr/bin/env python3
"""
Quick Supabase Status Check

Simple script to quickly check:
1. Connection status
2. What tables exist
3. How much data we have
4. Whether we're ready to proceed
"""

import os
import json
from supabase import create_client

def quick_check():
    """Quick check of Supabase status."""
    print("🔍 QUICK SUPABASE STATUS CHECK")
    print("=" * 40)
    
    # Check environment variables
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing environment variables:")
        print("   SUPABASE_URL:", "✅ Set" if supabase_url else "❌ Missing")
        print("   SUPABASE_SERVICE_KEY:", "✅ Set" if supabase_key else "❌ Missing")
        return False
    
    print("✅ Environment variables are set")
    
    # Try to connect
    try:
        supabase = create_client(supabase_url, supabase_key)
        print("✅ Connected to Supabase")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    # Check tables
    tables_to_check = ['sources', 'documents', 'crawled_pages']
    table_status = {}
    
    print("\n📊 TABLE STATUS:")
    for table in tables_to_check:
        try:
            result = supabase.table(table).select('*').limit(1).execute()
            count_result = supabase.table(table).select('id', count='exact').execute()
            count = count_result.count if hasattr(count_result, 'count') else len(count_result.data)
            
            table_status[table] = {
                'exists': True,
                'count': count,
                'accessible': True
            }
            print(f"   ✅ {table}: {count} records")
            
        except Exception as e:
            table_status[table] = {
                'exists': False,
                'count': 0,
                'accessible': False,
                'error': str(e)
            }
            print(f"   ❌ {table}: Not accessible ({str(e)[:50]}...)")
    
    # Check local data files
    print("\n📁 LOCAL DATA FILES:")
    local_files = [f for f in os.listdir('.') if f.startswith('legal_forms_') and f.endswith('.json')]
    
    if local_files:
        total_forms = 0
        for file in local_files:
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    count = len(data)
                    total_forms += count
                    topic = file.replace('legal_forms_', '').replace('.json', '')
                    print(f"   ✅ {topic}: {count} forms")
            except Exception as e:
                print(f"   ❌ {file}: Error reading ({e})")
        
        print(f"\n📈 TOTAL: {total_forms} forms in {len(local_files)} topics")
    else:
        print("   ❌ No local data files found")
    
    # Determine readiness
    has_working_table = any(status['accessible'] for status in table_status.values())
    has_local_data = len(local_files) > 0
    
    print(f"\n🎯 READINESS STATUS:")
    print(f"   Database ready: {'✅' if has_working_table else '❌'}")
    print(f"   Local data available: {'✅' if has_local_data else '❌'}")
    
    if has_working_table and has_local_data:
        print("\n🚀 READY TO PROCEED!")
        print("   You can run the full crawler to store all data in Supabase")
        recommended_table = next((table for table, status in table_status.items() 
                                if status['accessible']), None)
        if recommended_table:
            print(f"   Recommended table: {recommended_table}")
    elif has_local_data:
        print("\n⚠️  PARTIAL READINESS")
        print("   You have local data but need to set up Supabase tables")
        print("   Run: python verify_supabase_storage.py for detailed setup")
    else:
        print("\n❌ NOT READY")
        print("   Need to run crawler first to collect data")
        print("   Run: python test_comprehensive_crawler.py")
    
    return has_working_table and has_local_data

if __name__ == "__main__":
    success = quick_check()
    exit(0 if success else 1) 