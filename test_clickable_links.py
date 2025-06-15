#!/usr/bin/env python3
"""
Test script to demonstrate enhanced clickable links functionality.
"""
import requests
import json

def test_clickable_links():
    """Test that forms now have clickable URLs."""
    print("🔗 Testing Enhanced Clickable Links Functionality")
    print("=" * 60)
    
    base_url = "http://localhost:5000"
    
    # Test 1: Guidance forms with clickable links
    print("\n1. Testing Guidance Forms (Divorce Query)")
    print("-" * 40)
    
    try:
        response = requests.post(f"{base_url}/api/ask", 
                               json={"question": "I need help with divorce papers"})
        data = response.json()
        
        guidance = data.get('guidance', {})
        forms = guidance.get('forms', [])
        
        if forms:
            print(f"✅ Found {len(forms)} guidance forms with URLs:")
            for form in forms:
                code = form.get('code', 'N/A')
                name = form.get('name', 'N/A')
                url = form.get('url', 'No URL')
                print(f"  📄 {code}: {name}")
                print(f"     🔗 {url}")
                print()
        else:
            print("❌ No guidance forms found")
            
    except Exception as e:
        print(f"❌ Error testing guidance forms: {e}")
    
    # Test 2: Vector search results with clickable links
    print("\n2. Testing Vector Search Results")
    print("-" * 40)
    
    try:
        response = requests.post(f"{base_url}/api/search", 
                               json={"query": "child custody forms", "limit": 3})
        data = response.json()
        
        forms = data.get('forms', [])
        
        if forms:
            print(f"✅ Found {len(forms)} search results with URLs:")
            for form in forms:
                code = form.get('code', 'N/A')
                title = form.get('title', 'N/A')[:50] + "..."
                url = form.get('url', 'No URL')
                similarity = form.get('similarity', 0)
                print(f"  📄 {code}: {title}")
                print(f"     🎯 Similarity: {similarity:.3f}")
                print(f"     🔗 {url}")
                print()
        else:
            print("❌ No search results found")
            
    except Exception as e:
        print(f"❌ Error testing search results: {e}")
    
    # Test 3: Different legal topics
    print("\n3. Testing Different Legal Topics")
    print("-" * 40)
    
    topics_to_test = [
        ("adoption", "I want to adopt a child"),
        ("child support", "How do I request child support?"),
        ("restraining order", "I need a restraining order")
    ]
    
    for topic, question in topics_to_test:
        try:
            response = requests.post(f"{base_url}/api/ask", json={"question": question})
            data = response.json()
            
            guidance = data.get('guidance', {})
            forms = guidance.get('forms', [])
            
            forms_with_urls = [f for f in forms if f.get('url')]
            
            print(f"  📋 {topic.title()}: {len(forms_with_urls)}/{len(forms)} forms have URLs")
            
        except Exception as e:
            print(f"  ❌ Error testing {topic}: {e}")
    
    # Test 4: Frontend accessibility
    print("\n4. Testing Frontend Accessibility")
    print("-" * 40)
    
    try:
        response = requests.get(f"{base_url}")
        if response.status_code == 200:
            html_content = response.text
            
            # Check for enhanced link styling
            if 'form-url' in html_content and 'background: var(--primary-gradient)' in html_content:
                print("✅ Enhanced button styling detected in frontend")
            else:
                print("⚠️  Enhanced button styling not detected")
                
            # Check for accessibility features
            if 'target="_blank"' in html_content and 'rel="noopener noreferrer"' in html_content:
                print("✅ Secure external link attributes detected")
            else:
                print("⚠️  Secure external link attributes not detected")
                
            if 'title=' in html_content:
                print("✅ Accessibility tooltips detected")
            else:
                print("⚠️  Accessibility tooltips not detected")
                
        else:
            print(f"❌ Frontend not accessible (status: {response.status_code})")
            
    except Exception as e:
        print(f"❌ Error testing frontend: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Clickable Links Enhancement Test Complete!")
    print("\n📋 Summary of Enhancements:")
    print("  • Guidance forms now have clickable URLs")
    print("  • Vector search results include clickable links")
    print("  • Enhanced button styling with gradients and hover effects")
    print("  • Accessibility features: tooltips, secure external links")
    print("  • Responsive design for mobile and desktop")
    print("\n🌐 Open http://localhost:5000 to see the enhanced interface!")

if __name__ == "__main__":
    test_clickable_links() 