#!/usr/bin/env python3
"""
Test script to demonstrate sentiment analysis integration
"""

from sentiment_service import SentimentService
import json

def test_sentiment_analysis():
    # Initialize the sentiment service
    service = SentimentService()
    
    # Example reviews for testing
    test_reviews = [
        "This product is amazing! Great quality and fast shipping. Highly recommend!",
        "Terrible quality. Broke after one day. Waste of money.",
        "Average product. Nothing special but does the job.",
        "Excellent customer service and the product works perfectly. Love it!",
        "Poor packaging, arrived damaged. Very disappointed with this purchase.",
        "Good value for money. Quality is decent for the price.",
        "Worst product I've ever bought. Completely useless and overpriced.",
        "Fast delivery and great product. Exactly what I expected.",
        "Product description was misleading. Not as advertised.",
        "Perfect! Exactly what I needed. Will buy again.",
        "Cheap quality materials. Feels flimsy and unreliable.",
        "Satisfied with the purchase. Good product overall.",
        "Defective item received. Had to return it immediately.",
        "Awesome product! Exceeded my expectations in every way.",
        "Slow shipping but the product is good quality."
    ]
    
    # Example product info
    product_info = {
        "name": "Test Product - Wireless Headphones",
        "image": "https://example.com/headphones.jpg",
        "rating": 4.2,
        "review_count": 15
    }
    
    print("🔍 Analyzing Reviews...")
    print("="*50)
    
    # Perform sentiment analysis
    analysis = service.analyze_reviews(test_reviews, product_info)
    
    # Display results
    print("\n📊 SENTIMENT ANALYSIS RESULTS")
    print("="*50)
    
    # Summary
    summary = analysis['summary']
    print(f"📈 Average Rating: {summary['average_rating']}/5")
    print(f"📝 Total Reviews: {summary['total_reviews']}")
    print(f"⚠️  Complaints: {summary['complaint_count']} ({summary['complaint_percentage']}%)")
    print(f"🎯 Recommendation Score: {summary['recommendation_score']}/100")
    
    # Sentiment breakdown
    print(f"\n🎭 SENTIMENT BREAKDOWN")
    print("-"*30)
    sentiment = analysis['sentiment_breakdown']
    print(f"😊 Positive: {sentiment['positive']} ({sentiment['positive_percentage']:.1f}%)")
    print(f"😐 Neutral: {sentiment['neutral']} ({sentiment['neutral_percentage']:.1f}%)")
    print(f"😞 Negative: {sentiment['negative']} ({sentiment['negative_percentage']:.1f}%)")
    
    # Rating distribution
    print(f"\n⭐ RATING DISTRIBUTION")
    print("-"*30)
    rating_dist = analysis['rating_distribution']
    for rating in range(5, 0, -1):
        stars = "★" * rating + "☆" * (5-rating)
        count = rating_dist[str(rating)]
        print(f"{stars} {rating}: {count} reviews")
    
    # Complaints analysis
    if analysis['complaints']['count'] > 0:
        print(f"\n🚨 COMPLAINT ANALYSIS")
        print("-"*30)
        explanations = analysis['complaints']['explanations']
        for explanation in explanations:
            print(f"Issue: {explanation['issue']}")
            print(f"Frequency: {explanation['frequency']} times ({explanation['percentage']}%)")
            print(f"Examples: {explanation['examples'][0][:80]}...")
            print()
    
    # Positive themes
    if analysis['positive_feedback']['common_themes']:
        print(f"\n✨ POSITIVE THEMES")
        print("-"*30)
        for theme in analysis['positive_feedback']['common_themes']:
            print(f"• {theme['theme']}: {theme['mentions']} mentions ({theme['percentage']}%)")
    
    print(f"\n🔗 Analysis ID: {analysis['analysis_id']}")
    print(f"📅 Generated: {analysis['analysis_timestamp']}")
    
    # Save to JSON file for inspection
    with open('sample_analysis_result.json', 'w') as f:
        json.dump(analysis, f, indent=2)
    
    print(f"\n💾 Full analysis saved to 'sample_analysis_result.json'")
    
    return analysis

def test_api_format():
    """Test how the data would look when returned via API"""
    service = SentimentService()
    
    # Simple test with fewer reviews
    simple_reviews = [
        "Love this product! Amazing quality and fast shipping.",
        "Terrible. Broke immediately. Don't buy this.",
        "Good product, fair price. Recommended.",
        "Worst purchase ever. Complete waste of money."
    ]
    
    analysis = service.analyze_reviews(simple_reviews)
    
    print("\n🔌 API Response Format:")
    print("="*50)
    print(json.dumps(analysis, indent=2))

if __name__ == "__main__":
    print("🧪 Testing Sentiment Analysis Integration")
    print("="*50)
    
    try:
        # Run the main test
        analysis = test_sentiment_analysis()
        
        # Test API format
        test_api_format()
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc() 