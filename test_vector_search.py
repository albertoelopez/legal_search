#!/usr/bin/env python3
"""
Test Vector Search Functionality

This script tests:
1. Vector similarity search with embeddings
2. Metadata filtering
3. Topic-based searches
4. Form code searches
5. Performance and accuracy
"""

import os
import json
import time
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from supabase import create_client

class VectorSearchTester:
    def __init__(self):
        """Initialize the vector search tester."""
        print("🔍 Initializing Vector Search Tester")
        print("=" * 50)
        
        # Initialize embedding model (same as crawler)
        print("🤖 Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Embedding model loaded!")
        
        # Initialize Supabase
        self.init_supabase()
        
        # Test queries for different scenarios
        self.test_queries = [
            # General legal topics
            {"query": "divorce papers", "expected_topic": "divorce", "description": "General divorce query"},
            {"query": "child custody forms", "expected_topic": "child custody and visitation", "description": "Child custody query"},
            {"query": "adoption documents", "expected_topic": "adoption", "description": "Adoption query"},
            {"query": "eviction notice", "expected_topic": "eviction", "description": "Eviction query"},
            {"query": "domestic violence restraining order", "expected_topic": "domestic violence", "description": "Domestic violence query"},
            
            # Specific form codes
            {"query": "FL-180", "expected_form": "FL-180", "description": "Specific form code search"},
            {"query": "DV-100", "expected_form": "DV-100", "description": "Domestic violence form search"},
            
            # Complex queries
            {"query": "how to change my name legally", "expected_topic": "name change", "description": "Natural language query"},
            {"query": "small claims court filing", "expected_topic": "small claims", "description": "Court procedure query"},
            {"query": "probate estate administration", "expected_topic": "probate", "description": "Estate planning query"},
            
            # Edge cases
            {"query": "traffic ticket appeal", "expected_topic": "traffic", "description": "Traffic-related query"},
            {"query": "fee waiver application", "expected_topic": "fee waivers", "description": "Fee waiver query"}
        ]
    
    def init_supabase(self):
        """Initialize Supabase client."""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("❌ SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        
        self.supabase_client = create_client(supabase_url, supabase_key)
        print("✅ Supabase connected!")
    
    def create_query_embedding(self, query: str) -> List[float]:
        """Create embedding for a search query."""
        try:
            embedding = self.embedding_model.encode([query], convert_to_tensor=False)
            return embedding[0].tolist()
        except Exception as e:
            print(f"❌ Error creating embedding for '{query}': {e}")
            return [0.0] * 384
    
    def search_similar_forms(self, query: str, limit: int = 10, similarity_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """Search for similar forms using vector similarity."""
        try:
            # Create embedding for the query
            query_embedding = self.create_query_embedding(query)
            
            # Use the match_crawled_pages function we created
            result = self.supabase_client.rpc(
                'match_crawled_pages',
                {
                    'query_embedding': query_embedding,
                    'match_count': limit,
                    'filter': {},
                    'source_filter': 'california_courts_comprehensive'
                }
            ).execute()
            
            if result.data:
                # Filter by similarity threshold
                filtered_results = [
                    item for item in result.data 
                    if item.get('similarity', 0) >= similarity_threshold
                ]
                return filtered_results
            else:
                return []
                
        except Exception as e:
            print(f"❌ Error searching for '{query}': {e}")
            return []
    
    def search_by_metadata(self, metadata_filter: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        """Search forms by metadata filtering."""
        try:
            result = self.supabase_client.table('crawled_pages').select(
                'id, content, metadata, url'
            ).contains('metadata', metadata_filter).limit(limit).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"❌ Error searching by metadata {metadata_filter}: {e}")
            return []
    
    def test_basic_vector_search(self):
        """Test basic vector search functionality."""
        print("\n🧪 TESTING BASIC VECTOR SEARCH")
        print("-" * 40)
        
        test_results = []
        
        for i, test_case in enumerate(self.test_queries, 1):
            query = test_case["query"]
            description = test_case["description"]
            
            print(f"\n{i}. Testing: {description}")
            print(f"   Query: '{query}'")
            
            start_time = time.time()
            results = self.search_similar_forms(query, limit=5, similarity_threshold=0.1)
            search_time = time.time() - start_time
            
            if results:
                print(f"   ✅ Found {len(results)} results in {search_time:.3f}s")
                
                # Show top result
                top_result = results[0]
                similarity = top_result.get('similarity', 0)
                metadata = top_result.get('metadata', {})
                form_code = metadata.get('form_code', 'Unknown')
                topic = metadata.get('topic', 'Unknown')
                title = metadata.get('title', 'Unknown')
                
                print(f"   🎯 Top result: {form_code} - {title}")
                print(f"   📊 Similarity: {similarity:.3f}")
                print(f"   🏷️  Topic: {topic}")
                
                # Check if result matches expectations
                expected_topic = test_case.get("expected_topic")
                expected_form = test_case.get("expected_form")
                
                success = False
                if expected_topic and expected_topic.lower() in topic.lower():
                    print(f"   ✅ Topic match: Expected '{expected_topic}', got '{topic}'")
                    success = True
                elif expected_form and expected_form.upper() in form_code.upper():
                    print(f"   ✅ Form match: Expected '{expected_form}', got '{form_code}'")
                    success = True
                elif similarity > 0.3:  # High similarity threshold
                    print(f"   ✅ High similarity match: {similarity:.3f}")
                    success = True
                else:
                    print(f"   ⚠️  Partial match: Topic '{topic}', Form '{form_code}'")
                
                test_results.append({
                    "query": query,
                    "success": success,
                    "similarity": similarity,
                    "topic": topic,
                    "form_code": form_code,
                    "search_time": search_time
                })
                
            else:
                print(f"   ❌ No results found")
                test_results.append({
                    "query": query,
                    "success": False,
                    "similarity": 0,
                    "topic": None,
                    "form_code": None,
                    "search_time": search_time
                })
        
        return test_results
    
    def test_metadata_filtering(self):
        """Test metadata-based filtering."""
        print("\n🏷️  TESTING METADATA FILTERING")
        print("-" * 40)
        
        metadata_tests = [
            {"topic": "divorce"},
            {"topic": "adoption"},
            {"topic": "domestic violence"},
            {"form_code": "FL-180"},
            {"form_code": "DV-100"}
        ]
        
        for test_filter in metadata_tests:
            print(f"\n🔍 Filtering by: {test_filter}")
            
            start_time = time.time()
            results = self.search_by_metadata(test_filter, limit=10)
            search_time = time.time() - start_time
            
            if results:
                print(f"   ✅ Found {len(results)} results in {search_time:.3f}s")
                
                # Show sample results
                for i, result in enumerate(results[:3], 1):
                    metadata = result.get('metadata', {})
                    form_code = metadata.get('form_code', 'Unknown')
                    topic = metadata.get('topic', 'Unknown')
                    print(f"   {i}. {form_code} - {topic}")
            else:
                print(f"   ❌ No results found")
    
    def test_database_stats(self):
        """Get database statistics."""
        print("\n📊 DATABASE STATISTICS")
        print("-" * 40)
        
        try:
            # Total records
            total_result = self.supabase_client.table('crawled_pages').select('id', count='exact').execute()
            total_records = total_result.count if hasattr(total_result, 'count') else len(total_result.data)
            
            print(f"📄 Total records: {total_records}")
            
            # Records by topic
            topics_result = self.supabase_client.table('crawled_pages').select('metadata').execute()
            
            if topics_result.data:
                topic_counts = {}
                for record in topics_result.data:
                    metadata = record.get('metadata', {})
                    topic = metadata.get('topic', 'Unknown')
                    topic_counts[topic] = topic_counts.get(topic, 0) + 1
                
                print(f"\n📋 Records by topic:")
                for topic, count in sorted(topic_counts.items()):
                    print(f"   {topic}: {count} forms")
                
                print(f"\n🏷️  Total topics: {len(topic_counts)}")
            
            # Check embedding quality
            sample_result = self.supabase_client.table('crawled_pages').select('embedding').limit(5).execute()
            
            if sample_result.data:
                embeddings_with_data = 0
                for record in sample_result.data:
                    embedding = record.get('embedding')
                    if embedding and len(embedding) == 384:
                        embeddings_with_data += 1
                
                print(f"🔢 Embedding quality check: {embeddings_with_data}/5 samples have valid 384-dim embeddings")
            
        except Exception as e:
            print(f"❌ Error getting database stats: {e}")
    
    def run_comprehensive_test(self):
        """Run all vector search tests."""
        print("🚀 COMPREHENSIVE VECTOR SEARCH TEST")
        print("=" * 60)
        
        start_time = time.time()
        
        # Test 1: Database Statistics
        self.test_database_stats()
        
        # Test 2: Basic Vector Search
        test_results = self.test_basic_vector_search()
        
        # Test 3: Metadata Filtering
        self.test_metadata_filtering()
        
        total_time = time.time() - start_time
        
        # Summary
        print(f"\n🎉 TEST SUMMARY")
        print("=" * 30)
        print(f"⏱️  Total test time: {total_time:.2f}s")
        
        if test_results:
            successful_tests = sum(1 for result in test_results if result["success"])
            success_rate = (successful_tests / len(test_results)) * 100
            avg_similarity = sum(result["similarity"] for result in test_results if result["similarity"]) / len([r for r in test_results if r["similarity"]])
            
            print(f"✅ Successful searches: {successful_tests}/{len(test_results)} ({success_rate:.1f}%)")
            print(f"📊 Average similarity score: {avg_similarity:.3f}")
            
            if success_rate >= 80:
                print("🎉 VECTOR SEARCH IS WORKING EXCELLENTLY!")
            elif success_rate >= 60:
                print("✅ Vector search is working well!")
            else:
                print("⚠️  Vector search needs improvement")
        
        # Save detailed results
        results_data = {
            "test_time": total_time,
            "test_results": test_results,
            "timestamp": time.time()
        }
        
        with open('vector_search_test_results.json', 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Detailed results saved to: vector_search_test_results.json")
        
        return test_results

def main():
    """Main test function."""
    try:
        tester = VectorSearchTester()
        results = tester.run_comprehensive_test()
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 