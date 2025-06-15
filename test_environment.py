#!/usr/bin/env python3
"""
Test script to verify environment variables and system components.
"""
import os
import sys
from dotenv import load_dotenv

def test_environment():
    """Test that all required environment variables are set."""
    print("🧪 Testing Environment Configuration")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Required environment variables
    required_vars = {
        'LLM_API_KEY': 'LLM API key for AI responses',
        'SUPABASE_URL': 'Supabase project URL',
        'SUPABASE_SERVICE_KEY': 'Supabase service role key'
    }
    
    # Optional environment variables
    optional_vars = {
        'LLM_API_URL': 'LLM API endpoint URL',
        'MCP_BASE_URL': 'MCP server base URL'
    }
    
    all_good = True
    
    print("\n📋 Required Environment Variables:")
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Show first 20 chars for security
            masked_value = value[:20] + "..." if len(value) > 20 else value
            print(f"  ✅ {var}: {masked_value}")
        else:
            print(f"  ❌ {var}: NOT SET - {description}")
            all_good = False
    
    print("\n📋 Optional Environment Variables:")
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {value}")
        else:
            print(f"  ⚠️  {var}: Using default - {description}")
    
    return all_good

def test_imports():
    """Test that all required packages can be imported."""
    print("\n🔧 Testing Package Imports")
    print("=" * 50)
    
    packages = [
        ('dotenv', 'python-dotenv'),
        ('supabase', 'supabase'),
        ('sentence_transformers', 'sentence-transformers'),
        ('numpy', 'numpy'),
        ('flask', 'flask')
    ]
    
    all_good = True
    
    for package, pip_name in packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - Install with: pip install {pip_name}")
            all_good = False
    
    return all_good

def test_agent_initialization():
    """Test that the court forms agent can be initialized."""
    print("\n🤖 Testing Agent Initialization")
    print("=" * 50)
    
    try:
        from court_forms_agent import CourtFormsAgent
        agent = CourtFormsAgent()
        print("  ✅ CourtFormsAgent initialized successfully")
        
        # Test database connection
        stats = agent.get_database_stats()
        if stats.get('database_ready'):
            print(f"  ✅ Database connected: {stats.get('total_forms', 0)} forms available")
            return True
        else:
            print(f"  ❌ Database connection failed: {stats.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"  ❌ Agent initialization failed: {e}")
        return False

def test_vector_search():
    """Test vector search functionality."""
    print("\n🔍 Testing Vector Search")
    print("=" * 50)
    
    try:
        from court_forms_agent import CourtFormsAgent
        agent = CourtFormsAgent()
        
        # Test a simple search
        results = agent.search_vector_database("divorce forms", limit=3)
        
        if results:
            print(f"  ✅ Vector search working: Found {len(results)} results")
            for i, result in enumerate(results[:2], 1):
                title = result.get('title', 'Unknown')[:50] + "..."
                similarity = result.get('similarity', 0)
                print(f"    {i}. {title} (similarity: {similarity:.3f})")
            return True
        else:
            print("  ❌ Vector search returned no results")
            return False
            
    except Exception as e:
        print(f"  ❌ Vector search failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 California Legal Forms Assistant - System Test")
    print("=" * 60)
    
    tests = [
        ("Environment Variables", test_environment),
        ("Package Imports", test_imports),
        ("Agent Initialization", test_agent_initialization),
        ("Vector Search", test_vector_search)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! System is ready to use.")
        print("🚀 Start the system with: ./start_system.sh")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the configuration.")
        print("📖 See README.md for setup instructions.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 