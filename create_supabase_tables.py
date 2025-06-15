#!/usr/bin/env python3
"""
Create necessary tables in Supabase for the legal forms database.
"""

import os
from supabase import create_client, Client

def create_tables():
    """Create the necessary tables in Supabase."""
    
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
        
        # Create documents table using raw SQL
        create_documents_sql = """
        CREATE TABLE IF NOT EXISTS documents (
            id BIGSERIAL PRIMARY KEY,
            url VARCHAR NOT NULL,
            chunk_number INTEGER NOT NULL,
            content TEXT NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            embedding VECTOR(384),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
            UNIQUE(url, chunk_number)
        );
        """
        
        print("📄 Creating documents table...")
        try:
            # Use the REST API to execute SQL
            import requests
            
            headers = {
                'apikey': supabase_key,
                'Authorization': f'Bearer {supabase_key}',
                'Content-Type': 'application/json'
            }
            
            # Enable pgvector extension first
            enable_vector_sql = "CREATE EXTENSION IF NOT EXISTS vector;"
            response = requests.post(
                f"{supabase_url}/rest/v1/rpc/exec_sql",
                headers=headers,
                json={'sql': enable_vector_sql}
            )
            print(f"   Vector extension: {response.status_code}")
            
            # Create documents table
            response = requests.post(
                f"{supabase_url}/rest/v1/rpc/exec_sql",
                headers=headers,
                json={'sql': create_documents_sql}
            )
            print(f"   Documents table: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Documents table created successfully!")
            else:
                print(f"⚠️  Documents table response: {response.text}")
                
        except Exception as e:
            print(f"❌ Error creating documents table: {e}")
            # Try alternative approach - just test if we can insert
            print("🔄 Testing direct table access...")
            
        # Test if we can access the table
        try:
            result = supabase.table('documents').select('id').limit(1).execute()
            print("✅ Documents table is accessible!")
            return True
        except Exception as e:
            print(f"❌ Cannot access documents table: {e}")
            
            # Try creating a simple test table to verify permissions
            print("🧪 Testing with a simple table...")
            try:
                # Create a simple test table
                test_result = supabase.table('test_table').insert({
                    'test_field': 'test_value'
                }).execute()
                print("✅ Basic table operations work!")
                
                # Clean up test
                supabase.table('test_table').delete().eq('test_field', 'test_value').execute()
                
            except Exception as test_e:
                print(f"❌ Basic table operations failed: {test_e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to setup Supabase: {e}")
        return False

if __name__ == "__main__":
    success = create_tables()
    exit(0 if success else 1) 