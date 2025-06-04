from flask import Blueprint, request, jsonify, current_app
import uuid
from scrappers.scrapper import scrape_comments
from scrappers.aliexpressScrapper import scrape_aliexpress_comments
from scrappers.trendyolScrapper import scrape_trendyol_comments
import jwt
from functools import wraps
import re

scrapper_bp = Blueprint('scrapper', __name__)

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
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['name', 'photo', 'review_count', 'rating']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields. Need: name, photo, review_count, rating'}), 400

    # Generate a unique product ID
    product_id = str(uuid.uuid4())
    
    # Create product document
    product_doc = {
        'name': data['name'],
        'photo': data['photo'],
        'review_count': data['review_count'],
        'rating': data['rating'],
        'product_link': data.get('product_link', 'https://example.com/no-link-provided'),  # Default link if none provided
        'type': 'product',  # Document type for querying
        'rating_distribution': data.get('rating_distribution'),  # Add rating distribution
        'recommended_percentage': data.get('recommended_percentage'),  # Add recommended percentage
        'reviews_with_images_count': data.get('reviews_with_images_count')  # Add reviews with images count
    }

    try:
        # Get collections from app config
        collection = current_app.config.get('COUCHBASE_COLLECTION')
        products_collection = current_app.config.get('COUCHBASE_PRODUCTS_COLLECTION')
        
        if not collection or not products_collection:
            return jsonify({'error': 'Database connection not available'}), 500
        
        # Save product to Products collection
        products_collection.upsert(f"product::{product_id}", product_doc)
        
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
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Check source and product ID/URL
    source = data.get('source', '').lower()
    product_id = data.get('product_id')
    product_url = data.get('product_url')
    
    if not source:
        return jsonify({'error': 'Source is required (target, aliexpress, or trendyol)'}), 400
    
    if not product_id and not product_url:
        return jsonify({'error': 'Either product_id or product_url is required'}), 400
    
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
                print(f"Extracted Target product ID using pattern {pattern}: {product_id}")
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
            print(f"Using Target product ID: {product_id}")
            
            result = scrape_comments(product_id)
            
            # Convert numpy array to list
            comments = result["comments"].tolist() if hasattr(result["comments"], 'tolist') else result["comments"]
            
            # Format the data for saving - preserve original image URL
            product_data = {
                'name': result["product_name"],
                'photo': result["product_image"],  # Keep original URL without modification
                'review_count': result["review_count"],
                'rating': result["rating"],
                'comments': comments,
                'source': 'target',
                'product_link': f"https://www.target.com/p/A-{product_id}",
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
                'name': result["product_name"],
                'photo': result["product_image"],
                'review_count': result["review_count"],
                'rating': result["rating"],
                'comments': comments,
                'source': 'aliexpress',
                'product_link': product_url or f"https://www.aliexpress.com/item/{product_id}.html"
            }
            
        elif source == 'trendyol':
            # Call Trendyol scraper
            result = scrape_trendyol_comments(product_id=product_id, product_url=product_url)
            
            # Convert numpy array to list
            comments = result["comments"].tolist() if hasattr(result["comments"], 'tolist') else result["comments"]
            
            product_data = {
                'name': result["product_name"],
                'photo': result["product_image"],
                'review_count': result["review_count"],
                'rating': result["rating"],
                'comments': comments,
                'source': 'trendyol',
                'product_link': product_url or f"https://www.trendyol.com/brand/name-p-{product_id}"
            }
            
        else:
            return jsonify({'error': f'Unsupported source: {source}'}), 400
        
        # Generate a unique product ID
        product_id = str(uuid.uuid4())
        
        # Get Couchbase connection
        cluster, bucket, _ = get_connection()
        
        # Get the Products collection specifically
        products_collection = bucket.collection("Products")
        
        # Save to Couchbase Products collection
        products_collection.upsert(f"product::{product_id}", product_data)
        
        # Return success with basic product info
        return jsonify({
            'id': product_id,
            'name': product_data['name'],
            'photo': product_data['photo'],  # Return original URL
            'review_count': product_data['review_count'],
            'rating': product_data['rating'],
            'source': product_data['source'],
            'product_link': product_data['product_link'],
            'rating_distribution': product_data.get('rating_distribution'),  # Add rating distribution
            'recommended_percentage': product_data.get('recommended_percentage'),
            'reviews_with_images_count': product_data.get('reviews_with_images_count')
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@scrapper_bp.route('/scrape_only', methods=['POST'])
def scrape_only():
    """Scrape product details without saving to database"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Check source and product ID/URL
    source = data.get('source', '').lower()
    product_id = data.get('product_id')
    product_url = data.get('product_url')
    
    if not source:
        return jsonify({'error': 'Source is required (target, aliexpress, or trendyol)'}), 400
    
    if not product_id and not product_url:
        return jsonify({'error': 'Either product_id or product_url is required'}), 400
    
    # Add this before checking for product_id
    if source == 'target' and not product_id and product_url:
        # Try to extract product ID from the URL
        import re
        match = re.search(r'/A-(\d+)|/p/([^/]+)-/A-(\d+)', product_url)
        if match:
            # Use the first group that matched
            product_id = next(g for g in match.groups() if g is not None)
            print(f"Extracted Target product ID: {product_id}")
        else:
            return jsonify({'error': 'Could not extract product ID from Target URL'}), 400
    
    try:
        # Scrape based on source
        if source == 'target':
            if not product_id:
                return jsonify({'error': 'Product ID is required for Target'}), 400
            result = scrape_comments(product_id)
            
            # Convert numpy array to list
            comments = result["comments"].tolist() if hasattr(result["comments"], 'tolist') else result["comments"]
            
            # Format the response data
            response_data = {
                'name': result["product_name"],
                'photo': result["product_image"],
                'review_count': result["review_count"],
                'rating': result["rating"],
                'comments': comments,
                'source': 'target',
                'product_link': f"https://www.target.com/p/A-{product_id}",
                'rating_distribution': result.get("rating_distribution"),  # Add rating distribution
                'recommended_percentage': result.get("recommended_percentage"),
                'reviews_with_images_count': result.get("reviews_with_images_count")
            }
            
        elif source == 'aliexpress':
            # Call AliExpress scraper
            result = scrape_aliexpress_comments(product_id=product_id, product_url=product_url)
            
            # Convert numpy array to list
            comments = result["comments"].tolist() if hasattr(result["comments"], 'tolist') else result["comments"]
            
            response_data = {
                'name': result["product_name"],
                'photo': result["product_image"],
                'review_count': result["review_count"],
                'rating': result["rating"],
                'comments': comments,
                'source': 'aliexpress',
                'product_link': product_url or f"https://www.aliexpress.com/item/{product_id}.html"
            }
            
        elif source == 'trendyol':
            # Call Trendyol scraper
            result = scrape_trendyol_comments(product_id=product_id, product_url=product_url)
            
            # Convert numpy array to list
            comments = result["comments"].tolist() if hasattr(result["comments"], 'tolist') else result["comments"]
            
            response_data = {
                'name': result["product_name"],
                'photo': result["product_image"],
                'review_count': result["review_count"],
                'rating': result["rating"],
                'comments': comments,
                'source': 'trendyol',
                'product_link': product_url or f"https://www.trendyol.com/brand/name-p-{product_id}"
            }
            
        else:
            return jsonify({'error': f'Unsupported source: {source}'}), 400
        
        # Return data without saving to database
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500