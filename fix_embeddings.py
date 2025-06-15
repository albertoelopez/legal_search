#!/usr/bin/env python3
"""
Fix Embedding Storage Issues

This script:
1. Identifies records with string embeddings
2. Converts them back to proper vector format
3. Updates the database with correct embeddings
"""

import os
import json
import ast
from typing import List
from supabase import create_client
from sentence_transformers import SentenceTransformer

def fix_embeddings():
    print("🔧 FIXING EMBEDDING STORAGE ISSUES")
    print("=" * 50)
    
    # Connect to Supabase
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    supabase = create_client(supabase_url, supabase_key)
    
    print("✅ Connected to Supabase")
    
    # Load embedding model
    print("🤖 Loading embedding model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("✅ Model loaded!")
    
    # Get all records with problematic embeddings
    print("\n📊 ANALYZING EMBEDDING ISSUES")
    print("-" * 40)
    
    try:
        # Get all records
        result = supabase.table('crawled_pages').select('id, content, embedding').execute()
        
        if not result.data:
            print("❌ No data found")
            return
        
        print(f"📄 Found {len(result.data)} total records")
        
        # Analyze embedding issues
        string_embeddings = 0
        valid_embeddings = 0
        null_embeddings = 0
        
        records_to_fix = []
        
        for record in result.data:
            embedding = record.get('embedding')
            record_id = record.get('id')
            content = record.get('content', '')
            
            if embedding is None:
                null_embeddings += 1
            elif isinstance(embedding, str):
                string_embeddings += 1
                records_to_fix.append({
                    'id': record_id,
                    'content': content,
                    'embedding_str': embedding
                })
            elif isinstance(embedding, list) and len(embedding) == 384:
                valid_embeddings += 1
            else:
                print(f"⚠️  Unusual embedding format for record {record_id}: {type(embedding)}")
        
        print(f"📊 Embedding Analysis:")
        print(f"   ✅ Valid embeddings: {valid_embeddings}")
        print(f"   ❌ String embeddings: {string_embeddings}")
        print(f"   ⚪ Null embeddings: {null_embeddings}")
        
        if string_embeddings == 0:
            print("🎉 No embedding issues found!")
            return
        
        # Fix string embeddings
        print(f"\n🔧 FIXING {len(records_to_fix)} RECORDS")
        print("-" * 40)
        
        batch_size = 10
        fixed_count = 0
        
        for i in range(0, len(records_to_fix), batch_size):
            batch = records_to_fix[i:i + batch_size]
            
            print(f"\n📦 Processing batch {i//batch_size + 1}/{(len(records_to_fix) + batch_size - 1)//batch_size}")
            
            for record in batch:
                try:
                    record_id = record['id']
                    content = record['content']
                    
                    # Recreate embedding from content
                    new_embedding = model.encode([content], convert_to_tensor=False)[0].tolist()
                    
                    # Update the record
                    update_result = supabase.table('crawled_pages').update({
                        'embedding': new_embedding
                    }).eq('id', record_id).execute()
                    
                    if update_result.data:
                        fixed_count += 1
                        print(f"   ✅ Fixed record {record_id}")
                    else:
                        print(f"   ❌ Failed to update record {record_id}")
                        
                except Exception as e:
                    print(f"   ❌ Error fixing record {record_id}: {e}")
        
        print(f"\n🎉 EMBEDDING FIX COMPLETE!")
        print(f"✅ Fixed {fixed_count}/{len(records_to_fix)} records")
        
        # Verify the fix
        print(f"\n🔍 VERIFYING FIX")
        print("-" * 40)
        
        # Check a few sample records
        verify_result = supabase.table('crawled_pages').select('id, embedding').limit(5).execute()
        
        if verify_result.data:
            valid_after_fix = 0
            for record in verify_result.data:
                embedding = record.get('embedding')
                if isinstance(embedding, list) and len(embedding) == 384:
                    valid_after_fix += 1
            
            print(f"✅ Verification: {valid_after_fix}/5 sample records have valid embeddings")
            
            if valid_after_fix == 5:
                print("🎉 EMBEDDING FIX SUCCESSFUL!")
            else:
                print("⚠️  Some records still have issues")
        
        # Test search functionality
        print(f"\n🧪 TESTING SEARCH AFTER FIX")
        print("-" * 40)
        
        test_queries = ["divorce", "FL-180", "adoption"]
        
        for query in test_queries:
            try:
                query_embedding = model.encode([query], convert_to_tensor=False)[0].tolist()
                
                search_result = supabase.rpc(
                    'match_crawled_pages',
                    {
                        'query_embedding': query_embedding,
                        'match_count': 3,
                        'filter': {},
                        'source_filter': 'california_courts_comprehensive'
                    }
                ).execute()
                
                if search_result.data:
                    print(f"✅ '{query}': {len(search_result.data)} results")
                    top_result = search_result.data[0]
                    similarity = top_result.get('similarity', 0)
                    metadata = top_result.get('metadata', {})
                    form_code = metadata.get('form_code', 'Unknown')
                    print(f"   Top: {form_code} (similarity: {similarity:.3f})")
                else:
                    print(f"❌ '{query}': No results")
                    
            except Exception as e:
                print(f"❌ Error testing '{query}': {e}")
        
    except Exception as e:
        print(f"❌ Error during fix process: {e}")

if __name__ == "__main__":
    fix_embeddings() 