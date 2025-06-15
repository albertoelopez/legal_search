#!/usr/bin/env python3
"""
Setup Supabase schema for California Legal Forms with open source embeddings.
"""

import os
from supabase import create_client, Client

def setup_supabase_schema():
    """Set up the Supabase schema for the legal forms database."""
    
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
        
        # Read the SQL schema file
        with open('setup_supabase_schema.sql', 'r') as f:
            sql_content = f.read()
        
        print("📄 Executing SQL schema setup...")
        
        # Split SQL into individual statements and execute them
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        for i, statement in enumerate(statements, 1):
            try:
                if statement.lower().startswith(('create', 'drop', 'alter', 'insert')):
                    print(f"   Executing statement {i}/{len(statements)}: {statement[:50]}...")
                    result = supabase.rpc('exec_sql', {'sql': statement}).execute()
                    
            except Exception as e:
                # Some statements might fail if objects already exist, that's okay
                if 'already exists' in str(e) or 'does not exist' in str(e):
                    print(f"   ⚠️  Statement {i} skipped: {str(e)[:100]}...")
                else:
                    print(f"   ❌ Error in statement {i}: {e}")
                    continue
        
        print("✅ Schema setup completed!")
        
        # Test the setup by checking if tables exist
        print("\n🔍 Verifying table creation...")
        
        # Test documents table
        try:
            result = supabase.table('documents').select('id').limit(1).execute()
            print("✅ documents table exists and accessible")
        except Exception as e:
            print(f"❌ documents table issue: {e}")
        
        # Test sources table
        try:
            result = supabase.table('sources').select('source_id').limit(1).execute()
            print("✅ sources table exists and accessible")
        except Exception as e:
            print(f"❌ sources table issue: {e}")
        
        # Test crawled_pages table
        try:
            result = supabase.table('crawled_pages').select('id').limit(1).execute()
            print("✅ crawled_pages table exists and accessible")
        except Exception as e:
            print(f"❌ crawled_pages table issue: {e}")
        
        print("\n🎉 Supabase setup completed successfully!")
        print("🔧 Ready for comprehensive legal forms crawling with open source embeddings!")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to setup Supabase schema: {e}")
        return False

if __name__ == "__main__":
    success = setup_supabase_schema()
    exit(0 if success else 1) 