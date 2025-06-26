#!/usr/bin/env python3
"""
Test script for CSV export functionality
"""

import sys
import os
import json
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.csv_exporter import get_csv_exporter

def create_sample_data():
    """Create sample scraped data for testing"""
    
    # Sample Target data
    target_data = {
        'product_name': 'iPhone 16 Pro Max - 256GB - Natural Titanium',
        'product_image': 'https://target.scene7.com/is/image/Target/GUEST_12345678',
        'review_count': 150,
        'rating': 4.2,
        'source': 'target',
        'product_link': 'https://www.target.com/p/A-12345678',
        'rating_distribution': {
            '1': 5,
            '2': 8,
            '3': 22,
            '4': 45,
            '5': 70
        },
        'recommended_percentage': 85.3,
        'reviews_with_images_count': 25,
        'comments': [
            '[5/5] Amazing phone! The camera quality is outstanding and the battery lasts all day. - John D from New York (2024-01-15)',
            '[4/5] Great phone overall, but the price is quite high. Worth it for the features though. - Sarah M from California (2024-01-14)',
            '[3/5] Good phone but nothing revolutionary. The upgrade from iPhone 15 Pro is minimal. - Mike R from Texas (2024-01-13)',
            '[5/5] Love the new Action Button and the improved cameras. Best iPhone yet! - Lisa K from Florida (2024-01-12)',
            '[2/5] Had issues with the battery draining quickly. Might be a defective unit. - Tom B from Illinois (2024-01-11)',
            '[4/5] (Variant: Natural Titanium) Beautiful design and feels premium. Face ID works perfectly. - Emma S from Washington (2024-01-10)',
            '[5/5] Fast shipping and phone works as expected. Very satisfied with purchase. [Review includes product photos] - David L from Oregon (2024-01-09)',
            '[4/5] Camera is excellent for photography. Video recording is smooth and stable. - Rachel P from Nevada (2024-01-08)',
            '[3/5] Phone is good but iOS still has some limitations compared to Android. - Alex W from Colorado (2024-01-07)',
            '[5/5] Perfect phone for professional use. No complaints at all! - Jennifer H from Arizona (2024-01-06)'
        ]
    }
    
    # Sample AliExpress data
    aliexpress_data = {
        'product_name': 'Wireless Bluetooth Headphones - Noise Cancelling',
        'product_image': 'https://ae01.alicdn.com/kf/example_image.jpg',
        'review_count': 523,
        'rating': 4.6,
        'source': 'aliexpress',
        'product_link': 'https://www.aliexpress.com/item/1005007189293096.html',
        'rating_distribution': {
            '1': 12,
            '2': 15,
            '3': 45,
            '4': 178,
            '5': 273
        },
        'comments': [
            '[5/5] Excellent sound quality and noise cancellation works great! (Variant: Black) - AudioLover from US (12 Dec 2024)',
            '[4/5] Good headphones for the price. Comfortable to wear for long periods. - MusicFan from GB (11 Dec 2024)',
            '[5/5] Fast delivery and product exactly as described. Highly recommend! - SatisfiedBuyer from CA (10 Dec 2024)',
            '[3/5] Average sound quality but good build. Expected better noise cancellation. (Variant: White) - Reviewer123 from AU (09 Dec 2024)',
            '[5/5] Amazing bass and clear highs. Perfect for music and calls. [Review includes product photos] - BassBoss from DE (08 Dec 2024)',
            '[4/5] Battery life is excellent, lasts for days. Comfortable fit. - LongListener from FR (07 Dec 2024)',
            '[2/5] Had connectivity issues with my phone. Works better now after reset. - TechUser from IT (06 Dec 2024)',
            '[5/5] Best headphones I\'ve bought at this price range. Worth every penny! - HappyCustomer from ES (05 Dec 2024)'
        ]
    }
    
    # Sample Trendyol data
    trendyol_data = {
        'product_name': 'Erkek Kışlık Mont - Siyah - L Beden',
        'product_image': 'https://cdn.dsmcdn.com/ty123/product_image.jpg',
        'review_count': 89,
        'rating': 4.1,
        'source': 'trendyol',
        'product_link': 'https://www.trendyol.com/brand/mont-p-782213857',
        'comments': [
            '[5/5] Çok kaliteli bir mont. Soğuktan koruyor ve şık duruyor. - Ahmet K (15 Ocak 2024)',
            '[4/5] Güzel mont ama biraz dar kalıyor. Bir beden büyük almak lazım. - Mehmet S (14 Ocak 2024)',
            '[5/5] Hızlı kargo ve ürün açıklamaya uygun. Memnun kaldım. - Fatma D (13 Ocak 2024)',
            '[3/5] Fiyatına göre iyi ama çok premium değil. Ortalama kalite. - Zeynep M (12 Ocak 2024)',
            '[4/5] Sıcak tutuyor ve rahat. Rengi de güzel. - Okan T (11 Ocak 2024)',
            '[5/5] Mükemmel mont! Çok beğendim, herkese tavsiye ederim. - Ayşe Y (10 Ocak 2024)'
        ]
    }
    
    return target_data, aliexpress_data, trendyol_data

def test_csv_export():
    """Test the CSV export functionality"""
    
    print("🚀 Testing CSV Export Functionality")
    print("=" * 50)
    
    # Get CSV exporter
    csv_exporter = get_csv_exporter(output_dir="test_exports")
    
    # Create sample data
    target_data, aliexpress_data, trendyol_data = create_sample_data()
    
    print("\n📊 Exporting Target product data...")
    try:
        # Export Target data
        target_csv = csv_exporter.export_scraped_data(
            scraped_data=target_data,
            source='target',
            product_id='12345678'
        )
        target_summary = csv_exporter.export_product_summary(
            scraped_data=target_data,
            source='target',
            product_id='12345678'
        )
        print(f"✅ Target CSV exported: {target_csv}")
        print(f"✅ Target summary exported: {target_summary}")
    except Exception as e:
        print(f"❌ Error exporting Target data: {str(e)}")
    
    print("\n📊 Exporting AliExpress product data...")
    try:
        # Export AliExpress data
        aliexpress_csv = csv_exporter.export_scraped_data(
            scraped_data=aliexpress_data,
            source='aliexpress',
            product_id='1005007189293096'
        )
        aliexpress_summary = csv_exporter.export_product_summary(
            scraped_data=aliexpress_data,
            source='aliexpress',
            product_id='1005007189293096'
        )
        print(f"✅ AliExpress CSV exported: {aliexpress_csv}")
        print(f"✅ AliExpress summary exported: {aliexpress_summary}")
    except Exception as e:
        print(f"❌ Error exporting AliExpress data: {str(e)}")
    
    print("\n📊 Exporting Trendyol product data...")
    try:
        # Export Trendyol data
        trendyol_csv = csv_exporter.export_scraped_data(
            scraped_data=trendyol_data,
            source='trendyol',
            product_id='782213857'
        )
        trendyol_summary = csv_exporter.export_product_summary(
            scraped_data=trendyol_data,
            source='trendyol',
            product_id='782213857'
        )
        print(f"✅ Trendyol CSV exported: {trendyol_csv}")
        print(f"✅ Trendyol summary exported: {trendyol_summary}")
    except Exception as e:
        print(f"❌ Error exporting Trendyol data: {str(e)}")
    
    print("\n📊 Exporting multiple products summary...")
    try:
        # Export multiple products
        all_products = [target_data, aliexpress_data, trendyol_data]
        multi_csv = csv_exporter.export_multiple_products(
            products_data=all_products,
            filename_prefix="all_platforms_comparison"
        )
        print(f"✅ Multi-product CSV exported: {multi_csv}")
    except Exception as e:
        print(f"❌ Error exporting multiple products: {str(e)}")
    
    print("\n📁 Export directory contents:")
    try:
        export_files = os.listdir("test_exports")
        for i, file in enumerate(export_files, 1):
            file_path = os.path.join("test_exports", file)
            file_size = os.path.getsize(file_path)
            print(f"  {i}. {file} ({file_size:,} bytes)")
    except Exception as e:
        print(f"❌ Error listing export files: {str(e)}")
    
    print("\n🎉 CSV Export testing completed!")
    print("\nTo test the integration:")
    print("1. Start your Flask server: python app.py")
    print("2. Use these endpoints:")
    print("   POST /api/scrape_only - with 'export_csv': true")
    print("   POST /api/scrape - with 'export_csv': true") 
    print("   POST /api/export_to_csv - export existing saved products")
    print("   POST /api/export_saved_products_csv - export all user's saved products")
    print("   GET /api/download_csv/<filename> - download exported CSV files")

def sample_api_requests():
    """Print sample API request examples"""
    
    print("\n" + "=" * 60)
    print("📝 SAMPLE API REQUESTS")
    print("=" * 60)
    
    print("\n1️⃣  Scrape Target product with CSV export:")
    print("""
    POST /api/scrape_only
    Headers: 
        Authorization: Bearer <your_jwt_token>
        Content-Type: application/json
    Body:
    {
        "source": "target",
        "product_url": "https://www.target.com/p/iphone-16-A-12345678",
        "export_csv": true
    }
    """)
    
    print("\n2️⃣  Scrape AliExpress product with CSV export:")
    print("""
    POST /api/scrape_only
    Headers: 
        Authorization: Bearer <your_jwt_token>
        Content-Type: application/json
    Body:
    {
        "source": "aliexpress",
        "product_url": "https://www.aliexpress.com/item/1005007189293096.html",
        "export_csv": true
    }
    """)
    
    print("\n3️⃣  Export existing saved product to CSV:")
    print("""
    POST /api/export_to_csv
    Headers: 
        Authorization: Bearer <your_jwt_token>
        Content-Type: application/json
    Body:
    {
        "product_id": "your-saved-product-id"
    }
    """)
    
    print("\n4️⃣  Export all saved products to CSV:")
    print("""
    POST /api/export_saved_products_csv
    Headers: 
        Authorization: Bearer <your_jwt_token>
        Content-Type: application/json
    Body:
    {
        "export_type": "both"  // Options: "detailed", "summary", "both"
    }
    """)
    
    print("\n5️⃣  Download a CSV file:")
    print("""
    GET /api/download_csv/target_reviews_12345678_20240115_143022.csv
    Headers: 
        Authorization: Bearer <your_jwt_token>
    """)

if __name__ == "__main__":
    test_csv_export()
    sample_api_requests() 