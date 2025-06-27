#!/usr/bin/env python3
"""
Test script to verify complaint analysis integration with sentiment analysis
"""

import requests
import json
import time

# Test data
TEST_REVIEWS = [
    "This product is amazing! Great quality and fast shipping.",
    "Terrible sound quality, very disappointing. The bass is awful and it sounds muffled.",
    "Good value for money but the battery life is too short.",
    "Uncomfortable to wear for long periods. Hurts my ears after 30 minutes.",
    "Connection keeps dropping, very frustrating Bluetooth issues.",
    "Product arrived damaged, poor packaging. Customer service was unhelpful.",
    "Overpriced for what you get. Not worth the money at all.",
    "Perfect! Love everything about this product. Highly recommend.",
    "The material feels cheap and flimsy. Broke after a week of use.",
    "Average product, nothing special but works as expected."
]

def test_analyze_reviews_endpoint():
    """Test the updated analyze-reviews endpoint with complaint analysis"""
    url = "http://localhost:8080/api/analyze-reviews"
    
    payload = {
        "reviews": TEST_REVIEWS,
        "product_info": {
            "name": "Test Product",
            "image": "https://example.com/image.jpg"
        }
    }
    
    try:
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            
            print("✅ Analyze Reviews Endpoint Test - SUCCESS")
            print(f"Analysis Method: {data.get('analysis_method', 'Unknown')}")
            print(f"Complaint Analysis Available: {data.get('complaint_analysis_available', False)}")
            
            # Check if complaint analysis is included
            if 'complaint_analysis' in data:
                complaint_data = data['complaint_analysis']
                print(f"Advanced Analysis: {complaint_data.get('advanced_analysis_available', False)}")
                
                if complaint_data.get('advanced_analysis_available'):
                    print(f"Top Complaints: {len(complaint_data.get('top_complaints', []))}")
                    print(f"Total Complaint Mentions: {complaint_data.get('total_complaint_mentions', 0)}")
                    
                    # Print top complaints
                    for i, (category, count, description) in enumerate(complaint_data.get('top_complaints', [])[:3]):
                        print(f"  {i+1}. {category}: {count} mentions - {description}")
            
            print(f"Average Rating: {data.get('summary', {}).get('average_rating', 'N/A')}")
            print(f"Total Reviews: {data.get('summary', {}).get('total_reviews', 'N/A')}")
            print(f"Complaint Percentage: {data.get('summary', {}).get('complaint_percentage', 'N/A')}%")
            
            return True
        else:
            print(f"❌ Analyze Reviews Endpoint Test - FAILED: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Analyze Reviews Endpoint Test - ERROR: {e}")
        return False

def test_complaint_categories_endpoint():
    """Test the complaint categories endpoint"""
    url = "http://localhost:8080/api/complaints/categories"
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            
            print("\n✅ Complaint Categories Endpoint Test - SUCCESS")
            print(f"Total Categories: {data.get('total_categories', 0)}")
            
            for category in data.get('categories', [])[:3]:
                print(f"  - {category.get('display_name')}: {category.get('description')}")
            
            return True
        else:
            print(f"\n❌ Complaint Categories Endpoint Test - FAILED: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"\n❌ Complaint Categories Endpoint Test - ERROR: {e}")
        return False

def test_analyze_text_endpoint():
    """Test the text complaint analysis endpoint"""
    url = "http://localhost:8080/api/complaints/analyze-text"
    
    test_text = "The sound quality is terrible and the battery dies too quickly. Very disappointed with this purchase."
    
    payload = {
        "text": test_text,
        "threshold": 0.5
    }
    
    try:
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            
            print("\n✅ Analyze Text Endpoint Test - SUCCESS")
            print(f"Text: {data.get('text', '')[:50]}...")
            print(f"Complaints Found: {data.get('total_complaints', 0)}")
            
            complaints = data.get('complaints_found', {})
            for category, details in complaints.items():
                print(f"  - {category}: {details.get('score', 0):.2f} confidence")
            
            return True
        else:
            print(f"\n❌ Analyze Text Endpoint Test - FAILED: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"\n❌ Analyze Text Endpoint Test - ERROR: {e}")
        return False

def main():
    """Run all tests"""
    print("🔍 Testing Complaint Analysis Integration\n")
    print("=" * 50)
    
    # Wait a moment for server to be ready
    time.sleep(1)
    
    tests = [
        test_analyze_reviews_endpoint,
        test_complaint_categories_endpoint,
        test_analyze_text_endpoint
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        time.sleep(1)  # Brief delay between tests
    
    print("\n" + "=" * 50)
    print(f"Tests Completed: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Complaint analysis integration is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the error messages above.")

if __name__ == "__main__":
    main() 