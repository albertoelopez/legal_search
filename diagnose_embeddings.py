#!/usr/bin/env python3
"""
Diagnose Embedding Issues

This script investigates:
1. How embeddings are stored in the database
2. Whether the match function is working
3. Content quality and structure
"""

import os
import json
from supabase import create_client
from sentence_transformers import SentenceTransformer

def diagnose_embeddings():
    print("🔍 DIAGNOSING EMBEDDING ISSUES")
    print("=" * 50)
    
    # Connect to Supabase
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    supabase = create_client(supabase_url, supabase_key)
    
    print("✅ Connected to Supabase")
    
    # 1. Check raw data structure
    print("\n📊 CHECKING RAW DATA STRUCTURE")
    print("-" * 40)
    
    try:
        # Get a few sample records
        result = supabase.table('crawled_pages').select('*').limit(3).execute()
        
        if result.data:
            for i, record in enumerate(result.data, 1):
                print(f"\n📄 Record {i}:")
                print(f"   ID: {record.get('id')}")
                print(f"   URL: {record.get('url', 'N/A')[:80]}...")
                print(f"   Content: {record.get('content', 'N/A')[:100]}...")
                
                metadata = record.get('metadata', {})
                print(f"   Form Code: {metadata.get('form_code', 'N/A')}")
                print(f"   Topic: {metadata.get('topic', 'N/A')}")
                print(f"   Title: {metadata.get('title', 'N/A')[:50]}...")
                
                embedding = record.get('embedding')
                if embedding:
                    print(f"   Embedding: {len(embedding)} dimensions")
                    print(f"   Sample values: {embedding[:5]}...")
                    print(f"   Embedding type: {type(embedding)}")
                else:
                    print(f"   Embedding: None")
        else:
            print("❌ No data found")
            
    except Exception as e:
        print(f"❌ Error checking raw data: {e}")
    
    # 2. Test the match function directly
    print("\n🔧 TESTING MATCH FUNCTION")
    print("-" * 40)
    
    try:
        # Create a simple test embedding
        model = SentenceTransformer('all-MiniLM-L6-v2')
        test_embedding = model.encode(["divorce papers"], convert_to_tensor=False)[0].tolist()
        
        print(f"✅ Created test embedding: {len(test_embedding)} dimensions")
        print(f"   Sample values: {test_embedding[:5]}")
        
        # Test the match function
        result = supabase.rpc(
            'match_crawled_pages',
            {
                'query_embedding': test_embedding,
                'match_count': 3,
                'filter': {},
                'source_filter': 'california_courts_comprehensive'
            }
        ).execute()
        
        if result.data:
            print(f"✅ Match function returned {len(result.data)} results")
            for i, match in enumerate(result.data, 1):
                similarity = match.get('similarity', 0)
                metadata = match.get('metadata', {})
                form_code = metadata.get('form_code', 'Unknown')
                topic = metadata.get('topic', 'Unknown')
                print(f"   {i}. {form_code} - {topic} (similarity: {similarity:.3f})")
        else:
            print("❌ Match function returned no results")
            
    except Exception as e:
        print(f"❌ Error testing match function: {e}")
    
    # 3. Check for specific form codes
    print("\n🔍 SEARCHING FOR SPECIFIC FORMS")
    print("-" * 40)
    
    form_codes_to_check = ['FL-180', 'DV-100', 'FL-150', 'ADOPT-050']
    
    for form_code in form_codes_to_check:
        try:
            result = supabase.table('crawled_pages').select('*').contains('metadata', {'form_code': form_code}).execute()
            
            if result.data:
                print(f"✅ Found {len(result.data)} records for {form_code}")
                for record in result.data[:2]:  # Show first 2
                    metadata = record.get('metadata', {})
                    topic = metadata.get('topic', 'Unknown')
                    content = record.get('content', '')[:100]
                    print(f"   Topic: {topic}")
                    print(f"   Content: {content}...")
            else:
                print(f"❌ No records found for {form_code}")
                
        except Exception as e:
            print(f"❌ Error searching for {form_code}: {e}")
    
    # 4. Test similarity threshold
    print("\n📊 TESTING SIMILARITY THRESHOLDS")
    print("-" * 40)
    
    try:
        test_queries = ["divorce", "FL-180", "adoption"]
        
        for query in test_queries:
            print(f"\n🔍 Testing query: '{query}'")
            
            # Create embedding
            query_embedding = model.encode([query], convert_to_tensor=False)[0].tolist()
            
            # Test with different thresholds
            for threshold in [0.0, 0.1, 0.2, 0.3]:
                result = supabase.rpc(
                    'match_crawled_pages',
                    {
                        'query_embedding': query_embedding,
                        'match_count': 5,
                        'filter': {},
                        'source_filter': 'california_courts_comprehensive'
                    }
                ).execute()
                
                if result.data:
                    filtered_results = [r for r in result.data if r.get('similarity', 0) >= threshold]
                    print(f"   Threshold {threshold}: {len(filtered_results)} results")
                else:
                    print(f"   Threshold {threshold}: 0 results")
                    
    except Exception as e:
        print(f"❌ Error testing thresholds: {e}")
    
    # 5. Check database function
    print("\n🔧 CHECKING DATABASE FUNCTION")
    print("-" * 40)
    
    try:
        # Check if the function exists
        result = supabase.rpc('match_crawled_pages', {
            'query_embedding': [0.0] * 384,
            'match_count': 1
        }).execute()
        
        print("✅ match_crawled_pages function exists and is callable")
        
    except Exception as e:
        print(f"❌ Function error: {e}")
        
        # Check if we need to recreate the function
        print("\n🔧 Checking if function needs to be recreated...")
        
        # Try a simple table query instead
        try:
            result = supabase.table('crawled_pages').select('id, metadata').limit(1).execute()
            if result.data:
                print("✅ Table access works, function might need recreation")
            else:
                print("❌ No data in table")
        except Exception as e2:
            print(f"❌ Table access also failed: {e2}")

if __name__ == "__main__":
    diagnose_embeddings() 