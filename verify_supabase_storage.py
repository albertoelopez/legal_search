#!/usr/bin/env python3
"""
Verify Supabase Storage and Setup

This script:
1. Checks if Supabase tables exist
2. Creates tables if they don't exist
3. Verifies data storage
4. Provides setup instructions if needed
"""

import os
import json
import time
from typing import Dict, List, Any
from supabase import create_client, Client

class SupabaseVerifier:
    def __init__(self):
        """Initialize the Supabase verifier."""
        self.supabase_client = None
        self.init_supabase()
        
    def init_supabase(self):
        """Initialize Supabase client."""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("❌ SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment variables")
        
        try:
            self.supabase_client = create_client(supabase_url, supabase_key)
            print("✅ Connected to Supabase")
            print(f"🔗 URL: {supabase_url}")
        except Exception as e:
            print(f"❌ Failed to connect to Supabase: {e}")
            raise
    
    def check_table_exists(self, table_name: str) -> bool:
        """Check if a specific table exists and is accessible."""
        try:
            result = self.supabase_client.table(table_name).select('*').limit(1).execute()
            return True
        except Exception as e:
            return False
    
    def get_table_count(self, table_name: str) -> int:
        """Get the number of records in a table."""
        try:
            result = self.supabase_client.table(table_name).select('id', count='exact').execute()
            return result.count if hasattr(result, 'count') else len(result.data)
        except Exception as e:
            return 0
    
    def create_tables_with_sql(self) -> bool:
        """Attempt to create tables using SQL commands."""
        print("🔧 Attempting to create tables...")
        
        # SQL commands to create tables
        sql_commands = [
            # Enable vector extension
            "CREATE EXTENSION IF NOT EXISTS vector;",
            
            # Create sources table
            """
            CREATE TABLE IF NOT EXISTS sources (
                source_id TEXT PRIMARY KEY,
                summary TEXT,
                total_word_count INTEGER DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
            );
            """,
            
            # Create documents table (for our crawler)
            """
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
            """,
            
            # Create crawled_pages table (for MCP server compatibility)
            """
            CREATE TABLE IF NOT EXISTS crawled_pages (
                id BIGSERIAL PRIMARY KEY,
                url VARCHAR NOT NULL,
                chunk_number INTEGER NOT NULL,
                content TEXT NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                source_id TEXT NOT NULL,
                embedding VECTOR(384),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
                UNIQUE(url, chunk_number),
                FOREIGN KEY (source_id) REFERENCES sources(source_id)
            );
            """,
            
            # Insert default source
            """
            INSERT INTO sources (source_id, summary, total_word_count) 
            VALUES ('california_courts_comprehensive', 'California Courts comprehensive legal forms database', 0)
            ON CONFLICT (source_id) DO NOTHING;
            """
        ]
        
        success_count = 0
        for i, sql in enumerate(sql_commands, 1):
            try:
                print(f"   Executing SQL command {i}/{len(sql_commands)}...")
                # Try using RPC if available
                result = self.supabase_client.rpc('exec_sql', {'sql': sql}).execute()
                success_count += 1
                print(f"   ✅ Command {i} executed successfully")
            except Exception as e:
                print(f"   ❌ Command {i} failed: {e}")
                # Try alternative method
                try:
                    # Some commands might work with direct table operations
                    if "INSERT INTO sources" in sql:
                        self.supabase_client.table('sources').insert({
                            'source_id': 'california_courts_comprehensive',
                            'summary': 'California Courts comprehensive legal forms database',
                            'total_word_count': 0
                        }).execute()
                        success_count += 1
                        print(f"   ✅ Command {i} executed via alternative method")
                except Exception as e2:
                    print(f"   ❌ Alternative method also failed: {e2}")
        
        return success_count > 0
    
    def verify_storage_capability(self) -> Dict[str, Any]:
        """Verify what storage capabilities we have."""
        print("\n🔍 Verifying storage capabilities...")
        
        capabilities = {
            "tables_exist": {},
            "can_insert": {},
            "record_counts": {},
            "recommended_table": None,
            "storage_ready": False
        }
        
        # Check which tables exist
        tables_to_check = ['documents', 'crawled_pages', 'sources']
        
        for table in tables_to_check:
            exists = self.check_table_exists(table)
            capabilities["tables_exist"][table] = exists
            
            if exists:
                count = self.get_table_count(table)
                capabilities["record_counts"][table] = count
                print(f"   ✅ {table}: exists ({count} records)")
                
                # Test insert capability
                try:
                    test_data = self.get_test_data_for_table(table)
                    if test_data:
                        result = self.supabase_client.table(table).insert(test_data).execute()
                        if result.data:
                            # Clean up test record
                            record_id = result.data[0]['id'] if 'id' in result.data[0] else result.data[0].get('source_id')
                            if record_id:
                                if table == 'sources':
                                    self.supabase_client.table(table).delete().eq('source_id', record_id).execute()
                                else:
                                    self.supabase_client.table(table).delete().eq('id', record_id).execute()
                        capabilities["can_insert"][table] = True
                        print(f"   ✅ {table}: can insert data")
                except Exception as e:
                    capabilities["can_insert"][table] = False
                    print(f"   ❌ {table}: cannot insert data - {e}")
            else:
                capabilities["record_counts"][table] = 0
                capabilities["can_insert"][table] = False
                print(f"   ❌ {table}: does not exist")
        
        # Determine recommended table
        if capabilities["can_insert"].get("crawled_pages", False):
            capabilities["recommended_table"] = "crawled_pages"
            capabilities["storage_ready"] = True
        elif capabilities["can_insert"].get("documents", False):
            capabilities["recommended_table"] = "documents"
            capabilities["storage_ready"] = True
        
        return capabilities
    
    def get_test_data_for_table(self, table: str) -> Dict[str, Any]:
        """Get test data for a specific table."""
        if table == "sources":
            return {
                'source_id': f'test_{int(time.time())}',
                'summary': 'Test source',
                'total_word_count': 0
            }
        elif table == "documents":
            return {
                'url': f'https://test.com/{int(time.time())}',
                'chunk_number': 0,
                'content': 'Test content',
                'metadata': {'test': True}
            }
        elif table == "crawled_pages":
            return {
                'url': f'https://test.com/{int(time.time())}',
                'chunk_number': 0,
                'content': 'Test content',
                'metadata': {'test': True},
                'source_id': 'california_courts_comprehensive'
            }
        return {}
    
    def store_sample_legal_data(self, table_name: str) -> bool:
        """Store a sample of legal forms data to verify everything works."""
        print(f"\n📄 Storing sample legal data in {table_name}...")
        
        # Load sample data from our JSON file
        if not os.path.exists('legal_forms_adoption.json'):
            print("❌ No sample data file found. Run the crawler first.")
            return False
        
        try:
            with open('legal_forms_adoption.json', 'r', encoding='utf-8') as f:
                sample_data = json.load(f)
            
            # Take first 3 forms as sample
            sample_forms = sample_data[:3]
            
            # Prepare data for storage
            documents_to_store = []
            for form in sample_forms:
                doc = form.copy()
                
                # Add source_id if using crawled_pages table
                if table_name == 'crawled_pages':
                    doc['source_id'] = 'california_courts_comprehensive'
                
                # Add a simple embedding (zeros for testing)
                doc['embedding'] = [0.0] * 384
                
                documents_to_store.append(doc)
            
            # Store the documents
            result = self.supabase_client.table(table_name).insert(documents_to_store).execute()
            
            if result.data:
                print(f"✅ Successfully stored {len(result.data)} sample documents")
                
                # Verify they were stored
                verification = self.supabase_client.table(table_name).select('id').eq('metadata->>topic', 'adoption').execute()
                print(f"✅ Verification: Found {len(verification.data)} adoption records")
                
                return True
            else:
                print("❌ No data was returned from insert operation")
                return False
                
        except Exception as e:
            print(f"❌ Error storing sample data: {e}")
            return False
    
    def run_comprehensive_verification(self) -> Dict[str, Any]:
        """Run comprehensive verification of Supabase setup."""
        print("🔍 COMPREHENSIVE SUPABASE VERIFICATION")
        print("=" * 60)
        
        # Step 1: Check current capabilities
        capabilities = self.verify_storage_capability()
        
        # Step 2: Try to create tables if none exist
        if not any(capabilities["tables_exist"].values()):
            print("\n🔧 No tables found. Attempting to create them...")
            table_creation_success = self.create_tables_with_sql()
            
            if table_creation_success:
                print("✅ Some table creation commands succeeded. Re-checking capabilities...")
                capabilities = self.verify_storage_capability()
            else:
                print("❌ Table creation failed. Manual setup required.")
        
        # Step 3: Test actual data storage if possible
        if capabilities["storage_ready"]:
            table_name = capabilities["recommended_table"]
            print(f"\n📊 Testing data storage with table: {table_name}")
            storage_success = self.store_sample_legal_data(table_name)
            capabilities["sample_storage_success"] = storage_success
        else:
            capabilities["sample_storage_success"] = False
        
        # Step 4: Provide recommendations
        self.provide_recommendations(capabilities)
        
        return capabilities
    
    def provide_recommendations(self, capabilities: Dict[str, Any]):
        """Provide recommendations based on verification results."""
        print("\n💡 RECOMMENDATIONS")
        print("=" * 40)
        
        if capabilities["storage_ready"] and capabilities.get("sample_storage_success", False):
            print("🎉 EXCELLENT! Supabase is ready for data storage.")
            print(f"✅ Recommended table: {capabilities['recommended_table']}")
            print("🚀 You can now run the full crawler with confidence!")
            print("\nNext steps:")
            print("1. Run: python run_full_crawler.py")
            print("2. This will crawl all 26 topics and store in Supabase")
            print("3. Then enhance the frontend to use the stored data")
            
        elif capabilities["storage_ready"]:
            print("⚠️  Tables exist but sample storage failed.")
            print("🔧 You may need to check permissions or table schema.")
            print(f"📋 Recommended table: {capabilities['recommended_table']}")
            
        else:
            print("❌ Supabase tables need to be created manually.")
            print("\n🔧 MANUAL SETUP REQUIRED:")
            print("1. Go to your Supabase dashboard")
            print("2. Open the SQL Editor")
            print("3. Run this SQL script:")
            print("\n" + "="*50)
            print("""
-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create sources table
CREATE TABLE sources (
    source_id TEXT PRIMARY KEY,
    summary TEXT,
    total_word_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create crawled_pages table (recommended)
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

-- Insert default source
INSERT INTO sources (source_id, summary, total_word_count) 
VALUES ('california_courts_comprehensive', 'California Courts comprehensive legal forms database', 0);

-- Create indexes for better performance
CREATE INDEX ON crawled_pages USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON crawled_pages USING gin (metadata);
            """)
            print("="*50)
            print("\n4. After running the SQL, run this script again to verify")
            print("5. Then run: python run_full_crawler.py")

def main():
    """Main verification function."""
    try:
        verifier = SupabaseVerifier()
        results = verifier.run_comprehensive_verification()
        
        # Save results for reference
        with open('supabase_verification_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Verification results saved to: supabase_verification_results.json")
        
        return results["storage_ready"] and results.get("sample_storage_success", False)
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 