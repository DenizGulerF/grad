import requests
import numpy as np
import json
import time
import random

def scrape_trendyol_comments(product_id=None, product_url=None, max_pages=3):
    """
    Get product reviews from Trendyol.com API
    
    Args:
        product_id (str): The Trendyol product ID
        product_url (str): Full URL to the product (optional if product_id is provided)
        max_pages (int): Maximum number of pages to fetch
        
    Returns:
        dict: Dictionary containing comments array, product name, product image, and rating info
    """
    if not product_id and not product_url:
        raise ValueError("Either product_id or product_url must be provided")
    
    # If product_id is not provided, try to extract it from the URL
    if not product_id and product_url:
        # Extract product ID from URL pattern like p-782213857
        import re
        match = re.search(r'p-(\d+)', product_url)
        if match:
            product_id = match.group(1)
        else:
            raise ValueError("Could not extract product ID from URL")
    
    # Base URL for the API
    api_url = f"https://apigw.trendyol.com/discovery-sfint-social-service/api/review/reviews/{product_id}"
    
    # Headers to mimic a browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"https://www.trendyol.com/en/product-p-{product_id}/reviews"
    }
    
    # Parameters for the API - explicitly requesting English reviews
    params = {
        "page": 0,
        "pageSize": 20,
        "storefrontId": 9,
        "language": "en",      # Filter for English language
        "countryCode": "BE",
        "culture": "en-BE"     # Use English culture
    }
    
    all_comments = []
    product_info = {
        "name": f"Trendyol Product {product_id}",
        "image": None,
        "averageRating": 0,
        "totalRatingCount": 0,
        "totalCommentCount": 0
    }
    
    # Get product details and reviews page by page
    for page in range(max_pages):
        try:
            params["page"] = page
            print(f"Fetching page {page} of reviews for product {product_id}...")
            
            # Add a slight delay between requests
           
            
            response = requests.get(api_url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract product info from the first page
                if page == 0 and "contentSummary" in data:
                    summary = data["contentSummary"]
                    product_info["averageRating"] = summary.get("averageRating", 0)
                    product_info["totalRatingCount"] = summary.get("totalRatingCount", 0)
                    product_info["totalCommentCount"] = summary.get("totalCommentCount", 0)
                    
                    # Try to find an image URL in the product reviews
                    if "productReviews" in data and "content" in data["productReviews"]:
                        for review in data["productReviews"]["content"]:
                            if "mediaFiles" in review and review["mediaFiles"]:
                                for media in review["mediaFiles"]:
                                    if media.get("mediaType") == "IMAGE" and "url" in media:
                                        product_info["image"] = media["url"]
                                        break
                                if product_info["image"]:
                                    break
                
                # Extract reviews - filtering for English only
                if "productReviews" in data and "content" in data["productReviews"]:
                    reviews = data["productReviews"]["content"]
                    
                    # Check if we have more pages
                    total_pages = data["productReviews"].get("totalPages", 1)
                    if page >= total_pages - 1:
                        print(f"Reached the last page of reviews ({total_pages} total pages)")
                        break
                    
                    # Process reviews - only include English ones
                    for review in reviews:
                        # Skip non-English reviews
                        if review.get("language", "").lower() != "en":
                            continue
                            
                        rating = review.get("rate", 0)
                        comment = review.get("comment", "").strip()
                        if not comment:
                            continue
                            
                        user = review.get("userFullName", "Trendyol Customer")
                        date = review.get("commentDateISOType", "")
                        size = review.get("productSize", "")
                        
                        # Format the review with rating prefix
                        formatted_review = f"[{rating}/5] {comment}"
                        
                        # Add product size if available
                        if size:
                            formatted_review += f" (Size: {size})"
                        
                        all_comments.append(formatted_review)
                    
                    # If we got very few reviews on this page, Trendyol might be showing
                    # mostly non-English reviews. Try another country code to get more English reviews.
                    if len(reviews) > 0 and sum(1 for r in reviews if r.get("language", "").lower() == "en") < 2:
                        alternative_countries = ["AE", "US", "GB", "QA", "SA"]
                        for country in alternative_countries:
                            if country != params["countryCode"]:
                                params["countryCode"] = country
                                params["culture"] = f"en-{country}"
                                print(f"Switching to country code {country} to find more English reviews")
                                break
                else:
                    print("No reviews found in API response")
                    break
            else:
                print(f"Error accessing Trendyol API: {response.status_code}")
                print(response.text)
                break
                
        except Exception as e:
            print(f"Error fetching Trendyol reviews: {str(e)}")
            break
    
    # Try to get a direct product URL from the Trendyol API to fetch details
    try:
        product_detail_url = f"https://apigw.trendyol.com/discovery-web-productgw-service/api/productDetail/{product_id}?storefrontId=9&culture=en-BE&countryCode=BE"
        detail_response = requests.get(product_detail_url, headers=headers)
        
        if detail_response.status_code == 200:
            detail_data = detail_response.json()
            if "result" in detail_data:
                result = detail_data["result"]
                if "name" in result:
                    product_info["name"] = result["name"]
                if "images" in result and result["images"]:
                    product_info["image"] = "https://cdn.dsmcdn.com/" + result["images"][0]
        else:
            print(f"Could not fetch product details: {detail_response.status_code}")
    except Exception as e:
        print(f"Error fetching product details: {str(e)}")
    
    print(f"Total English reviews found: {len(all_comments)}")
    
    # If we found no reviews, add a message
    if len(all_comments) == 0:
        all_comments.append("[3/5] No English reviews available for this product. Try a different product.")
    
    # Create a numpy array from the comments
    comments_array = np.array(all_comments)
    
    # Save the reviews to a file
    try:
        np.save(f"trendyol_reviews_{product_id}.npy", comments_array)
        print(f"Saved {len(comments_array)} reviews to trendyol_reviews_{product_id}.npy")
        
        # Also save as text
        with open(f"trendyol_reviews_{product_id}.txt", "w", encoding="utf-8") as f:
            for i, comment in enumerate(all_comments):
                f.write(f"{i+1}. {comment}\n\n")
    except Exception as e:
        print(f"Error saving reviews: {str(e)}")
    
    return {
        "comments": comments_array,
        "product_name": product_info["name"],
        "product_image": product_info["image"],
        "rating": product_info["averageRating"],
        "review_count": product_info["totalCommentCount"]
    }

if __name__ == "__main__":
    # Example usage
    product_url = "https://www.trendyol.com/en/trendyol-collection/asymmetric-buttoned-black-woven-vest-twoss24ye00007-p-782213857/reviews"
    result = scrape_trendyol_comments(product_url=product_url, max_pages=3)
    
    print("\nProduct:", result["product_name"])
    print("Image URL:", result["product_image"])
    print(f"Rating: {result['rating']} ({result['review_count']} reviews)")
    
    print("\nSample of reviews:")
    for i, review in enumerate(result["comments"][:5]):  # Print first 5 reviews
        print(f"{i+1}. {review}")
        print("-" * 80)