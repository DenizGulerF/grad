from flask import Flask, render_template, jsonify, request, redirect, url_for
from scrappers.scrapper import scrape_comments
from scrappers.trendyolScrapper import scrape_trendyol_comments
from scrappers.aliexpressScrapper import scrape_aliexpress_comments
from couchbaseConfig import get_connection  # Direct import from the root directory
from couchbase.exceptions import DocumentNotFoundException  # From the SDK package
import numpy as np
import re
import requests
import time
import json
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

# Simple in-memory cache
cache = {}
CACHE_EXPIRY = 60  # 60 seconds cache

# Connect to Couchbase - simplified
try:
    cluster, bucket, collection = get_connection()
    print("Couchbase connection established")
except Exception as e:
    print(f"Failed to connect to Couchbase: {e}")
    cluster = bucket = collection = None

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
                          show_form_only=False)