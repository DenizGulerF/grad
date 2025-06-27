from flask import Blueprint, request, jsonify, current_app
import uuid
from scrappers.scrapper import scrape_comments
from scrappers.aliexpressScrapper import scrape_aliexpress_comments
from scrappers.trendyolScrapper import scrape_trendyol_comments
from couchbaseConfig import get_connection
import jwt
from functools import wraps
import re
from sentiment_service import SentimentService  # Import sentiment analysis
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scrapper_bp = Blueprint('scrapper', __name__)

# Initialize sentiment service only (CSV export disabled)
sentiment_service = SentimentService()
logger.info("📊 CSV export feature disabled - using ML-only analysis")

# Log sentiment service initialization
logger.info(f"🔍 Sentiment service initialized in router - ML available: {sentiment_service.ml_available}")

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Missing or invalid authorization header"}), 401
            
        token = auth_header.split(' ')[1]
        
        try:
            # Decode the token
            payload = jwt.decode(
                token,
                current_app.config['JWT_SECRET_KEY'],
                algorithms=['HS256']
            )
            # Add user info to request
            request.user = {
                'id': payload['sub'],
                'username': payload['username'],
                'roles': payload.get('roles', ['user'])
            }
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
    return decorated

@scrapper_bp.route('/save_product', methods=['POST'])
@token_required
def save_product():
    """Save product details directly from POST request and add to user's saved products"""
    logger.info("📦 Starting save_product endpoint")
    data = request.get_json()
    
    logger.info(f"📦 Received data keys: {list(data.keys()) if data else 'None'}")
    
    # Validate required fields
    required_fields = ['name', 'photo', 'review_count', 'rating']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields. Need: name, photo, review_count, rating'}), 400

    # Generate a unique product ID
    product_id = str(uuid.uuid4())
    logger.info(f"📦 Generated product ID: {product_id}")
    
    # Create product document
    product_doc = {
        'name': data['name'],
        'photo': data['photo'],
        'review_count': data['review_count'],
        'rating': data['rating'],
        'product_link': data.get('product_link', 'https://example.com/no-link-provided'),
        'type': 'product',
        'rating_distribution': data.get('rating_distribution'),
        'recommended_percentage': data.get('recommended_percentage'),
        'reviews_with_images_count': data.get('reviews_with_images_count'),
        # Don't save comments to database - only use for analysis
        'source': data.get('source', 'unknown')  # Add source information
    }
    
    logger.info(f"📦 Product document created (comments excluded from storage)")

    # Check if sentiment analysis data is already provided
    if data.get('sentiment_analysis'):
        logger.info("📊 Using pre-computed sentiment analysis data")
        sentiment_analysis = data['sentiment_analysis']
        product_doc['sentiment_analysis'] = sentiment_analysis
        
        # Log sentiment summary
        logger.info(f"📈 Sentiment Summary - Avg Rating: {sentiment_analysis.get('average_rating', 'N/A')}, Total Complaints: {sentiment_analysis.get('total_complaints', 'N/A')}, Method: {sentiment_analysis.get('analysis_method', 'N/A')}")
        
        # Log complaint reviews if available
        complaint_reviews = sentiment_analysis.get('complaint_reviews', [])
        logger.info(f"📝 Found {len(complaint_reviews)} complaint reviews in sentiment analysis:")
        for i, review in enumerate(complaint_reviews[:5]):  # Show first 5
            logger.info(f"   {i+1}. [{review.get('complaint_type', 'unknown')}] {review.get('text', 'No text')[:80]}... (confidence: {review.get('confidence', 'N/A')})")
        if len(complaint_reviews) > 5:
            logger.info(f"   ... and {len(complaint_reviews) - 5} more complaint reviews")
        
    # If no pre-computed sentiment analysis but comments are available, analyze them
    elif data.get('comments') and len(data.get('comments', [])) > 0:
        logger.info(f"🔍 Starting sentiment analysis for {len(data['comments'])} comments")
        try:
            product_info = {
                'name': data['name'],
                'rating': data['rating'],
                'review_count': data['review_count']
            }
            
            sentiment_analysis = sentiment_service.analyze_reviews(data['comments'], product_info)
            logger.info(f"✅ Sentiment analysis completed - Score: {sentiment_analysis.get('recommendation_score', 'N/A')}")
            
            # Log complaint reviews from fresh analysis
            complaint_reviews = sentiment_analysis.get('complaint_reviews', [])
            logger.info(f"📝 Generated {len(complaint_reviews)} complaint reviews from analysis:")
            for i, review in enumerate(complaint_reviews[:5]):  # Show first 5
                logger.info(f"   {i+1}. [{review.get('complaint_type', 'unknown')}] {review.get('text', 'No text')[:80]}... (confidence: {review.get('confidence', 'N/A')})")
            if len(complaint_reviews) > 5:
                logger.info(f"   ... and {len(complaint_reviews) - 5} more complaint reviews")
            
            # Add sentiment analysis to product document (but not the comments themselves)
            product_doc['sentiment_analysis'] = sentiment_analysis
            
        except Exception as e:
            logger.error(f"❌ Sentiment analysis failed: {str(e)}")
            product_doc['sentiment_analysis'] = {"error": "Analysis failed", "details": str(e)}
            
    else:
        logger.info("⚠️ No sentiment analysis data or comments available")
        logger.info(f"📋 Available data: has_sentiment_analysis={bool(data.get('sentiment_analysis'))}, has_comments={bool(data.get('comments'))}, comments_count={len(data.get('comments', []))}")

    try:
        # Get collections from app config
        collection = current_app.config.get('COUCHBASE_COLLECTION')
        products_collection = current_app.config.get('COUCHBASE_PRODUCTS_COLLECTION')
        
        if not collection or not products_collection:
            return jsonify({'error': 'Database connection not available'}), 500
        
        # Extract complaint_reviews from sentiment_analysis if present and move to document level
        if 'sentiment_analysis' in product_doc:
            sentiment_analysis = product_doc['sentiment_analysis']
            complaint_reviews = sentiment_analysis.get('complaint_reviews', [])
            
            # If complaint_reviews is empty but we have comments, try to extract them now
            if not complaint_reviews and data.get('comments') and len(data.get('comments', [])) > 0:
                logger.info(f"📝 No complaint reviews in sentiment analysis, attempting to extract from {len(data['comments'])} comments...")
                try:
                    # Import the complaint extraction function
                    from complaint_modal.inference import count_complaints_by_category
                    
                    # Extract complaint reviews using BART model
                    threshold = 0.3  # Lower threshold for better recall
                    batch_size = 16
                    complaint_counts, extracted_reviews = count_complaints_by_category(
                        data['comments'], threshold=threshold, batch_size=batch_size, extract_reviews=True
                    )
                    
                    complaint_reviews = extracted_reviews[:10]  # Limit to top 10
                    logger.info(f"✅ Successfully extracted {len(complaint_reviews)} complaint reviews using BART model")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to extract complaint reviews: {str(e)}")
                    complaint_reviews = []
            
            # Remove complaint_reviews from sentiment_analysis (they go at document level)
            if 'complaint_reviews' in sentiment_analysis:
                del sentiment_analysis['complaint_reviews']
            
            # Add complaint_reviews at document level
            product_doc['complaint_reviews'] = complaint_reviews
            
            logger.info(f"📝 Moved {len(complaint_reviews)} complaint reviews to document level")
            
            # Log complaint reviews details
            if complaint_reviews:
                logger.info(f"📝 Complaint reviews details:")
                for i, review in enumerate(complaint_reviews[:5]):  # Show first 5
                    logger.info(f"   {i+1}. [{review.get('complaint_type', 'unknown')}] {review.get('text', 'No text')[:80]}... (confidence: {review.get('confidence', 'N/A')})")
                if len(complaint_reviews) > 5:
                    logger.info(f"   ... and {len(complaint_reviews) - 5} more complaint reviews")
            else:
                logger.info(f"   ⚠️ No complaint reviews found or extracted")
        else:
            # If no sentiment analysis, ensure complaint_reviews exists as empty array
            product_doc['complaint_reviews'] = []
            logger.info(f"📝 No sentiment analysis provided, complaint_reviews set to empty array")

        # Save product to Products collection
        products_collection.upsert(f"product::{product_id}", product_doc)
        
        # Log what was saved
        has_sentiment = 'sentiment_analysis' in product_doc
        complaint_count = len(product_doc.get('complaint_reviews', []))
        logger.info(f"💾 Product saved to database with ID: {product_id} (includes_sentiment: {has_sentiment}, complaint_reviews: {complaint_count})")
        
        # Get current user's document
        try:
            user_doc = collection.get(f"user::{request.user['id']}").content_as[dict]
        except:
            return jsonify({'error': 'User not found'}), 404
        
        # Add product ID to user's saved_products list if not already there
        if 'saved_products' not in user_doc:
            user_doc['saved_products'] = []
        
        if product_id not in user_doc['saved_products']:
            user_doc['saved_products'].append(product_id)
            
        # Update user document
        collection.upsert(f"user::{request.user['id']}", user_doc)
        
        return jsonify({
            'id': product_id, 
            **product_doc,
            'saved': True
        }), 201
        
    except Exception as e:
        logger.error(f"❌ Error saving product: {str(e)}")
        return jsonify({'error': str(e)}), 500

@scrapper_bp.route('/user/saved_products', methods=['GET'])
@token_required
def get_saved_products():
    """Get all saved products for the current user"""
    try:
        # Get collections from app config
        collection = current_app.config.get('COUCHBASE_COLLECTION')
        products_collection = current_app.config.get('COUCHBASE_PRODUCTS_COLLECTION')
        
        if not collection or not products_collection:
            return jsonify({'error': 'Database connection not available'}), 500
        
        # Get user document
        try:
            user_doc = collection.get(f"user::{request.user['id']}").content_as[dict]
        except:
            return jsonify({'products': []}), 200
            
        # Get saved product IDs
        saved_products = user_doc.get('saved_products', [])
        
        # Get product details for each saved product ID
        products = []
        for product_id in saved_products:
            try:
                product = products_collection.get(f"product::{product_id}").content_as[dict]
                products.append({
                    'id': product_id,
                    **product
                })
            except:
                # If product no longer exists, skip it
                continue
                
        return jsonify({'products': products}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@scrapper_bp.route('/user/saved_products/<product_id>', methods=['DELETE'])
@token_required
def remove_saved_product(product_id):
    """Remove a product from user's saved products list"""
    try:
        # Get collections from app config
        collection = current_app.config.get('COUCHBASE_COLLECTION')
        if not collection:
            return jsonify({'error': 'Database connection not available'}), 500
        
        # Get user document
        try:
            user_doc = collection.get(f"user::{request.user['id']}").content_as[dict]
        except:
            return jsonify({'error': 'User not found'}), 404
            
        # Remove product ID from saved_products list
        if 'saved_products' in user_doc and product_id in user_doc['saved_products']:
            user_doc['saved_products'].remove(product_id)
            collection.upsert(f"user::{request.user['id']}", user_doc)
            return jsonify({'message': 'Product removed from saved products'}), 200
        else:
            return jsonify({'error': 'Product not found in saved products'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@scrapper_bp.route('/scrape', methods=['POST'])
def scrape_and_save():
    """Scrape product details and save to Couchbase"""
    logger.info("🕷️ Starting scrape_and_save endpoint")
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Check source and product ID/URL
    source = data.get('source', '').lower()
    product_id = data.get('product_id')
    product_url = data.get('product_url')
    export_csv = data.get('export_csv', True)  # Default to True for CSV export
    
    logger.info(f"🕷️ Scraping {source} - Product ID: {product_id}")
    
    if not source:
        return jsonify({'error': 'Source is required (target, aliexpress, or trendyol)'}), 400
    
    if not product_id and not product_url:
        return jsonify({'error': 'Either product_id or product_url is required'}), 400
    
    # Store original product_id for CSV export
    original_product_id = product_id
    
    # Add this before checking for product_id
    if source == 'target' and not product_id and product_url:
        # Try to extract product ID from the URL using multiple patterns
        target_patterns = [
            r'/A-(\d+)',  # Standard format: /A-12345678
            r'/-/A-(\d+)',  # SEO format: /product-name/-/A-12345678
            r'/p/(\d+)',  # Alternative format: /p/12345678
            r'tcin=(\d+)',  # Query parameter format: ?tcin=12345678
            r'targetcom/p/([^/]+)-(\d+)',  # Another SEO format
            r'target\.com/p/([^/]+)/A-(\d+)'  # Yet another format
        ]
        
        product_id = None
        for pattern in target_patterns:
            match = re.search(pattern, product_url)
            if match:
                # Some patterns have multiple groups, get the last group which is usually the ID
                product_id = match.group(match.lastindex)
                original_product_id = product_id
                logger.info(f"🎯 Extracted Target product ID: {product_id}")
                break
        
        if not product_id:
            return jsonify({'error': 'Could not extract product ID from Target URL. Please provide the product ID directly.'}), 400
    
    try:
        # Scrape based on source
        if source == 'target':
            if not product_id:
                return jsonify({'error': 'Product ID is required for Target'}), 400
                
            # Clean up the product ID - remove any non-numeric characters
            product_id = re.sub(r'\D', '', product_id)
            logger.info(f"🎯 Using cleaned Target product ID: {product_id}")
            
            result = scrape_comments(product_id)
            
            # Convert numpy array to list
            comments = result["comments"].tolist() if hasattr(result["comments"], 'tolist') else result["comments"]
            
            # Format the data for saving - preserve original image URL
            product_data = {
                'product_name': result["product_name"],
                'product_image': result["product_image"],  # Keep original URL without modification
                'review_count': result["review_count"],
                'rating': result["rating"],
                'comments': comments,
                'source': 'target',
                'product_link': generate_target_url(product_id, result["product_name"]),
                'rating_distribution': result.get("rating_distribution"),
                'recommended_percentage': result.get("recommended_percentage"),
                'reviews_with_images_count': result.get("reviews_with_images_count"),
                'type': 'product'  # Add document type
            }
            
        elif source == 'aliexpress':
            # Call AliExpress scraper
            result = scrape_aliexpress_comments(product_id=product_id, product_url=product_url)
            
            # Convert numpy array to list
            comments = result["comments"].tolist() if hasattr(result["comments"], 'tolist') else result["comments"]
            
            product_data = {
                'product_name': result["product_name"],
                'product_image': result["product_image"],
                'review_count': result["review_count"],
                'rating': result["rating"],
                'comments': comments,
                'source': 'aliexpress',
                'product_link': product_url or f"https://www.aliexpress.com/item/{product_id}.html",
                'rating_distribution': result.get("rating_distribution"),  # Add rating distribution
                'type': 'product'  # Add document type
            }
            
        elif source == 'trendyol':
            # Call Trendyol scraper
            result = scrape_trendyol_comments(product_id=product_id, product_url=product_url)
            
            # Convert numpy array to list
            comments = result["comments"].tolist() if hasattr(result["comments"], 'tolist') else result["comments"]
            
            product_data = {
                'product_name': result["product_name"],
                'product_image': result["product_image"],
                'review_count': result["review_count"],
                'rating': result["rating"],
                'comments': comments,
                'source': 'trendyol',
                'product_link': product_url or f"https://www.trendyol.com/brand/name-p-{product_id}"
            }
            
        else:
            return jsonify({'error': f'Unsupported source: {source}'}), 400
        
        logger.info(f"✅ Scraping completed - {len(product_data.get('comments', []))} comments found")
        
        # Perform sentiment analysis
        if product_data.get('comments') and len(product_data['comments']) > 0:
            logger.info(f"🔍 Starting sentiment analysis for {len(product_data['comments'])} comments")
            try:
                product_info = {
                    'name': product_data['product_name'],
                    'rating': product_data['rating'],
                    'review_count': product_data['review_count']
                }
                
                sentiment_analysis = sentiment_service.analyze_reviews(product_data['comments'], product_info)
                product_data['sentiment_analysis'] = sentiment_analysis
                
                logger.info(f"✅ Sentiment analysis completed - Score: {sentiment_analysis.get('recommendation_score', 'N/A')}")
                logger.info(f"📊 Analysis summary: Avg rating: {sentiment_analysis.get('summary', {}).get('average_rating', 'N/A')}, Complaints: {sentiment_analysis.get('summary', {}).get('complaint_count', 'N/A')}")
                
            except Exception as e:
                logger.error(f"❌ Sentiment analysis failed: {str(e)}")
                product_data['sentiment_analysis'] = {"error": "Analysis failed", "details": str(e)}
        else:
            logger.info("⚠️ No comments available for sentiment analysis")
        
        # CSV export disabled - ML models don't use CSV files
        csv_files = {}
        if export_csv:
            logger.info("📊 CSV export requested but disabled (ML models analyze data directly)")
            csv_files['disabled'] = "CSV export disabled - ML analysis happens in real-time"
        
        # Generate a unique product ID for database
        db_product_id = str(uuid.uuid4())
        
        # Get Couchbase connection
        cluster, bucket, _ = get_connection()
        
        # Get the Products collection specifically
        products_collection = bucket.collection("Products")
        
        # Extract sentiment analysis and prepare for new clean structure
        sentiment_analysis = product_data.get('sentiment_analysis', {})
        complaint_reviews = sentiment_analysis.get('complaint_reviews', [])
        
        # Remove complaint_reviews from analysis before saving (it goes at document level)
        analysis_for_db = sentiment_analysis.copy() if sentiment_analysis else {}
        if 'complaint_reviews' in analysis_for_db:
            del analysis_for_db['complaint_reviews']
        
        # Create product document in new clean structure
        db_product_data = {
            'document_key': f"scraped_{db_product_id}_product",
            'product_id': db_product_id,
            'retailer': product_data['source'],
            'product_info': {
                'name': product_data['product_name'],
                'rating': product_data['rating'],
                'review_count': product_data['review_count'],
                'original_rating_distribution': product_data.get('rating_distribution', {}),
                'recommended_percentage': product_data.get('recommended_percentage'),
                'reviews_with_images_count': product_data.get('reviews_with_images_count'),
                'product_link': product_data['product_link'],
                'product_image': product_data['product_image']
            },
            'analysis': analysis_for_db,
            'complaint_reviews': complaint_reviews,
            'timestamp': int(time.time()),
            
            # Keep legacy fields for backward compatibility (can be removed later)
            'name': product_data['product_name'],
            'photo': product_data['product_image'],
            'review_count': product_data['review_count'],
            'rating': product_data['rating'],
            'comments': product_data['comments'],
            'source': product_data['source'],
            'product_link': product_data['product_link'],
            'rating_distribution': product_data.get('rating_distribution'),
            'recommended_percentage': product_data.get('recommended_percentage'),
            'reviews_with_images_count': product_data.get('reviews_with_images_count'),
            'sentiment_analysis': analysis_for_db,  # Legacy field
            'type': 'product'
        }
        
        # Save to Couchbase Products collection with new key format
        product_key = f"scraped_{db_product_id}_product"
        products_collection.upsert(product_key, db_product_data)
        logger.info(f"💾 Product saved to database with sentiment analysis: {db_product_id}")
        logger.info(f"📝 Saved {len(complaint_reviews)} complaint reviews to document level")
        
        # Log complaint reviews details
        if complaint_reviews:
            logger.info(f"📝 Complaint reviews saved to database:")
            for i, review in enumerate(complaint_reviews[:5]):  # Show first 5
                logger.info(f"   {i+1}. [{review.get('complaint_type', 'unknown')}] {review.get('text', 'No text')[:80]}... (confidence: {review.get('confidence', 'N/A')})")
            if len(complaint_reviews) > 5:
                logger.info(f"   ... and {len(complaint_reviews) - 5} more complaint reviews")
        else:
            logger.info(f"   ⚠️ No complaint reviews found in sentiment analysis")
        
        # Prepare response
        response_data = {
            'id': db_product_id,
            'name': db_product_data['name'],
            'photo': db_product_data['photo'],
            'review_count': db_product_data['review_count'],
            'rating': db_product_data['rating'],
            'source': db_product_data['source'],
            'product_link': db_product_data['product_link'],
            'rating_distribution': db_product_data.get('rating_distribution'),
            'recommended_percentage': db_product_data.get('recommended_percentage'),
            'reviews_with_images_count': db_product_data.get('reviews_with_images_count'),
            'sentiment_analysis': db_product_data.get('sentiment_analysis')  # Include sentiment analysis
        }
        
        # Add CSV file paths to response if exported
        if csv_files:
            response_data['csv_exports'] = csv_files
        
        return jsonify(response_data), 201
        
    except Exception as e:
        logger.error(f"❌ Error in scrape_and_save: {str(e)}")
        return jsonify({'error': str(e)}), 500

@scrapper_bp.route('/scrape_only', methods=['POST'])
def scrape_only():
    """Scrape product details without saving to database but with optional CSV export"""
    logger.info("🕷️ Starting scrape_only endpoint")
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Check source and product ID/URL
    source = data.get('source', '').lower()
    product_id = data.get('product_id')
    product_url = data.get('product_url')
    export_csv = data.get('export_csv', True)
    
    logger.info(f"🕷️ Scraping {source} - Product ID: {product_id}")
    
    if not source:
        return jsonify({'error': 'Source is required (target, aliexpress, or trendyol)'}), 400
    
    if not product_id and not product_url:
        return jsonify({'error': 'Either product_id or product_url is required'}), 400
    
    # Store original product_id for CSV export
    original_product_id = product_id
    
    # Extract product ID from URL if needed
    if source == 'target' and not product_id and product_url:
        target_patterns = [
            r'/A-(\d+)',
            r'/-/A-(\d+)',
            r'/p/(\d+)',
            r'tcin=(\d+)',
            r'targetcom/p/([^/]+)-(\d+)',
            r'target\.com/p/([^/]+)/A-(\d+)'
        ]
        
        product_id = None
        for pattern in target_patterns:
            match = re.search(pattern, product_url)
            if match:
                product_id = match.group(match.lastindex)
                original_product_id = product_id
                logger.info(f"🎯 Extracted Target product ID: {product_id}")
                break
        
        if not product_id:
            return jsonify({'error': 'Could not extract product ID from Target URL'}), 400

    try:
        # Scrape based on source
        if source == 'target':
            if not product_id:
                return jsonify({'error': 'Product ID is required for Target'}), 400
                
            product_id = re.sub(r'\D', '', product_id)
            logger.info(f"🎯 Using cleaned Target product ID: {product_id}")
            
            result = scrape_comments(product_id)
            comments = result["comments"].tolist() if hasattr(result["comments"], 'tolist') else result["comments"]
            
            response_data = {
                'product_name': result["product_name"],
                'product_image': result["product_image"],
                'review_count': result["review_count"],
                'rating': result["rating"],
                'comments': comments,
                'source': 'target',
                'product_link': generate_target_url(product_id, result["product_name"]),
                'rating_distribution': result.get("rating_distribution"),
                'recommended_percentage': result.get("recommended_percentage"),
                'reviews_with_images_count': result.get("reviews_with_images_count")
            }
            
        elif source == 'aliexpress':
            result = scrape_aliexpress_comments(product_id=product_id, product_url=product_url)
            comments = result["comments"].tolist() if hasattr(result["comments"], 'tolist') else result["comments"]
            
            response_data = {
                'product_name': result["product_name"],
                'product_image': result["product_image"],
                'review_count': result["review_count"],
                'rating': result["rating"],
                'comments': comments,
                'source': 'aliexpress',
                'product_link': product_url or f"https://www.aliexpress.com/item/{product_id}.html",
                'rating_distribution': result.get("rating_distribution")
            }
            
        elif source == 'trendyol':
            result = scrape_trendyol_comments(product_id=product_id, product_url=product_url)
            comments = result["comments"].tolist() if hasattr(result["comments"], 'tolist') else result["comments"]
            
            response_data = {
                'product_name': result["product_name"],
                'product_image': result["product_image"],
                'review_count': result["review_count"],
                'rating': result["rating"],
                'comments': comments,
                'source': 'trendyol',
                'product_link': product_url or f"https://www.trendyol.com/brand/name-p-{product_id}"
            }
            
        else:
            return jsonify({'error': f'Unsupported source: {source}'}), 400
        
        logger.info(f"✅ Scraping completed - {len(response_data.get('comments', []))} comments found")
        
        # Perform sentiment analysis
        if response_data.get('comments') and len(response_data['comments']) > 0:
            logger.info(f"🔍 Starting sentiment analysis for {len(response_data['comments'])} comments")
            try:
                product_info = {
                    'name': response_data['product_name'],
                    'rating': response_data['rating'],
                    'review_count': response_data['review_count']
                }
                
                sentiment_analysis = sentiment_service.analyze_reviews(response_data['comments'], product_info)
                
                # Extract complaint_reviews to top level for frontend access
                complaint_reviews = sentiment_analysis.get('complaint_reviews', [])
                
                # Remove complaint_reviews from sentiment_analysis for clean response
                if 'complaint_reviews' in sentiment_analysis:
                    del sentiment_analysis['complaint_reviews']
                
                response_data['sentiment_analysis'] = sentiment_analysis
                response_data['complaint_reviews'] = complaint_reviews
                
                logger.info(f"✅ Sentiment analysis completed - Method: {sentiment_analysis.get('analysis_method', 'N/A')}")
                logger.info(f"📊 Analysis summary: Avg rating: {sentiment_analysis.get('average_rating', 'N/A')}, Total complaints: {sentiment_analysis.get('total_complaints', 'N/A')}")
                logger.info(f"📝 Extracted {len(complaint_reviews)} complaint reviews for frontend access")
                
                # Log complaint reviews details
                if complaint_reviews:
                    logger.info(f"📝 Complaint reviews available in scrape_only response:")
                    for i, review in enumerate(complaint_reviews[:3]):  # Show first 3
                        logger.info(f"   {i+1}. [{review.get('complaint_type', 'unknown')}] {review.get('text', 'No text')[:80]}... (confidence: {review.get('confidence', 'N/A')})")
                    if len(complaint_reviews) > 3:
                        logger.info(f"   ... and {len(complaint_reviews) - 3} more complaint reviews")
                
            except Exception as e:
                logger.error(f"❌ Sentiment analysis failed: {str(e)}")
                response_data['sentiment_analysis'] = {"error": "Analysis failed", "details": str(e)}
                response_data['complaint_reviews'] = []  # Ensure complaint_reviews exists even on error
        else:
            logger.info("⚠️ No comments available for sentiment analysis")
            response_data['complaint_reviews'] = []  # Ensure complaint_reviews exists when no comments
        
        # CSV export disabled - ML models don't use CSV files
        csv_files = {}
        if export_csv:
            logger.info("📊 CSV export requested but disabled (ML models analyze data directly)")
            csv_files['disabled'] = "CSV export disabled - ML analysis happens in real-time"
        
        if csv_files:
            response_data['csv_exports'] = csv_files
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"❌ Error in scrape_only: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
    
@scrapper_bp.route('/download_csv/<path:filename>', methods=['GET'])
def download_csv(filename):
    """CSV download disabled - ML models analyze data directly"""
    return jsonify({
        'message': 'CSV download feature has been disabled',
        'reason': 'ML models analyze review data in real-time without needing CSV files',
        'suggestion': 'Access sentiment analysis results directly from the database'
    }), 200

def generate_target_url(product_id, product_name):
    """Generate proper Target URL with product name slug"""
    # Create URL slug from product name
    if product_name and product_name != f"Target Product {product_id}":
        # Convert product name to URL-friendly slug
        slug = product_name.lower()
        # Replace special characters and spaces with hyphens
        slug = re.sub(r'[^\w\s-]', '', slug)  # Remove special chars except hyphens and spaces
        slug = re.sub(r'[-\s]+', '-', slug)  # Replace spaces and multiple hyphens with single hyphen
        slug = slug.strip('-')  # Remove leading/trailing hyphens
        
        return f"https://www.target.com/p/{slug}/-/A-{product_id}"
    else:
        # Fallback to simplified URL if no product name available
        return f"https://www.target.com/p/A-{product_id}"