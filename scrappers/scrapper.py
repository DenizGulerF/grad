import requests
import json
import time
import random

def scrape_comments(product_id="89799762"):
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
    max_pages = 1  # Limit the number of pages to fetch
    
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
                
                # Extract reviews from the response
                # The reviews are nested in data["reviews"]["results"]
                if "reviews" in data and "results" in data["reviews"]:
                    reviews = data["reviews"]["results"]
                    
                    if not reviews:
                        print(f"No more reviews found on page {page}")
                        break
                    
                    #print(f"Found {len(reviews)} reviews on page {page}")
                    
                    # Extract title and text from each review
                    for review in reviews:
                        title = review.get("title", "")
                        text = review.get("text", "")
                        rating = review.get("Rating", "")
                        
                        # Combine rating, title and text
                        full_comment = f"[{rating}/5] {title}: {text}" if title else f"[{rating}/5] {text}"
                        
                        if full_comment and len(full_comment) > 10 and full_comment not in comments:
                            comments.append(full_comment)
                else:
                    print("No reviews found in the API response")
                   # print("Response structure:", json.dumps(data.keys(), indent=2))
                    break
            else:
                print(f"API request failed with status code: {response.status_code}")
                break
                
        except Exception as e:
            print(f"Error fetching reviews from page {page}: {e}")
            break
    
    print(f"Scraped {len(comments)} comments in total")
    return comments