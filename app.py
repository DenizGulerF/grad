from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_cors import CORS
from scrappers.scrapper import scrape_comments
from scrappers.trendyolScrapper import scrape_trendyol_comments
from scrappers.aliexpressScrapper import scrape_aliexpress_comments
from couchbaseConfig import get_connection  # Direct import from the root directory
from couchbase.exceptions import DocumentNotFoundException  # From the SDK package
from sentiment_service import SentimentService  # Import our new sentiment service
# Import complaint analysis modules
# Complaint analysis imports removed - handled through sentiment_service
import numpy as np
import re
import requests
import time
import json
import uuid
import os
from router.scrapper_router import scrapper_bp


app = Flask(__name__)
CORS(app)
app.config.update(
    SERVER_NAME="localhost:8080"
)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key')

# Connect to Couchbase and store in app config
try:
    cluster, bucket, collection = get_connection()
    app.config['COUCHBASE_CLUSTER'] = cluster
    app.config['COUCHBASE_COLLECTION'] = collection
    
    # Create Products collection if it doesn't exist
    try:
        products_collection = bucket.collection("Products")
    except:
        bucket.create_collection("Products")
        products_collection = bucket.collection("Products")
    
    app.config['COUCHBASE_PRODUCTS_COLLECTION'] = products_collection
    print("Couchbase connection established")
except Exception as e:
    print(f"Failed to connect to Couchbase: {e}")
    app.config['COUCHBASE_CLUSTER'] = None
    app.config['COUCHBASE_COLLECTION'] = None
    app.config['COUCHBASE_PRODUCTS_COLLECTION'] = None

# Register blueprint with prefix - make sure this is in your app
app.register_blueprint(scrapper_bp, url_prefix='/api')

# Simple in-memory cache
cache = {}
CACHE_EXPIRY = 60  # 60 seconds cache

# Initialize sentiment service
sentiment_service = SentimentService()

def get_target_product_details(product_id):
    """
    Get product details from Target's RedSky API
    
    Args:
        product_id (str): Target product ID (TCIN)
    
    Returns:
        dict: Product details including name, image, and rating
    """
    api_url = f"https://redsky.target.com/redsky_aggregations/v1/web/pdp_client_v1"
    params = {
        "key": "9f36aeafbe60771e321a7cc95a78140772ab3e96",
        "tcin": product_id,
        "is_bot": "false",
        "store_id": "1771",
        "pricing_store_id": "1771",
        "has_pricing_store_id": "true",
        "has_financing_options": "true",
        "visitor_id": "01959AAA2AA90201B0A503971AE40FCF",
        "include_obsolete": "true",
        "skip_personalized": "true",
        "skip_variation_hierarchy": "true",
        "channel": "WEB",
        "page": f"/p/A-{product_id}"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": f"https://www.target.com/p/A-{product_id}"
    }
    
    try:
        response = requests.get(api_url, params=params, headers=headers)
        
        if (response.status_code == 200):
            data = response.json()
            
            # Default product info in case we can't extract it
            product_info = {
                "name": f"Target Product {product_id}",
                "image": f"https://target.scene7.com/is/image/Target/GUEST_{product_id}",
                "rating": 0,
                "review_count": 0
            }
            
            # Extract product name
            try:
                product_info["name"] = data["data"]["product"]["item"]["product_description"]["title"]
            except:
                print("Could not extract product name")
            
            # Extract product image
            try:
                # Try different paths where the image might be located in the API response
                if "data" in data and "product" in data["data"]:
                    product_data = data["data"]["product"]
                    
                    # Try path 1: item > enrichment > images
                    if "item" in product_data and "enrichment" in product_data["item"]:
                        item_enrichment = product_data["item"]["enrichment"]
                        if "images" in item_enrichment and "primary_image_url" in item_enrichment["images"]:
                            product_info["image"] = item_enrichment["images"]["primary_image_url"]
                            print(f"Found image in path 1: {product_info['image']}")
                    
                    # Try path 2: esp > enrichment > images
                    elif "esp" in product_data and "enrichment" in product_data["esp"]:
                        esp_enrichment = product_data["esp"]["enrichment"]
                        if "images" in esp_enrichment:
                            if "primary_image_url" in esp_enrichment["images"]:
                                product_info["image"] = esp_enrichment["images"]["primary_image_url"]
                                print(f"Found image in path 2: {product_info['image']}")
                    
                    # Try path 3: looking for the image in various locations with debug info
                    else:
                        print("Searching for image in other paths...")
                        # Dump the structure of the product data for debugging
                        import json
                        with open(f"target_api_response_{product_id}.json", "w") as f:
                            json.dump(data, f, indent=2)
                        print(f"Saved full API response to target_api_response_{product_id}.json")
                        
                        # Try to find image anywhere in the response
                        def find_image_url(obj, path=""):
                            if isinstance(obj, dict):
                                for key, value in obj.items():
                                    if key == "primary_image_url" and isinstance(value, str) and value.startswith("http"):
                                        print(f"Found image at path: {path}.{key}")
                                        return value
                                    elif isinstance(value, (dict, list)):
                                        result = find_image_url(value, f"{path}.{key}" if path else key)
                                        if result:
                                            return result
                            elif isinstance(obj, list):
                                for i, item in enumerate(obj):
                                    if isinstance(item, (dict, list)):
                                        result = find_image_url(item, f"{path}[{i}]")
                                        if result:
                                            return result
                            return None
                        
                        image_url = find_image_url(product_data)
                        if image_url:
                            product_info["image"] = image_url
                            print(f"Found image using deep search: {image_url}")
            except Exception as e:
                print(f"Error extracting product image: {e}")
                print("Using default image URL")
            
            # Extract rating info
            try:
                rating_review_info = data["data"]["product"]["ratings_and_reviews"]
                if "statistics" in rating_review_info:
                    product_info["rating"] = rating_review_info["statistics"]["rating"]["average"]
                    product_info["review_count"] = rating_review_info["statistics"]["rating"]["count"]
            except:
                print("Could not extract rating information")
            
            print(f"Successfully extracted product details for Target product {product_id}")
            return product_info
            
        else:
            print(f"Error accessing Target API: {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"Error fetching Target product details: {str(e)}")
        return None

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/get_reviews', methods=['POST'])
def get_reviews():
    product_url = request.form.get('product_url', '')
    retailer = request.form.get('retailer', 'target')
    
    # Extract product ID from URL
    product_id = None
    
    if retailer == 'target':
        # Extract Target product ID
        # Example Target URL: https://www.target.com/p/product-name/-/A-12345678
        match = re.search(r'/A-(\d+)', product_url)
        if match:
            product_id = match.group(1)
        # Try alternative format
        if not product_id:
            match = re.search(r'p/([^/]+)/([^/]+)/?', product_url)
            if match:
                product_id = match.group(2)
    
    elif retailer == 'trendyol':
        # Extract Trendyol product ID
        # Example Trendyol URL: https://www.trendyol.com/en/brand/product-p-123456/reviews
        match = re.search(r'p-(\d+)', product_url)
        if match:
            product_id = match.group(1)
    
    elif retailer == 'aliexpress':
        # Extract AliExpress product ID
        # Multiple patterns to match different URL formats
        patterns = [
            r'/(\d+)\.html',  # Standard URL format
            r'_(\d+)\.html',  # Alternative format
            r'item/(\d+)',    # Another format
            r'product/(\d+)', # Another format
            r'productId=(\d+)' # API URL format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, product_url)
            if match:
                product_id = match.group(1)
                break
    
    if not product_id:
        return render_template('index.html', 
                               error="Could not extract product ID from the URL. Please try again.",
                               show_form_only=True,
                               title="Product Review Finder")
    
    try:
        # Get reviews based on retailer
        if retailer == 'target':
            # Get product details from Target API
            product_info = get_target_product_details(product_id)
            
            if not product_info:
                # Use default product info if API call fails
                product_info = {
                    "name": f"Target Product {product_id}",
                    "image": f"https://target.scene7.com/is/image/Target/GUEST_{product_id}",
                    "rating": 0,
                    "review_count": 0
                }
            
            # Get reviews
            comments = scrape_comments(product_id=product_id)
            
            # Ensure comments is a Python list
            if isinstance(comments, np.ndarray):
                comments = comments.tolist()
            elif comments is None:
                comments = []
                
            print(f"Scraped {len(comments)} Target reviews for product {product_id}")
            
            # Update review count in product info if we have it
            if not product_info["review_count"] and comments:
                product_info["review_count"] = len(comments)
                
        elif retailer == 'trendyol':
            # Set up for Trendyol
            result = scrape_trendyol_comments(product_id=product_id, max_pages=3)
            
            # Convert NumPy array to Python list
            comments = result["comments"].tolist() if isinstance(result["comments"], np.ndarray) else result["comments"]
            if comments is None:
                comments = []
                
            print(f"Fetched {len(comments)} Trendyol reviews for product {product_id}")
            
            # Use the extracted product info
            product_info = {
                "name": result["product_name"],
                "image": result["product_image"] or "https://via.placeholder.com/150",
                "rating": result["rating"],
                "review_count": result["review_count"]
            }
            
        elif retailer == 'aliexpress':
            # Set up for AliExpress
            result = scrape_aliexpress_comments(product_id=product_id, max_pages=3)
            
            # Convert NumPy array to Python list
            comments = result["comments"].tolist() if isinstance(result["comments"], np.ndarray) else result["comments"]
            if comments is None:
                comments = []
                
            print(f"Fetched {len(comments)} AliExpress reviews for product {product_id}")
            
            # Use the extracted product info
            product_info = {
                "name": result["product_name"],
                "image": result["product_image"] or "https://via.placeholder.com/150",
                "rating": result["rating"],
                "review_count": result["review_count"]
            }

        # Perform sentiment analysis on the reviews
        print(f"Performing sentiment analysis on {len(comments)} reviews...")
        sentiment_analysis = sentiment_service.analyze_reviews(comments, product_info)
        
        # Analysis is saved as part of the product document below
        
        # Save product with clean structure
        if app.config.get('COUCHBASE_PRODUCTS_COLLECTION'):
            try:
                product_document = {
                    'document_key': f"{retailer}_{product_id}_product",
                    'product_id': product_id,
                    'retailer': retailer,
                    'product_info': product_info,
                    'analysis': sentiment_analysis,
                    'timestamp': int(time.time())
                }
                
                product_key = f"{retailer}_{product_id}_product"
                app.config['COUCHBASE_PRODUCTS_COLLECTION'].upsert(product_key, product_document)
                print(f"Product saved with key: {product_key}")
            except Exception as e:
                print(f"Error saving product: {e}")
    
    except Exception as e:
        return render_template('index.html', 
                               error=f"Error fetching reviews: {str(e)}",
                               show_form_only=True,
                               title="Product Review Finder")
    
    return render_template('index.html', 
                          comments=comments,
                          product_name=product_info["name"],
                          product_image=product_info["image"],
                          product_rating=product_info["rating"],
                          review_count=product_info["review_count"],
                          retailer=retailer,
                          title=f"{retailer.capitalize()} Product Reviews",
                          show_form_only=False,
                          product_link=product_url,
                          sentiment_analysis=sentiment_analysis)  # Pass sentiment analysis to template

@app.route('/api/sentiment-analysis/<retailer>/<product_id>', methods=['GET'])
def get_sentiment_analysis(retailer, product_id):
    """Get sentiment analysis for a specific product"""
    try:
        if not app.config.get('COUCHBASE_PRODUCTS_COLLECTION'):
            return jsonify({'error': 'Database not available'}), 500
        
        # Get product data with new structure
        product_key = f"{retailer}_{product_id}_product"
        try:
            product_result = app.config['COUCHBASE_PRODUCTS_COLLECTION'].get(product_key)
            product_data = product_result.value
            
            # Return just the analysis part
            if 'analysis' in product_data:
                return jsonify(product_data['analysis'])
            else:
                return jsonify({'error': 'Analysis not found'}), 404
                
        except DocumentNotFoundException:
            return jsonify({'error': 'Product not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/product/<retailer>/<product_id>', methods=['GET'])
def get_product_with_analysis(retailer, product_id):
    """Get product information with sentiment analysis"""
    try:
        if not app.config.get('COUCHBASE_PRODUCTS_COLLECTION'):
            return jsonify({'error': 'Database not available'}), 500
        
        # Get product data
        product_key = f"{retailer}_{product_id}_product"
        try:
            product_result = app.config['COUCHBASE_PRODUCTS_COLLECTION'].get(product_key)
            product_data = product_result.value
            return jsonify(product_data)
        except DocumentNotFoundException:
            return jsonify({'error': 'Product not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze-reviews', methods=['POST'])
def analyze_reviews_endpoint():
    """Endpoint to analyze reviews without scraping"""
    try:
        data = request.get_json()
        if not data or 'reviews' not in data:
            return jsonify({'error': 'Reviews data required'}), 400
        
        reviews = data['reviews']
        product_info = data.get('product_info', {})
        
        # Perform sentiment analysis with complaint analysis
        analysis = sentiment_service.analyze_reviews(reviews, product_info)
        
        # Optionally save to database if product_id and retailer are provided
        if data.get('product_id') and data.get('retailer') and app.config.get('COUCHBASE_PRODUCTS_COLLECTION'):
            try:
                # Extract complaint_reviews from analysis if present
                complaint_reviews = analysis.get('complaint_reviews', [])
                
                # Remove complaint_reviews from analysis before saving (it goes at document level)
                analysis_for_db = analysis.copy()
                if 'complaint_reviews' in analysis_for_db:
                    del analysis_for_db['complaint_reviews']
                
                product_document = {
                    'document_key': f"{data['retailer']}_{data['product_id']}_product",
                    'product_id': data['product_id'],
                    'retailer': data['retailer'],
                    'product_info': product_info,
                    'analysis': analysis_for_db,
                    'complaint_reviews': complaint_reviews,
                    'timestamp': int(time.time())
                }
                
                product_key = f"{data['retailer']}_{data['product_id']}_product"
                app.config['COUCHBASE_PRODUCTS_COLLECTION'].upsert(product_key, product_document)
                print(f"Product saved with key: {product_key}")
                print(f"Saved {len(complaint_reviews)} complaint reviews to document level")
                
                # Log complaint reviews details
                if complaint_reviews:
                    print(f"📝 Complaint reviews being saved to database:")
                    for i, review in enumerate(complaint_reviews[:5]):  # Show first 5
                        print(f"   {i+1}. [{review.get('complaint_type', 'unknown')}] {review.get('text', 'No text')[:80]}... (confidence: {review.get('confidence', 'N/A')})")
                    if len(complaint_reviews) > 5:
                        print(f"   ... and {len(complaint_reviews) - 5} more complaint reviews")
                else:
                    print(f"   ⚠️ No complaint reviews found in analysis")
            except Exception as e:
                print(f"Error saving product: {e}")
        
        return jsonify(analysis)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/complaint-analysis/<retailer>/<product_id>', methods=['GET'])
def get_complaint_analysis(retailer, product_id):
    """Get detailed complaint analysis for a specific product"""
    try:
        if not app.config.get('COUCHBASE_PRODUCTS_COLLECTION'):
            return jsonify({'error': 'Database not available'}), 500
        
        # Get product data with new structure
        product_key = f"{retailer}_{product_id}_product"
        try:
            product_result = app.config['COUCHBASE_PRODUCTS_COLLECTION'].get(product_key)
            product_data = product_result.value
            
            # Return complaint-specific data from analysis
            if 'analysis' in product_data:
                analysis = product_data['analysis']
                complaint_data = {
                    'product_info': product_data.get('product_info', {}),
                    'total_reviews': analysis.get('total_reviews', 0),
                    'total_complaints': analysis.get('total_complaints', 0),
                    'complaint_percentage': analysis.get('complaint_percentage', 0),
                    'top_complaints': analysis.get('top_complaints', []),
                    'complaint_categories': analysis.get('complaint_categories', {}),
                    'complaint_reviews': product_data.get('complaint_reviews', []),
                    'ml_rating_distribution': analysis.get('ml_rating_distribution', {}),
                    'analysis_method': analysis.get('analysis_method', 'Unknown'),
                    'timestamp': product_data.get('timestamp', 0)
                }
                return jsonify(complaint_data)
            else:
                return jsonify({'error': 'Analysis not found'}), 404
                
        except DocumentNotFoundException:
            return jsonify({'error': 'Product not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/complaints/categories', methods=['GET'])
def get_complaint_categories():
    """Get available complaint categories and their descriptions"""
    try:
        # Import only when needed to avoid loading BART model
        from complaint_modal.complaint_categories_zeroshot import COMPLAINT_LABELS
        
        categories = []
        for category, description in COMPLAINT_LABELS.items():
            categories.append({
                'category': category,
                'description': description,
                'display_name': category.replace('_', ' ').title()
            })
        
        return jsonify({
            'categories': categories,
            'total_categories': len(categories)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/complaints/analyze-text', methods=['POST'])
def analyze_text_complaints():
    """Analyze complaints in provided text using zero-shot classification"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'Text data required'}), 400
        
        text = data['text']
        threshold = data.get('threshold', 0.5)
        
        # Import only when needed to avoid loading BART model during app startup
        from complaint_modal.complaint_categories_zeroshot import extract_complaints_zeroshot
        
        # Perform complaint analysis on the text
        complaints = extract_complaints_zeroshot(text, threshold=threshold)
        
        result = {
            'text': text,
            'threshold': threshold,
            'complaints_found': complaints,
            'total_complaints': len(complaints),
            'analysis_timestamp': time.time()
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/products', methods=['GET'])
def get_all_products():
    """Get all products from the database"""
    try:
        if not app.config.get('COUCHBASE_PRODUCTS_COLLECTION'):
            return jsonify({'error': 'Database not available'}), 500
        
        # Query all products with new structure
        products = []
        try:
            from couchbase.options import QueryOptions
            
            cluster = app.config['COUCHBASE_CLUSTER']
            # Query for documents that have the product structure
            query = """
            SELECT p.*, META(p).id as document_id 
            FROM `Users`.`_default`.`Products` p 
            WHERE p.document_key LIKE '%_product'
            AND p.retailer IS NOT MISSING 
            AND p.product_id IS NOT MISSING
            ORDER BY p.timestamp DESC
            LIMIT 50
            """
            
            query_result = cluster.query(query, QueryOptions(metrics=True))
            
            for row in query_result:
                product_data = row
                # Return product with simplified structure for listing
                products.append({
                    'product_id': product_data.get('product_id', ''),
                    'retailer': product_data.get('retailer', ''),
                    'product_info': product_data.get('product_info', {}),
                    'analysis_summary': {
                        'average_rating': product_data.get('analysis', {}).get('average_rating', 0),
                        'total_reviews': product_data.get('analysis', {}).get('total_reviews', 0),
                        'total_complaints': product_data.get('analysis', {}).get('total_complaints', 0),
                        'complaint_percentage': product_data.get('analysis', {}).get('complaint_percentage', 0),
                        'analysis_method': product_data.get('analysis', {}).get('analysis_method', 'Unknown')
                    },
                    'timestamp': product_data.get('timestamp', 0)
                })
                
            return jsonify({
                'products': products,
                'total_count': len(products)
            })
            
        except Exception as e:
            print(f"Error querying products: {e}")
            return jsonify({'error': 'Failed to retrieve products'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)