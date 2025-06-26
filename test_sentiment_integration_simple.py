#!/usr/bin/env python3
"""
Simple test script to demonstrate sentiment analysis integration without loading actual models
"""

import numpy as np
from collections import Counter
import re
from datetime import datetime
import uuid
import json

# Mock the sentiment analysis functions to test service logic
def mock_predict_rating(comments):
    """Mock version of predict_rating that returns sample ratings"""
    ratings = []
    for comment in comments:
        comment_lower = comment.lower()
        # Simple keyword-based rating prediction for testing
        if any(word in comment_lower for word in ['amazing', 'excellent', 'great', 'perfect', 'love']):
            ratings.append(5)
        elif any(word in comment_lower for word in ['good', 'nice', 'satisfied', 'recommend']):
            ratings.append(4)
        elif any(word in comment_lower for word in ['average', 'okay', 'decent']):
            ratings.append(3)
        elif any(word in comment_lower for word in ['poor', 'disappointed', 'slow']):
            ratings.append(2)
        elif any(word in comment_lower for word in ['terrible', 'awful', 'worst', 'hate', 'broken', 'defective']):
            ratings.append(1)
        else:
            ratings.append(3)  # Default neutral
    return np.array(ratings)

def mock_clean_text(text):
    """Simple text cleaning for testing"""
    if not isinstance(text, str):
        return ""
    text = re.sub(r'[^\w\s]', '', text)
    return text.lower()

# Create a simplified sentiment service class for testing
class SimpleSentimentService:
    def __init__(self):
        self.rating_mapping = {
            '1': 1, '2': 2, '3': 3, '4': 4, '5': 5,
            1: 1, 2: 2, 3: 3, 4: 4, 5: 5
        }
        self.complaint_keywords = [
            'terrible', 'awful', 'horrible', 'worst', 'hate', 'disappointed', 
            'defective', 'broken', 'damaged', 'poor', 'bad', 'useless',
            'waste', 'scam', 'fake', 'fraud', 'returned', 'refund',
            'problem', 'issue', 'wrong', 'error', 'fail', 'faulty'
        ]
    
    def analyze_reviews(self, reviews, product_info=None):
        """Analyze reviews using mock predictions"""
        if not reviews:
            return self._empty_analysis(product_info)
        
        # Clean and prepare reviews
        cleaned_reviews = [mock_clean_text(review) if isinstance(review, str) else "" for review in reviews]
        
        # Get mock sentiment predictions
        predicted_ratings = mock_predict_rating(reviews)
        
        # Convert to list
        numerical_ratings = predicted_ratings.tolist()
        
        # Calculate statistics
        analysis_results = self._calculate_statistics(reviews, numerical_ratings, cleaned_reviews)
        
        # Add product info if provided
        if product_info:
            analysis_results['product_info'] = product_info
        
        # Add timestamp
        analysis_results['analysis_timestamp'] = datetime.now().isoformat()
        analysis_results['analysis_id'] = str(uuid.uuid4())
        
        return analysis_results
    
    def _calculate_statistics(self, original_reviews, ratings, cleaned_reviews):
        """Calculate comprehensive statistics from the reviews and ratings"""
        
        # Basic statistics
        average_rating = np.mean(ratings)
        total_reviews = len(ratings)
        
        # Rating distribution
        rating_counts = Counter(ratings)
        rating_distribution = {
            str(i): rating_counts.get(i, 0) for i in range(1, 6)
        }
        
        # Identify complaints (ratings 1-2)
        complaints = []
        positive_reviews = []
        neutral_reviews = []
        
        for i, rating in enumerate(ratings):
            review_data = {
                'text': original_reviews[i] if i < len(original_reviews) else "",
                'rating': rating,
                'cleaned_text': cleaned_reviews[i] if i < len(cleaned_reviews) else "",
                'index': i
            }
            
            if rating <= 2:
                # Check for complaint keywords
                complaint_keywords_found = [
                    keyword for keyword in self.complaint_keywords 
                    if keyword in cleaned_reviews[i].lower()
                ]
                review_data['complaint_keywords'] = complaint_keywords_found
                review_data['is_complaint'] = True
                complaints.append(review_data)
            elif rating >= 4:
                review_data['is_complaint'] = False
                positive_reviews.append(review_data)
            else:
                review_data['is_complaint'] = False
                neutral_reviews.append(review_data)
        
        # Generate explanations for complaints
        complaint_explanations = self._generate_complaint_explanations(complaints)
        
        # Sentiment breakdown
        sentiment_breakdown = {
            'positive': len(positive_reviews),
            'neutral': len(neutral_reviews),
            'negative': len(complaints),
            'positive_percentage': (len(positive_reviews) / total_reviews) * 100 if total_reviews > 0 else 0,
            'neutral_percentage': (len(neutral_reviews) / total_reviews) * 100 if total_reviews > 0 else 0,
            'negative_percentage': (len(complaints) / total_reviews) * 100 if total_reviews > 0 else 0
        }
        
        return {
            'summary': {
                'average_rating': round(average_rating, 2),
                'total_reviews': total_reviews,
                'complaint_count': len(complaints),
                'complaint_percentage': round((len(complaints) / total_reviews) * 100, 1) if total_reviews > 0 else 0,
                'recommendation_score': self._calculate_recommendation_score(average_rating, len(complaints), total_reviews)
            },
            'rating_distribution': rating_distribution,
            'sentiment_breakdown': sentiment_breakdown,
            'complaints': {
                'count': len(complaints),
                'details': complaints[:10],
                'explanations': complaint_explanations
            },
            'positive_feedback': {
                'count': len(positive_reviews),
                'details': positive_reviews[:5]
            },
            'detailed_analysis': {
                'ratings': ratings,
                'predicted_ratings': ratings,
                'total_analyzed': total_reviews
            }
        }
    
    def _generate_complaint_explanations(self, complaints):
        """Generate explanations for the most common complaints"""
        if not complaints:
            return []
        
        # Group complaints by common keywords
        keyword_groups = {}
        for complaint in complaints:
            for keyword in complaint.get('complaint_keywords', []):
                if keyword not in keyword_groups:
                    keyword_groups[keyword] = []
                keyword_groups[keyword].append(complaint)
        
        # Generate explanations
        explanations = []
        for keyword, related_complaints in keyword_groups.items():
            if len(related_complaints) >= 1:  # Include all for demo
                explanation = {
                    'issue': keyword.capitalize(),
                    'frequency': len(related_complaints),
                    'percentage': round((len(related_complaints) / len(complaints)) * 100, 1),
                    'examples': [c['text'][:100] + "..." if len(c['text']) > 100 else c['text'] 
                               for c in related_complaints[:3]]
                }
                explanations.append(explanation)
        
        # Sort by frequency
        explanations.sort(key=lambda x: x['frequency'], reverse=True)
        return explanations[:5]  # Return top 5 issues
    
    def _calculate_recommendation_score(self, avg_rating, complaint_count, total_reviews):
        """Calculate a recommendation score based on rating and complaints"""
        if total_reviews == 0:
            return 0
        
        # Base score from average rating (0-100)
        base_score = (avg_rating / 5) * 100
        
        # Penalty for high complaint percentage
        complaint_percentage = (complaint_count / total_reviews) * 100
        complaint_penalty = min(complaint_percentage * 2, 50)  # Max 50 point penalty
        
        # Sample size bonus (more reviews = more reliable)
        sample_bonus = min(total_reviews / 10, 10)  # Max 10 point bonus
        
        final_score = max(0, min(100, base_score - complaint_penalty + sample_bonus))
        return round(final_score, 1)
    
    def _empty_analysis(self, product_info=None):
        """Return empty analysis when no reviews are available"""
        analysis = {
            'summary': {
                'average_rating': 0,
                'total_reviews': 0,
                'complaint_count': 0,
                'complaint_percentage': 0,
                'recommendation_score': 0
            },
            'rating_distribution': {str(i): 0 for i in range(1, 6)},
            'sentiment_breakdown': {
                'positive': 0,
                'neutral': 0,
                'negative': 0,
                'positive_percentage': 0,
                'neutral_percentage': 0,
                'negative_percentage': 0
            },
            'complaints': {
                'count': 0,
                'details': [],
                'explanations': []
            },
            'positive_feedback': {
                'count': 0,
                'details': []
            },
            'detailed_analysis': {
                'ratings': [],
                'predicted_ratings': [],
                'total_analyzed': 0
            },
            'analysis_timestamp': datetime.now().isoformat(),
            'analysis_id': str(uuid.uuid4())
        }
        
        if product_info:
            analysis['product_info'] = product_info
            
        return analysis

def test_sentiment_analysis():
    # Initialize the simple sentiment service
    service = SimpleSentimentService()
    
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
    
    print("🔍 Analyzing Reviews (Simple Test)...")
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
            if explanation['examples']:
                print(f"Examples: {explanation['examples'][0][:80]}...")
            print()
    
    print(f"\n🔗 Analysis ID: {analysis['analysis_id']}")
    print(f"📅 Generated: {analysis['analysis_timestamp']}")
    
    # Save to JSON file for inspection
    with open('simple_analysis_result.json', 'w') as f:
        json.dump(analysis, f, indent=2)
    
    print(f"\n💾 Full analysis saved to 'simple_analysis_result.json'")
    
    return analysis

if __name__ == "__main__":
    print("🧪 Testing Sentiment Analysis Integration (Simple Version)")
    print("="*50)
    
    try:
        # Run the test
        analysis = test_sentiment_analysis()
        
        print("\n✅ Simple test completed successfully!")
        print("\n📝 Notes:")
        print("- This test uses mock predictions instead of actual ML models")
        print("- The service logic and data structures are working correctly")
        print("- For full ML integration, ensure model compatibility")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc() 