import numpy as np
from collections import Counter
import re
from datetime import datetime
import uuid
import logging
import time

# Import complaint analysis modules
try:
    from complaint_modal.inference import count_complaints_by_category, get_top_complaints_zeroshot
    COMPLAINT_ANALYSIS_AVAILABLE = True
    print("✅ Complaint analysis modules loaded successfully")
except Exception as e:
    print(f"⚠️  Complaint analysis unavailable ({e})")
    COMPLAINT_ANALYSIS_AVAILABLE = False

# Set up logger
logger = logging.getLogger(__name__)

# Try to import ML-based sentiment analysis, fall back to simple analysis if failed
try:
    from sentiment_analyzer import predict_rating, clean_text
    ML_AVAILABLE = True
    print("✅ ML-based sentiment analysis loaded successfully")
    # However, disable ML for now due to compatibility issues
    USE_ML = False
    print("⚠️  Using keyword-based analysis due to model compatibility issues")
except Exception as e:
    print(f"⚠️  ML models unavailable ({e}), using simple keyword-based analysis")
    ML_AVAILABLE = False
    USE_ML = False
    
    # Simple fallback implementations
    def predict_rating(comments):
        """Simple keyword-based rating prediction"""
        ratings = []
        for comment in comments:
            comment_lower = str(comment).lower()
            if any(word in comment_lower for word in ['amazing', 'excellent', 'great', 'perfect', 'love', 'awesome']):
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
    
    def clean_text(text):
        """Simple text cleaning"""
        if not isinstance(text, str):
            return ""
        text = re.sub(r'[^\w\s]', '', text)
        return text.lower()

class SentimentService:
    def __init__(self):
        """Initialize the sentiment analysis service"""
        logger.info("🔍 Initializing Sentiment Analysis Service...")
        
        # Use the ML availability status from module level
        self.ml_available = ML_AVAILABLE
        
        # Define specific quality-based complaint categories
        self.quality_categories = {
            'material_quality': [
                'cheap', 'flimsy', 'plastic', 'fragile', 'poor quality', 'build quality',
                'material', 'construction', 'sturdy', 'durable', 'solid', 'weak',
                'breaks', 'broken', 'fell apart', 'defective', 'manufacturing'
            ],
            'sound_quality': [
                'sound', 'audio', 'bass', 'treble', 'clarity', 'volume', 'noise',
                'distortion', 'muffled', 'tinny', 'crisp', 'clear', 'muddy',
                'loud', 'quiet', 'music', 'quality', 'speakers', 'headphones'
            ],
            'comfort_quality': [
                'comfort', 'comfortable', 'uncomfortable', 'fit', 'fits', 'tight',
                'loose', 'painful', 'hurt', 'ears', 'head', 'pressure', 'heavy',
                'light', 'soft', 'hard', 'padding', 'cushion', 'ergonomic'
            ],
            'battery_quality': [
                'battery', 'charge', 'charging', 'power', 'died', 'drain', 'last',
                'life', 'hours', 'long', 'short', 'quick', 'slow'
            ],
            'connectivity_quality': [
                'bluetooth', 'connection', 'connect', 'pair', 'pairing', 'wireless',
                'signal', 'range', 'disconnect', 'drops', 'lag', 'delay'
            ],
            'price_quality': [
                'price', 'expensive', 'cheap', 'cost', 'value', 'money', 'worth',
                'overpriced', 'affordable', 'budget', 'dollar'
            ],
            'shipping_quality': [
                'shipping', 'delivery', 'package', 'packaging', 'box', 'arrived',
                'fast', 'slow', 'damaged', 'late', 'quick'
            ]
        }
        
        # General complaint keywords (fallback)
        self.complaint_keywords = [
            'terrible', 'awful', 'horrible', 'bad', 'worst', 'hate', 'disappointed',
            'regret', 'waste', 'useless', 'broken', 'defective', 'poor', 'cheap',
            'flimsy', 'uncomfortable', 'painful', 'difficult', 'problem', 'issue',
            'complaint', 'return', 'refund', 'exchange', 'wrong', 'error'
        ]
        
        if self.ml_available:
            logger.info("✅ ML-based sentiment analysis loaded successfully")
        else:
            logger.warning("⚠️ Using keyword-based analysis due to ML model issues")
    
    def analyze_reviews(self, reviews, product_info=None):
        """
        Analyze a list of reviews and return comprehensive sentiment analysis
        
        Args:
            reviews (list): List of review texts
            product_info (dict): Product information including name, image, etc.
        
        Returns:
            dict: Complete analysis results
        """
        if not reviews:
            return self._empty_analysis(product_info)
        
        import time
        total_start_time = time.time()
        print(f"📝 Starting complete analysis for {len(reviews)} reviews...")
        
        try:
            # Clean and prepare reviews
            clean_start = time.time()
            cleaned_reviews = [clean_text(review) if isinstance(review, str) else "" for review in reviews]
            clean_time = time.time() - clean_start
            print(f"🧹 Text cleaning completed in {clean_time:.2f} seconds")
            
            # Get sentiment predictions (use keyword-based for now due to compatibility)
            rating_start = time.time()
            if USE_ML and self.ml_available:
                predicted_ratings = predict_rating(reviews)
            else:
                # Use keyword-based analysis
                predicted_ratings = []
                for comment in reviews:
                    comment_lower = str(comment).lower()
                    if any(word in comment_lower for word in ['amazing', 'excellent', 'great', 'perfect', 'love', 'awesome']):
                        predicted_ratings.append(5)
                    elif any(word in comment_lower for word in ['good', 'nice', 'satisfied', 'recommend']):
                        predicted_ratings.append(4)
                    elif any(word in comment_lower for word in ['average', 'okay', 'decent']):
                        predicted_ratings.append(3)
                    elif any(word in comment_lower for word in ['poor', 'disappointed', 'slow']):
                        predicted_ratings.append(2)
                    elif any(word in comment_lower for word in ['terrible', 'awful', 'worst', 'hate', 'broken', 'defective']):
                        predicted_ratings.append(1)
                    else:
                        predicted_ratings.append(3)  # Default neutral
                predicted_ratings = np.array(predicted_ratings)
            
            rating_time = time.time() - rating_start
            print(f"⭐ Rating prediction completed in {rating_time:.2f} seconds")
            
            # Note: complaint analysis is done later, only sentiment prediction here
            
            # Calculate statistics
            stats_start = time.time()
            analysis_results = self._calculate_statistics(reviews, predicted_ratings, cleaned_reviews, product_info)
            stats_time = time.time() - stats_start
            print(f"📊 Statistics calculation completed in {stats_time:.2f} seconds")
            
            # Add complaint analysis using inference.py + complaint_categories_zeroshot.py
            if COMPLAINT_ANALYSIS_AVAILABLE:
                try:
                    import time
                    start_time = time.time()
                    print(f"🚀 Starting zero-shot complaint analysis for {len(reviews)} reviews...")
                    
                    # Use inference.py for complaint analysis with optimized batch processing
                    batch_size = 32 if len(reviews) > 50 else 16  # Larger batches for more reviews
                    threshold = 0.3  # Lower threshold for better recall
                    
                    # Process once and get counts + extract complaint reviews
                    complaint_counts, complaint_reviews = count_complaints_by_category(
                        reviews, threshold=threshold, batch_size=batch_size, extract_reviews=True
                    )
                    
                    # Get top complaints from the counts (no additional processing needed)
                    top_complaints = self._get_top_complaints_from_counts(complaint_counts, top_n=3)
                    
                    # Add complaint reviews to analysis results
                    analysis_results['complaint_reviews'] = complaint_reviews[:10]  # Limit to top 10
                    print(f"📝 Extracted {len(complaint_reviews[:10])} complaint reviews")
                    
                    # Log complaint reviews details
                    if complaint_reviews:
                        print(f"📝 Complaint reviews extracted:")
                        for i, review in enumerate(complaint_reviews[:5]):  # Show first 5
                            print(f"   {i+1}. [{review.get('complaint_type', 'unknown')}] {review.get('text', 'No text')[:60]}... (confidence: {review.get('confidence', 'N/A')})")
                        if len(complaint_reviews) > 5:
                            print(f"   ... and {len(complaint_reviews) - 5} more complaint reviews")
                    
                    # Format top_complaints as [category, count] pairs
                    formatted_top_complaints = [[complaint[0], complaint[1]] for complaint in top_complaints]
                    
                    analysis_results['top_complaints'] = formatted_top_complaints
                    analysis_results['complaint_categories'] = complaint_counts
                    
                    elapsed_time = time.time() - start_time
                    print(f"✅ Zero-shot complaint analysis completed in {elapsed_time:.2f} seconds")
                    
                except Exception as e:
                    print(f"Error in zero-shot complaint analysis: {e}")
                    import traceback
                    traceback.print_exc()
                    # Fallback to basic complaint detection using keywords
                    try:
                        basic_complaints = self._basic_complaint_analysis(reviews)
                        analysis_results['top_complaints'] = basic_complaints['top_complaints']
                        analysis_results['complaint_categories'] = basic_complaints['complaint_categories']
                        analysis_results['complaint_reviews'] = []  # Empty for fallback
                        print("✅ Using fallback complaint analysis")
                    except Exception as e2:
                        print(f"Error in fallback complaint analysis: {e2}")
                        # Keep empty lists as default
            
            # Convert numpy types to Python native types for JSON serialization
            conversion_start = time.time()
            analysis_results = self._convert_numpy_types(analysis_results)
            conversion_time = time.time() - conversion_start
            print(f"🔄 Data conversion completed in {conversion_time:.2f} seconds")
            
            # Remove product_info from analysis if it was added (it should be at document level)
            if 'product_info' in analysis_results:
                del analysis_results['product_info']
            
            # Remove timestamp from analysis - it should only be at document level
            if 'timestamp' in analysis_results:
                del analysis_results['timestamp']
            
            total_time = time.time() - total_start_time
            print(f"🎉 Complete analysis finished in {total_time:.2f} seconds total!")
            
            return analysis_results
            
        except Exception as e:
            print(f"Error in sentiment analysis: {e}")
            return self._empty_analysis(product_info)
    
    def _calculate_statistics(self, original_reviews, ratings, cleaned_reviews, product_info=None):
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
        complaint_analysis = self._generate_complaint_explanations(complaints)
        
        # Sentiment breakdown
        sentiment_breakdown = {
            'positive': len(positive_reviews),
            'neutral': len(neutral_reviews),
            'negative': len(complaints),
            'positive_percentage': (len(positive_reviews) / total_reviews) * 100 if total_reviews > 0 else 0,
            'neutral_percentage': (len(neutral_reviews) / total_reviews) * 100 if total_reviews > 0 else 0,
            'negative_percentage': (len(complaints) / total_reviews) * 100 if total_reviews > 0 else 0
        }
        
        # Common themes
        positive_themes = self._extract_themes(positive_reviews, positive=True)
        negative_themes = self._extract_themes(complaints, positive=False)
        
        # Create clean analysis structure
        analysis_result = {
            'average_rating': round(average_rating, 2),
            'total_reviews': total_reviews,
            'total_complaints': len(complaints),
            'complaint_percentage': round((len(complaints) / total_reviews) * 100, 1) if total_reviews > 0 else 0,
            'ml_rating_distribution': {
                str(i): int(rating_counts.get(i, 0)) for i in range(1, 6)
            },
            'sentiment_breakdown': {
                'positive': round((len(positive_reviews) / total_reviews) * 100, 1) if total_reviews > 0 else 0,
                'negative': round((len(complaints) / total_reviews) * 100, 1) if total_reviews > 0 else 0
            },
            'top_complaints': [],
            'complaint_categories': {},
            'complaint_reviews': [],  # Initialize empty - will be populated by zero-shot analysis
            'positive_themes': [theme['theme'] for theme in positive_themes[:4]] if positive_themes else [],
            'analysis_method': 'ML+Complaint Analysis' if COMPLAINT_ANALYSIS_AVAILABLE else ('ML-based' if (USE_ML and self.ml_available) else 'Keyword-based')
        }
        
        return self._convert_numpy_types(analysis_result)
    
    def _generate_complaint_explanations(self, complaints):
        """Generate explanations for the most common complaints with quality categorization"""
        if not complaints:
            return {
                'explanations': [],
                'quality_scores': {}
            }
        
        # Categorize complaints by quality type
        quality_complaints = {category: [] for category in self.quality_categories.keys()}
        uncategorized_complaints = []
        
        for complaint in complaints:
            text = complaint.get('cleaned_text', '').lower()
            categorized = False
            
            # Check each quality category
            for category, keywords in self.quality_categories.items():
                if any(keyword in text for keyword in keywords):
                    quality_complaints[category].append(complaint)
                    categorized = True
                    break  # Assign to first matching category only
            
            if not categorized:
                uncategorized_complaints.append(complaint)
        
        # Generate quality-based explanations
        explanations = []
        for category, category_complaints in quality_complaints.items():
            if category_complaints:
                explanation = {
                    'quality_category': category,
                    'frequency': len(category_complaints),
                    'percentage': round((len(category_complaints) / len(complaints)) * 100, 1),
                    'examples': [c['text'][:100] + "..." if len(c['text']) > 100 else c['text'] 
                               for c in category_complaints[:2]]  # Show 2 examples
                }
                explanations.append(explanation)
        
        # Add uncategorized complaints if any
        if uncategorized_complaints:
            explanation = {
                'quality_category': 'general_issues',
                'frequency': len(uncategorized_complaints),
                'percentage': round((len(uncategorized_complaints) / len(complaints)) * 100, 1),
                'examples': [c['text'][:100] + "..." if len(c['text']) > 100 else c['text'] 
                           for c in uncategorized_complaints[:2]]
            }
            explanations.append(explanation)
        
        # Sort by frequency
        explanations.sort(key=lambda x: x['frequency'], reverse=True)
        
        # Create quality scores summary
        quality_scores = {}
        total_complaints = len(complaints)
        
        for category in self.quality_categories.keys():
            complaint_count = len(quality_complaints[category])
            if complaint_count > 0:
                quality_scores[category] = {
                    'complaint_count': complaint_count,
                    'percentage': round((complaint_count / total_complaints) * 100, 1)
                }
        
        return {
            'explanations': explanations[:7],  # Return top 7 categories
            'quality_scores': quality_scores
        }
    
    def _extract_themes(self, reviews, positive=True):
        """Extract common themes from positive or negative reviews"""
        if not reviews:
            return []
        
        # Positive keywords for themes
        positive_keywords = [
            'quality', 'fast', 'good', 'great', 'excellent', 'amazing', 'perfect',
            'recommend', 'love', 'satisfied', 'happy', 'comfortable', 'durable',
            'value', 'price', 'shipping', 'delivery', 'packaging'
        ]
        
        # Negative keywords for themes
        negative_keywords = [
            'quality', 'slow', 'expensive', 'cheap', 'poor', 'terrible', 'awful',
            'disappointed', 'broken', 'defective', 'shipping', 'delivery', 'size',
            'color', 'material', 'service', 'support'
        ]
        
        keywords = positive_keywords if positive else negative_keywords
        theme_counts = {}
        
        for review in reviews:
            text = review['cleaned_text'].lower()
            for keyword in keywords:
                if keyword in text:
                    theme_counts[keyword] = theme_counts.get(keyword, 0) + 1
        
        # Convert to themes with percentages
        themes = []
        total_reviews = len(reviews)
        for keyword, count in sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            themes.append({
                'theme': keyword.capitalize(),
                'mentions': count,
                'percentage': round((count / total_reviews) * 100, 1)
            })
        
        return themes
    
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
                'explanations': [],
                'common_issues': []
            },
            'positive_feedback': {
                'count': 0,
                'details': [],
                'common_themes': []
            },
            'detailed_analysis': {
                'ratings': [],
                'predicted_ratings': [],
                'total_analyzed': 0
            },
            'ml_based': USE_ML and self.ml_available,
            'analysis_method': 'ML-based' if (USE_ML and self.ml_available) else 'Keyword-based',
            'analysis_timestamp': datetime.now().isoformat(),
            'analysis_id': str(uuid.uuid4())
        }
        
        if product_info:
            analysis['product_info'] = product_info
            
        return analysis
    
    def save_analysis_to_db(self, analysis_data, collection, product_id, retailer):
        """Save analysis results to database"""
        try:
            document_key = f"{retailer}_{product_id}_analysis"
            analysis_data['document_key'] = document_key
            analysis_data['product_id'] = product_id
            analysis_data['retailer'] = retailer
            analysis_data['saved_timestamp'] = datetime.now().isoformat()
            
            collection.upsert(document_key, analysis_data)
            print(f"Analysis saved to database with key: {document_key}")
            return document_key
        except Exception as e:
            print(f"Error saving analysis to database: {e}")
            return None
    
    def get_analysis_from_db(self, collection, product_id, retailer):
        """Retrieve analysis results from database"""
        try:
            document_key = f"{retailer}_{product_id}_analysis"
            result = collection.get(document_key)
            return result.value
        except Exception as e:
            print(f"Error retrieving analysis from database: {e}")
            return None

    def _basic_complaint_analysis(self, reviews):
        """Basic complaint analysis using keyword detection as fallback"""
        complaint_keywords = {
            'sound_quality': ['sound', 'audio', 'muffled', 'distorted', 'static', 'noise', 'tinny', 'bass', 'treble'],
            'battery_life': ['battery', 'charge', 'charging', 'power', 'dies', 'drain', 'short'],
            'material_quality': ['cheap', 'flimsy', 'broke', 'broken', 'crack', 'plastic', 'build', 'quality'],
            'comfort_fit': ['comfort', 'uncomfortable', 'tight', 'loose', 'fit', 'ear', 'head', 'pressure'],
            'connectivity': ['connect', 'bluetooth', 'pair', 'pairing', 'wireless', 'signal', 'drop'],
            'shipping_delivery': ['shipping', 'delivery', 'package', 'box', 'arrived', 'delayed'],
            'price_value': ['price', 'expensive', 'cheap', 'value', 'money', 'cost', 'worth'],
            'customer_service': ['service', 'support', 'help', 'response', 'staff', 'representative']
        }
        
        complaint_counts = {category: 0 for category in complaint_keywords.keys()}
        
        # Count complaints by looking for negative sentiment + category keywords
        for review in reviews:
            if isinstance(review, str):
                review_lower = review.lower()
                # Check if review has negative sentiment indicators
                negative_indicators = ['bad', 'terrible', 'awful', 'worst', 'hate', 'disappointed', 'poor', 'horrible']
                has_negative = any(word in review_lower for word in negative_indicators)
                
                if has_negative:
                    for category, keywords in complaint_keywords.items():
                        if any(keyword in review_lower for keyword in keywords):
                            complaint_counts[category] += 1
        
        # Get top complaints
        sorted_complaints = sorted(
            [(cat, count) for cat, count in complaint_counts.items() if count > 0],
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            'top_complaints': sorted_complaints[:3],
            'complaint_categories': complaint_counts
        }

    def _get_top_complaints_from_counts(self, complaint_counts, top_n=3):
        """Get top complaints from already computed complaint counts (avoids duplicate processing)"""
        # Sort complaints by count and get top N
        sorted_complaints = sorted(
            [(cat, count) for cat, count in complaint_counts.items() if count > 0],
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_complaints[:top_n]

    def _convert_numpy_types(self, obj):
        """Convert numpy types to Python native types for JSON serialization"""
        if isinstance(obj, dict):
            return {key: self._convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj 