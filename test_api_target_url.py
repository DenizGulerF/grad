import requests
import json

# Test the API with Sony headphones
url = "http://localhost:5000/scrape_only"

# Extract product ID from the Sony headphones URL
sony_url = "https://www.target.com/p/sony-wh-1000xm5-noise-canceling-overhead-bluetooth-wireless-headphones-black/-/A-79757327"
product_id = "79757327"

data = {
    "source": "target",
    "product_id": product_id,
    "export_csv": False
}

print(f"Testing Target URL generation for product ID: {product_id}")
print(f"Original URL: {sony_url}")
print(f"Sending request to API...")

try:
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ API Response successful!")
        print(f"Product Name: {result.get('product_name', 'N/A')}")
        print(f"Generated URL: {result.get('product_link', 'N/A')}")
        print(f"Expected URL: {sony_url}")
        print(f"URLs match: {result.get('product_link') == sony_url}")
        
        # Check if it's close (allowing for minor differences)
        generated = result.get('product_link', '')
        if 'sony-wh-1000xm5' in generated and '79757327' in generated:
            print("✅ URL contains expected product slug and ID")
        else:
            print("❌ URL doesn't contain expected elements")
            
    else:
        print(f"❌ API Error: {response.status_code}")
        print(f"Response: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("❌ Could not connect to API. Make sure the server is running on localhost:5000")
except Exception as e:
    print(f"❌ Error: {str(e)}") 