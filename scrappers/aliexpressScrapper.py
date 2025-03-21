import requests
import json
import time
import random
import numpy as np
import re
from datetime import datetime

def scrape_aliexpress_comments(product_id=None, product_url=None, max_pages=3):
    """
    Get product reviews from AliExpress API
    
    Args:
        product_id (str): The AliExpress product ID
        product_url (str): Full URL to the product (optional if product_id is provided)
        max_pages (int): Maximum number of pages to fetch
        
    Returns:
        dict: Dictionary containing comments array, product name, product image, and rating info
    """
    if not product_id and not product_url:
        raise ValueError("Either product_id or product_url must be provided")
    
    # If product_id is not provided, try to extract it from the URL
    if not product_id and product_url:
        # Extract product ID from URL pattern
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
                print(f"Extracted product ID: {product_id}")
                break
                
        if not product_id:
            raise ValueError("Could not extract product ID from URL")
    
    # Base URL for the API
    feedback_api_url = "https://feedback.aliexpress.com/pc/searchEvaluation.do"
    
    # Headers to mimic a browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"https://www.aliexpress.com/item/{product_id}.html",
        "Origin": "https://www.aliexpress.com",
        "Connection": "keep-alive"
    }
    
    # Alternative countries to try for more English reviews
    countries = ["US", "GB", "CA", "AU", "TR", "NZ", "IE", "ZA"]
    
    all_comments = []
    product_info = {
        "name": f"AliExpress Product {product_id}",
        "image": None,
        "rating": 0,
        "totalRatingCount": 0,
        "reviewCount": 0
    }
    
    # Try to get product details directly first using aliexpress.com
    try:
        # Create a direct product page URL
        product_page_url = f"https://www.aliexpress.com/item/{product_id}.html"
        print(f"Fetching product details from: {product_page_url}")
        
        # Use a specific User-Agent that's more likely to work with AliExpress
        detail_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "max-age=0"
        }
        
        page_response = requests.get(product_page_url, headers=detail_headers, timeout=10)
        
        if page_response.status_code == 200:
            # Try to extract product name and image using regex
            html_content = page_response.text
            
            # Extract product name
            name_match = re.search(r',"title":"([^"]+)"', html_content)
            if name_match:
                product_info["name"] = name_match.group(1).replace('\\', '')
                print(f"Found product name: {product_info['name']}")
                
            # Extract product image
            image_match = re.search(r'"imagePathList":\["([^"]+)"\]', html_content)
            if image_match:
                product_info["image"] = image_match.group(1)
                if not product_info["image"].startswith("http"):
                    product_info["image"] = "https:" + product_info["image"]
                print(f"Found product image: {product_info['image']}")
                
            # Extract rating
            rating_match = re.search(r'"averageStar":"([^"]+)"', html_content)
            if rating_match:
                try:
                    product_info["rating"] = float(rating_match.group(1))
                    print(f"Found product rating: {product_info['rating']}")
                except:
                    pass
                    
            # Extract review count
            review_count_match = re.search(r'"totalValidNum":"(\d+)"', html_content)
            if review_count_match:
                product_info["reviewCount"] = int(review_count_match.group(1))
                product_info["totalRatingCount"] = product_info["reviewCount"]
                print(f"Found review count: {product_info['reviewCount']}")
    except Exception as e:
        print(f"Error fetching product details page: {str(e)}")
    
    # Try another API for product details if we couldn't get them from the page
    if not product_info["image"] or product_info["name"] == f"AliExpress Product {product_id}":
        try:
            # Try the ae01 API which often has product details
            detail_api_url = f"https://www.aliexpress.com/item/{product_id}.html?gatewayAdapt=glo2usa&_randl_shipto=US"
            print(f"Trying alternative API for product details: {detail_api_url}")
            
            detail_response = requests.get(detail_api_url, headers=headers, timeout=10)
            
            if detail_response.status_code == 200:
                # Look for image URLs in the response
                detail_html = detail_response.text
                
                # Try to find the main image gallery
                image_urls = re.findall(r'"imagePathList":\s*\[\s*"([^"]+)"', detail_html)
                if image_urls:
                    image_url = image_urls[0]
                    if not image_url.startswith("http"):
                        image_url = "https:" + image_url
                    product_info["image"] = image_url
                    print(f"Found product image from alternative API: {product_info['image']}")
                
                # Try to find product name
                title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', detail_html)
                if title_match:
                    product_info["name"] = title_match.group(1).strip()
                    print(f"Found product name from alternative API: {product_info['name']}")
        except Exception as e:
            print(f"Error fetching from alternative API: {str(e)}")
    
    # Process review pages with new corrected structure
    for page in range(1, max_pages + 1):
        try:
            # Rotate through countries to get more English reviews
            country_index = (page - 1) % len(countries)
            country = countries[country_index]
            
            # Set up parameters for the API
            params = {
                "productId": product_id,
                "lang": "en_US",
                "country": country,
                "page": page,
                "pageSize": 50,  # Maximum page size
                "filter": "all",  # Get all reviews
                "sort": "complex_default"  # Default sorting
            }
            
            print(f"Fetching page {page} of reviews for product {product_id} from {country}...")
            
            # Add a delay between requests to avoid rate limiting
            if page > 1:
                time.sleep(random.uniform(1.5, 3))
            
            response = requests.get(feedback_api_url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Save the raw response for debugging
                    with open(f"aliexpress_raw_response_page{page}.json", "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
                    
                    # Check response structure
                    if "data" in data:
                        # Extract product info if available
                        if page == 1 and "productEvaluationStatistic" in data["data"]:
                            stats = data["data"]["productEvaluationStatistic"]
                            
                            if "evarageStar" in stats:
                                product_info["rating"] = float(stats["evarageStar"])
                                print(f"Found product rating from API: {product_info['rating']}")
                                
                            if "totalNum" in stats:
                                product_info["reviewCount"] = int(stats["totalNum"])
                                product_info["totalRatingCount"] = product_info["reviewCount"]
                                print(f"Found review count from API: {product_info['reviewCount']}")
                        
                        # Check for reviews in the correct path: data.evaViewList
                        if "evaViewList" in data["data"] and isinstance(data["data"]["evaViewList"], list):
                            reviews = data["data"]["evaViewList"]
                            print(f"Found {len(reviews)} reviews on page {page}")
                            
                            # Check pagination info
                            if "currentPage" in data["data"] and "totalPage" in data["data"]:
                                current_page = data["data"]["currentPage"]
                                total_pages = data["data"]["totalPage"]
                                print(f"Page {current_page} of {total_pages}")
                                
                                if current_page >= total_pages:
                                    print("Reached the last page of reviews")
                                    if page < max_pages:
                                        max_pages = page  # Stop after this page
                            
                            # Process each review in the list
                            for review in reviews:
                                try:
                                    # Extract rating (buyerEval is out of 100, so divide by 20 to get 1-5)
                                    if "buyerEval" in review:
                                        rating = int(review["buyerEval"]) / 20
                                    else:
                                        rating = 3  # Default to 3 stars
                                    
                                    # Get review text (prefer translated if available)
                                    review_text = ""
                                    if "buyerTranslationFeedback" in review and review["buyerTranslationFeedback"]:
                                        review_text = review["buyerTranslationFeedback"].strip()
                                    elif "buyerFeedback" in review:
                                        review_text = review["buyerFeedback"].strip()
                                    
                                    # Skip empty reviews
                                    if not review_text:
                                        continue
                                    
                                    # Get reviewer name
                                    reviewer_name = "AliExpress Shopper"
                                    if "buyerName" in review and review["buyerName"]:
                                        reviewer_name = review["buyerName"]
                                    
                                    # Get country
                                    reviewer_country = ""
                                    if "buyerCountry" in review and review["buyerCountry"]:
                                        reviewer_country = review["buyerCountry"]
                                    
                                    # Get date
                                    review_date = ""
                                    if "evalDate" in review:
                                        review_date = review["evalDate"]
                                    
                                    # Get SKU info (product variant)
                                    variant_info = ""
                                    if "skuInfo" in review and review["skuInfo"]:
                                        variant_info = review["skuInfo"]
                                    
                                    # Format the review
                                    formatted_review = f"[{rating:.0f}/5] {review_text}"
                                    
                                    # Add variant info if available
                                    if variant_info:
                                        formatted_review += f" (Variant: {variant_info})"
                                    
                                    # Add reviewer and country info
                                    formatted_review += f" - {reviewer_name}"
                                    if reviewer_country:
                                        formatted_review += f" from {reviewer_country}"
                                    
                                    # Add date
                                    if review_date:
                                        formatted_review += f" ({review_date})"
                                    
                                    # Check for images
                                    if "images" in review and review["images"]:
                                        formatted_review += " [Review includes product photos]"
                                    
                                    # Add to comments array
                                    all_comments.append(formatted_review)
                                    
                                except Exception as e:
                                    print(f"Error processing review: {str(e)}")
                        else:
                            print(f"No reviews found in response. Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    else:
                        print("No 'data' field in response")
                    
                except Exception as e:
                    print(f"Error parsing JSON response: {str(e)}")
                    
            else:
                print(f"Error accessing AliExpress API: {response.status_code}")
                print(response.text[:200])  # Show first bit of the response
                
        except Exception as e:
            print(f"Error processing page {page}: {str(e)}")
    
    # If we still couldn't find a product image, use a placeholder
    if not product_info["image"]:
        product_info["image"] = f"https://ae01.alicdn.com/kf/placeholder_1.png"
        print("Using placeholder image")
    
    print(f"Total reviews found: {len(all_comments)}")
    
    # If we found no reviews, add a placeholder message
    if len(all_comments) == 0:
        # Try to find reviews directly from the JSON data you pasted
        try:
            print("Trying to parse reviews from raw data...")
            # Save this data to a file for processing
            with open("aliexpress_raw_data.json", "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                
            if "data" in raw_data and "evaViewList" in raw_data["data"]:
                reviews = raw_data["data"]["evaViewList"]
                print(f"Found {len(reviews)} reviews in raw data")
                
                for review in reviews:
                    try:
                        # Get rating (usually out of 100, divide by 20 to get 1-5)
                        rating = 3  # Default
                        if "buyerEval" in review:
                            rating = int(review["buyerEval"]) / 20
                        
                        # Get review text
                        if "buyerTranslationFeedback" in review and review["buyerTranslationFeedback"]:
                            review_text = review["buyerTranslationFeedback"].strip()
                        elif "buyerFeedback" in review:
                            review_text = review["buyerFeedback"].strip()
                        else:
                            continue  # Skip if no review text
                        
                        # Format review
                        formatted_review = f"[{rating:.0f}/5] {review_text}"
                        
                        # Get variant info
                        if "skuInfo" in review and review["skuInfo"]:
                            formatted_review += f" (Variant: {review['skuInfo']})"
                        
                        # Get reviewer info
                        reviewer = "AliExpress Shopper"
                        if "buyerName" in review and review["buyerName"]:
                            reviewer = review["buyerName"]
                        
                        # Add country
                        if "buyerCountry" in review and review["buyerCountry"]:
                            formatted_review += f" - {reviewer} from {review['buyerCountry']}"
                        else:
                            formatted_review += f" - {reviewer}"
                        
                        # Add date
                        if "evalDate" in review and review["evalDate"]:
                            formatted_review += f" ({review['evalDate']})"
                        
                        # Add to comments
                        all_comments.append(formatted_review)
                    except Exception as e:
                        print(f"Error processing raw review: {str(e)}")
        except Exception as e:
            print(f"Error processing raw data: {str(e)}")
            
        # If still no reviews, add a default message
        if len(all_comments) == 0:
            all_comments.append("[3/5] No reviews available for this product. Try a different product.")
    
    # Create a numpy array from the comments
    comments_array = np.array(all_comments)
    
    # Save the reviews to files
    try:
        np.save(f"aliexpress_reviews_{product_id}.npy", comments_array)
        print(f"Saved {len(comments_array)} reviews to aliexpress_reviews_{product_id}.npy")
        
        # Also save as text
        with open(f"aliexpress_reviews_{product_id}.txt", "w", encoding="utf-8") as f:
            for i, comment in enumerate(all_comments):
                f.write(f"{i+1}. {comment}\n\n")
    except Exception as e:
        print(f"Error saving reviews: {str(e)}")
    
    return {
        "comments": comments_array,
        "product_name": product_info["name"],
        "product_image": product_info["image"],
        "rating": product_info["rating"],
        "review_count": product_info["reviewCount"]
    }

# Create a method that loads from the JSON data you provided
def load_reviews_from_json_data(json_data_file):
    """
    Load reviews from a saved JSON file
    """
    all_comments = []
    
    try:
        with open(json_data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check if the data has the expected structure
        if "data" in data and "evaViewList" in data["data"]:
            reviews = data["data"]["evaViewList"]
            print(f"Found {len(reviews)} reviews in JSON file")
            
            for review in reviews:
                try:
                    # Get rating (usually out of 100, divide by 20 to get 1-5)
                    rating = 3  # Default
                    if "buyerEval" in review:
                        rating = int(review["buyerEval"]) / 20
                    
                    # Get review text
                    if "buyerTranslationFeedback" in review and review["buyerTranslationFeedback"]:
                        review_text = review["buyerTranslationFeedback"].strip()
                    elif "buyerFeedback" in review:
                        review_text = review["buyerFeedback"].strip()
                    else:
                        continue  # Skip if no review text
                    
                    # Format review
                    formatted_review = f"[{rating:.0f}/5] {review_text}"
                    
                    # Get variant info
                    if "skuInfo" in review and review["skuInfo"]:
                        formatted_review += f" (Variant: {review['skuInfo']})"
                    
                    # Get reviewer info
                    reviewer = "AliExpress Shopper"
                    if "buyerName" in review and review["buyerName"]:
                        reviewer = review["buyerName"]
                    
                    # Add country
                    if "buyerCountry" in review and review["buyerCountry"]:
                        formatted_review += f" - {reviewer} from {review['buyerCountry']}"
                    else:
                        formatted_review += f" - {reviewer}"
                    
                    # Add date
                    if "evalDate" in review and review["evalDate"]:
                        formatted_review += f" ({review['evalDate']})"
                    
                    # Add to comments
                    all_comments.append(formatted_review)
                except Exception as e:
                    print(f"Error processing JSON review: {str(e)}")
            
            # Product info
            product_info = {
                "name": "AliExpress Product",
                "image": "https://ae01.alicdn.com/kf/placeholder_1.png",
                "rating": 0,
                "reviewCount": 0
            }
            
            # Get product rating and count if available
            if "productEvaluationStatistic" in data["data"]:
                stats = data["data"]["productEvaluationStatistic"]
                if "evarageStar" in stats:
                    product_info["rating"] = float(stats["evarageStar"])
                if "totalNum" in stats:
                    product_info["reviewCount"] = int(stats["totalNum"])
            
            return {
                "comments": np.array(all_comments),
                "product_name": product_info["name"],
                "product_image": product_info["image"],
                "rating": product_info["rating"],
                "review_count": product_info["reviewCount"]
            }
    except Exception as e:
        print(f"Error loading reviews from JSON: {str(e)}")
    
    return {
        "comments": np.array(["[3/5] No reviews available from JSON file."]),
        "product_name": "AliExpress Product",
        "product_image": "https://ae01.alicdn.com/kf/placeholder_1.png",
        "rating": 0,
        "review_count": 0
    }

if __name__ == "__main__":
    # Example usage
    product_url = "https://www.aliexpress.com/item/1005005790166027.html"
    result = scrape_aliexpress_comments(product_url=product_url, max_pages=2)
    
    print("\nProduct:", result["product_name"])
    print("Image URL:", result["product_image"])
    print(f"Rating: {result['rating']} ({result['review_count']} reviews)")
    
    print("\nSample of reviews:")
    for i, review in enumerate(result["comments"][:5]):  # Print first 5 reviews
        print(f"{i+1}. {review}")
        print("-" * 80)
    
    # Alternative: Try loading reviews from JSON data
    print("\nTrying to load reviews from JSON data...")
    # First save your JSON data to a file
    with open("aliexpress_sample_data.json", "w", encoding="utf-8") as f:
        f.write("""
        {
          "displayMessage": {"reviewStructureAdditionalFeedback": "Additional Feedback "},
          "data": {
            "currentPage": 3,
            "evaViewList": [
              {
                "buyerCountry": "ES",
                "buyerEval": 60,
                "buyerFeedback": "La talla M me viene supergrande. Tendría que haber pedido una talla menos",
                "buyerName": "E***r",
                "buyerTranslationFeedback": "Size M is super big for me. Should have ordered one size less",
                "evalDate": "09 Nov 2024",
                "skuInfo": "Color:WIine red Size:M "
              },
              {
                "buyerCountry": "FR",
                "buyerEval": 80,
                "buyerFeedback": "Je vous remercie",
                "buyerName": "AliExpress Shopper",
                "buyerTranslationFeedback": "I thank you",
                "evalDate": "14 Oct 2024",
                "skuInfo": "Color:black Size:M "
              }
            ],
            "productEvaluationStatistic": {
              "evarageStar": 4.4,
              "totalNum": 4398
            }
          }
        }
        """)
    
    json_result = load_reviews_from_json_data("aliexpress_sample_data.json")
    print("\nProduct from JSON:", json_result["product_name"])
    print(f"Rating from JSON: {json_result['rating']} ({json_result['review_count']} reviews)")
    
    print("\nSample of reviews from JSON:")
    for i, review in enumerate(json_result["comments"]):
        print(f"{i+1}. {review}")
        print("-" * 80)