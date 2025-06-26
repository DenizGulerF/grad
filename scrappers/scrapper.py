import requests
import json
import time
import random

def get_target_product_details(product_id):
    """Get product details from Target's RedSky API"""
    api_url = f"https://redsky.target.com/redsky_aggregations/v1/web/pdp_client_v1"
    params = {
        "key": "9f36aeafbe60771e321a7cc95a78140772ab3e96",
        "tcin": product_id,
        "pricing_store_id": "3991",
        "has_pricing_store_id": "true",
        "visitor_id": "0181C5E21E8B02019FE5B36A03DD88B0",
        "region_id": "3991",
        "is_bot": "false",
        "member_id": "0",
        "has_member_id": "false",
        "has_physical_store_id": "true",
        "physical_store_id": "3991",
        "channel": "WEB",
        "page": "/p/-/A-" + product_id
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"https://www.target.com/p/-/A-{product_id}"
    }
    
    def get_best_image_url(product_id, item_data):
        """Helper function to get the best available image URL"""
        # List of possible image URL formats
        image_formats = [
            # Primary image from enrichment
            lambda: item_data.get("enrichment", {}).get("images", {}).get("primary_image_url"),
            # First alternate image from enrichment
            lambda: item_data.get("enrichment", {}).get("images", {}).get("alternate_image_urls", [None])[0],
            # Scene7 high quality format with GUEST prefix
            lambda: f"https://target.scene7.com/is/image/Target/GUEST_{product_id}?wid=800&hei=800&qlt=80",
            # Scene7 high quality format
            lambda: f"https://target.scene7.com/is/image/Target/{product_id}?wid=800&hei=800&qlt=80",
            # Basic format with GUEST prefix
            lambda: f"https://target.scene7.com/is/image/Target/GUEST_{product_id}",
            # Basic format
            lambda: f"https://target.scene7.com/is/image/Target/{product_id}"
        ]
        
        # Try each format until we get a working URL
        for get_url in image_formats:
            try:
                url = get_url()
                if url:
                    # Verify the image URL works
                    response = requests.head(url, timeout=5)
                    if response.status_code == 200:
                        print(f"Found working image URL: {url}")
                        return url
            except:
                continue
        
        # Return the default format if nothing else works
        return f"https://target.scene7.com/is/image/Target/GUEST_{product_id}?wid=800&hei=800&qlt=80"
    
    try:
        response = requests.get(api_url, params=params, headers=headers)
        print(f"Product API response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Default product info
            product_info = {
                "name": f"Target Product {product_id}",
                "image": f"https://target.scene7.com/is/image/Target/GUEST_{product_id}",
                "rating": 0,
                "review_count": 0,
                "rating_distribution": None,
                "recommended_percentage": None,
                "reviews_with_images_count": None
            }
            
            try:
                if "data" in data and "product" in data["data"]:
                    product_data = data["data"]["product"]
                    
                    # Extract product details
                    if "item" in product_data:
                        item = product_data["item"]
                        
                        # Get product name
                        if "product_description" in item:
                            desc = item["product_description"]
                            if "title" in desc:
                                product_info["name"] = desc["title"]
                            elif "downstream_description" in desc:
                                product_info["name"] = desc["downstream_description"]
                        
                        # Get brand name
                        if "primary_brand" in item:
                            brand = item["primary_brand"].get("name")
                            if brand and brand.lower() not in product_info["name"].lower():
                                product_info["name"] = f"{brand} - {product_info['name']}"
                        
                        # Get product image using helper function
                        product_info["image"] = get_best_image_url(product_id, item)
                        
                        # Get rating and review count
                        if "ratings_and_reviews" in item:
                            stats = item["ratings_and_reviews"]
                            if "statistics" in stats:
                                statistics = stats["statistics"]
                                if "rating" in statistics:
                                    product_info["rating"] = float(statistics["rating"].get("average", 0))
                                    # Add rating distribution if available
                                    if "distribution" in statistics["rating"]:
                                        product_info["rating_distribution"] = statistics["rating"]["distribution"]
                                if "review_count" in statistics:
                                    product_info["review_count"] = int(statistics["review_count"])
                                    # Add recommended percentage if available
                                    if "recommended_percentage" in statistics:
                                        product_info["recommended_percentage"] = statistics["recommended_percentage"]
                                    # Add reviews with images count if available
                                    if "reviews_with_images_count" in statistics:
                                        product_info["reviews_with_images_count"] = statistics["reviews_with_images_count"]
                
                print(f"Found product details: {json.dumps(product_info, indent=2)}")
                return product_info
                
            except Exception as e:
                print(f"Error parsing product details: {str(e)}")
                print("API Response:", json.dumps(data, indent=2)[:1000])  # Print first 1000 chars of response
                return product_info
                
        else:
            print(f"Error accessing Target API: {response.status_code}")
            print(response.text)
            
            # Try alternate product API
            alt_url = f"https://redsky.target.com/v3/pdp/tcin/{product_id}"
            alt_params = {
                "key": "9f36aeafbe60771e321a7cc95a78140772ab3e96",
                "channel": "WEB"
            }
            
            alt_response = requests.get(alt_url, params=alt_params, headers=headers)
            if alt_response.status_code == 200:
                alt_data = alt_response.json()
                product_info = {
                    "name": alt_data.get("item", {}).get("product_description", {}).get("title", f"Target Product {product_id}"),
                    "image": get_best_image_url(product_id, alt_data.get("item", {})),
                    "rating": float(alt_data.get("item", {}).get("ratings_and_reviews", {}).get("statistics", {}).get("rating", {}).get("average", 0)),
                    "review_count": int(alt_data.get("item", {}).get("ratings_and_reviews", {}).get("statistics", {}).get("review_count", 0)),
                    "rating_distribution": None,
                    "recommended_percentage": None,
                    "reviews_with_images_count": None
                }
                return product_info
            
            return None
            
    except Exception as e:
        print(f"Error fetching Target product details: {str(e)}")
        return None

def scrape_comments(product_id="89799762"):
    # First get product details
    product_info = get_target_product_details(product_id)
    if not product_info:
        product_info = {
            "name": f"Target Product {product_id}",
            "image": f"https://target.scene7.com/is/image/Target/GUEST_{product_id}",
            "rating": 0,
            "review_count": 0,
            "rating_distribution": None,
            "recommended_percentage": None,
            "reviews_with_images_count": None
        }
    
    # Use the API endpoint to get reviews
    base_url = "https://r2d2.target.com/ggc/v2/summary"
    
    # Parameters
    params = {
        "key": "c6b68aaef0eac4df4931aae70500b7056531cb37",
        "hasOnlyPhotos": "false",
        "includes": "reviews,reviewsWithPhotos,entities,metadata,statistics",
        "page": "1",
        "entity": "",
        "reviewedId": product_id,  # Use the provided product ID
        "reviewType": "PRODUCT",
        "size": "50",  # Get more reviews per request
        "sortBy": "most_recent",
        "verifiedOnly": "false"
    }
    
    comments = []
    max_pages = 2  # Limit the number of pages to fetch
    
    for page in range(1, max_pages + 1):
        try:
            # Update the page parameter
            params["page"] = str(page)
            
            # Add randomized delay to seem more human
            
            # Make the API request
            print(f"Fetching page {page} of reviews...")
            response = requests.get(base_url, params=params)
            
            # Check if the request was successful
            if response.status_code == 200:
                data = response.json()
                
                # Update product info from metadata if available
                if page == 1:
                    if "statistics" in data:
                        stats = data["statistics"]
                        if "rating" in stats:
                            rating_data = stats["rating"]
                            product_info["rating"] = float(rating_data.get("average", 0))
                            # Extract rating distribution
                            if "distribution" in rating_data:
                                product_info["rating_distribution"] = rating_data["distribution"]
                        if "review_count" in stats:
                            product_info["review_count"] = int(stats.get("review_count", 0))
                        if "recommended_percentage" in stats:
                            product_info["recommended_percentage"] = stats.get("recommended_percentage")
                        if "reviews_with_images_count" in stats:
                            product_info["reviews_with_images_count"] = stats.get("reviews_with_images_count")
                    elif "metadata" in data:
                        metadata = data["metadata"]
                        if "title" in metadata and not product_info["name"].startswith("Target Product"):
                            product_info["name"] = metadata["title"]
                
                # Extract reviews from the response
                if "reviews" in data and "results" in data["reviews"]:
                    reviews = data["reviews"]["results"]
                    
                    if not reviews:
                        print(f"No more reviews found on page {page}")
                        break
                    
                    # Extract title and text from each review
                    for review in reviews:
                        title = review.get("title", "")
                        text = review.get("text", "")
                        rating = review.get("rating", review.get("Rating", ""))  # Try both field names
                        
                        # Combine rating, title and text
                        full_comment = f"[{rating}/5] {title}: {text}" if title else f"[{rating}/5] {text}"
                        
                        if full_comment and len(full_comment) > 10 and full_comment not in comments:
                            comments.append(full_comment)
                else:
                    print("No reviews found in the API response")
                    print("Response structure:", json.dumps(data.keys(), indent=2))
                    break
            else:
                print(f"API request failed with status code: {response.status_code}")
                break
                
        except Exception as e:
            print(f"Error fetching reviews:", str(e))
            break
    
    print(f"Scraped {len(comments)} comments in total")
    print(f"Product info: {json.dumps(product_info, indent=2)}")
    
    # If no reviews found, add a message
    if len(comments) == 0:
        comments.append("[3/5] No reviews available for this product. Try a different product.")
    
    return {
        "comments": comments,
        "product_name": product_info["name"],
        "product_image": product_info["image"],
        "rating": product_info["rating"],
        "review_count": product_info["review_count"],
        "rating_distribution": product_info["rating_distribution"],
        "recommended_percentage": product_info["recommended_percentage"],
        "reviews_with_images_count": product_info["reviews_with_images_count"]
    }