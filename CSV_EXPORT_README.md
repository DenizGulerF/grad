# CSV Export Functionality for Product Review Scraper

## Overview

This module provides comprehensive CSV export functionality for scraped product reviews from Target, AliExpress, and Trendyol. It automatically exports review data in structured CSV format with detailed review parsing and product information.

## Features

### ✅ **Automatic CSV Export**
- Automatically exports scraped data to CSV files
- Supports all three platforms: Target, AliExpress, Trendyol
- Generates timestamped filenames for organization
- Creates both detailed reviews and product summary files

### ✅ **Intelligent Review Parsing**
- Extracts individual ratings from review text (e.g., `[5/5]`, `[★★★★★]`)
- Parses reviewer information (name, location, date)
- Identifies product variants (e.g., "Variant: Black")
- Detects reviews with images
- Cleans text for CSV compatibility

### ✅ **Multiple Export Formats**
1. **Detailed Reviews CSV**: One row per review with full details
2. **Product Summary CSV**: One row per product with aggregated data
3. **Multi-Product CSV**: Comparison of multiple products in one file

### ✅ **Comprehensive Data Fields**
- Product information (name, image, rating, review count)
- Individual review details (rating, text, reviewer info)
- Rating distribution (1-5 stars breakdown)
- Platform-specific metrics (recommended percentage, etc.)
- Metadata (scraping timestamp, source platform)

## File Structure

```
├── utils/
│   ├── __init__.py
│   └── csv_exporter.py          # Main CSV export module
├── router/
│   └── scrapper_router.py       # API endpoints with CSV export
├── test_csv_export.py           # Test script
├── exports/                     # Default output directory
│   ├── target_reviews_*.csv     # Target detailed reviews
│   ├── aliexpress_reviews_*.csv # AliExpress detailed reviews
│   ├── trendyol_reviews_*.csv   # Trendyol detailed reviews
│   └── *_summary_*.csv          # Product summaries
└── test_exports/                # Test output directory
```

## API Endpoints

### 1. **Scrape with Automatic CSV Export**

#### POST `/api/scrape_only`
Scrape product reviews without saving to database, with optional CSV export.

```json
{
    "source": "target",
    "product_url": "https://www.target.com/p/iphone-16-A-12345678",
    "export_csv": true
}
```

**Response:**
```json
{
    "product_name": "iPhone 16 Pro Max",
    "rating": 4.2,
    "review_count": 150,
    "comments": [...],
    "csv_exports": {
        "detailed_reviews": "exports/target_reviews_12345678_20240115.csv",
        "product_summary": "exports/target_summary_12345678_20240115.csv"
    }
}
```

#### POST `/api/scrape`
Scrape and save to database with CSV export.

```json
{
    "source": "aliexpress",
    "product_url": "https://www.aliexpress.com/item/1005007189293096.html",
    "export_csv": true
}
```

### 2. **Export Existing Products**

#### POST `/api/export_to_csv`
Export a specific saved product to CSV.

```json
{
    "product_id": "your-saved-product-uuid"
}
```

#### POST `/api/export_saved_products_csv`
Export all saved products for the current user.

```json
{
    "export_type": "both"  // Options: "detailed", "summary", "both"
}
```

**Response:**
```json
{
    "message": "Successfully exported 5 saved products",
    "exported_products_count": 5,
    "csv_files": {
        "all_products_summary": "exports/user_123_saved_products_summary_20240115.csv",
        "detailed_products": {
            "product-uuid-1": {
                "name": "iPhone 16 Pro",
                "csv_path": "exports/target_reviews_product-uuid-1_20240115.csv"
            }
        }
    }
}
```

### 3. **Download CSV Files**

#### GET `/api/download_csv/<filename>`
Download exported CSV files.

```bash
GET /api/download_csv/target_reviews_12345678_20240115_143022.csv
```

## CSV File Formats

### Detailed Reviews CSV

| Column | Description | Example |
|--------|-------------|---------|
| `product_name` | Product title | "iPhone 16 Pro Max - 256GB" |
| `source` | Platform | "target", "aliexpress", "trendyol" |
| `product_rating` | Official product rating | 4.2 |
| `review_count` | Total review count | 150 |
| `review_index` | Review number | 1, 2, 3... |
| `individual_rating` | Extracted rating from review | 5.0 |
| `review_text` | Clean review text | "Amazing phone! Great camera..." |
| `reviewer_name` | Reviewer's name | "John D" |
| `reviewer_location` | Reviewer's location | "New York" |
| `review_date` | Review date | "2024-01-15" |
| `variant_info` | Product variant | "Natural Titanium" |
| `has_images` | Review includes photos | true/false |
| `product_image` | Product image URL | "https://..." |
| `product_link` | Product page URL | "https://..." |
| `scraping_timestamp` | When data was scraped | "20240115_143022" |
| `rating_distribution_*_star` | Rating breakdown | 70 (for 5-star) |
| `recommended_percentage` | % who recommend | 85.3 |
| `reviews_with_images_count` | Reviews with photos | 25 |

### Product Summary CSV

| Column | Description | Example |
|--------|-------------|---------|
| `product_name` | Product title | "iPhone 16 Pro Max" |
| `source` | Platform | "target" |
| `product_id` | Product identifier | "12345678" |
| `official_rating` | Platform's rating | 4.2 |
| `official_review_count` | Platform's review count | 150 |
| `scraped_review_count` | Reviews we scraped | 25 |
| `reviews_with_individual_rating` | Reviews with ratings | 20 |
| `avg_individual_rating` | Average of individual ratings | 4.1 |

## Usage Examples

### Basic Usage

```python
from utils.csv_exporter import get_csv_exporter

# Initialize exporter
exporter = get_csv_exporter(output_dir="my_exports")

# Export scraped data
csv_path = exporter.export_scraped_data(
    scraped_data=target_data,
    source='target',
    product_id='12345678'
)

print(f"Exported to: {csv_path}")
```

### Advanced Usage

```python
# Export multiple products comparison
multi_csv = exporter.export_multiple_products(
    products_data=[target_data, aliexpress_data, trendyol_data],
    filename_prefix="platform_comparison"
)

# Export product summary only
summary_csv = exporter.export_product_summary(
    scraped_data=product_data,
    source='aliexpress',
    product_id='1005007189293096'
)
```

### Testing

Run the test script to verify functionality:

```bash
python test_csv_export.py
```

This will:
- Create sample data for all three platforms
- Export to `test_exports/` directory
- Generate both detailed and summary CSV files
- Display file sizes and locations

## Configuration

### Environment Variables

```bash
# Optional: Set custom export directory
CSV_EXPORT_DIR=/path/to/exports

# Flask app configuration
JWT_SECRET_KEY=your-jwt-secret
```

### Default Settings

- **Output Directory**: `exports/` (auto-created)
- **File Encoding**: UTF-8
- **Timestamp Format**: `YYYYMMDD_HHMMSS`
- **CSV Delimiter**: Comma (`,`)
- **Text Cleaning**: Removes newlines, tabs, normalizes spaces

## Integration with Scrapers

The CSV export is automatically integrated with all scrapers:

### Target Scraper
- Extracts rating distribution
- Includes recommended percentage
- Parses review images count
- Handles product variants

### AliExpress Scraper
- Supports multiple languages
- Extracts variant information
- Handles country-specific reviews
- Includes buyer feedback translations

### Trendyol Scraper
- Turkish language support
- Size/color variants
- Local review patterns
- Platform-specific metrics

## Error Handling

- **Graceful Failures**: CSV export errors don't break scraping
- **Logging**: Detailed logs for debugging
- **Validation**: Checks for required fields
- **Encoding**: Handles special characters and emojis
- **File Conflicts**: Timestamp-based naming prevents overwrites

## Benefits

### 📊 **Data Analysis**
- Open CSV files in Excel, Google Sheets, or any spreadsheet tool
- Easy data filtering and sorting
- Create charts and pivot tables
- Statistical analysis of reviews

### 🔄 **Data Portability**
- Standard CSV format works with all tools
- Easy to import into databases
- Share data with team members
- Backup and archive review data

### 📈 **Business Intelligence**
- Compare products across platforms
- Track sentiment trends over time
- Analyze competitor products
- Generate reports and insights

### 🛠 **Development**
- Debug scraping issues
- Validate data quality
- Test new features
- Create sample datasets

## File Naming Convention

```
{source}_reviews_{product_id}_{timestamp}.csv          # Detailed reviews
{source}_product_summary_{product_id}_{timestamp}.csv  # Product summary
{prefix}_summary_{timestamp}.csv                       # Multi-product
user_{user_id}_saved_products_summary_{timestamp}.csv  # User exports
```

Examples:
- `target_reviews_12345678_20240115_143022.csv`
- `aliexpress_product_summary_1005007189293096_20240115_143022.csv`
- `platform_comparison_summary_20240115_143022.csv`

## Troubleshooting

### Common Issues

**Issue**: CSV files not being created
- **Solution**: Check write permissions on output directory
- **Check**: Log messages for specific error details

**Issue**: Special characters in reviews causing issues
- **Solution**: Text is automatically cleaned, but check encoding
- **Note**: Files use UTF-8 encoding by default

**Issue**: Large files taking time to export
- **Solution**: This is normal for products with many reviews
- **Tip**: Use summary export for quick overview

**Issue**: Missing review data in CSV
- **Solution**: Check if reviews were successfully scraped first
- **Debug**: Run scraper separately to verify data

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will show detailed information about:
- File creation process
- Review parsing details
- Error messages
- Performance metrics

## Future Enhancements

- [ ] Excel (.xlsx) export format
- [ ] JSON export option
- [ ] Compressed exports for large datasets
- [ ] Scheduled automatic exports
- [ ] Email delivery of exports
- [ ] Custom field selection
- [ ] Data visualization integration
- [ ] API rate limiting for bulk exports

---

## Support

For issues or questions about CSV export functionality:

1. Check the logs for detailed error messages
2. Run `test_csv_export.py` to verify setup
3. Ensure all dependencies are installed
4. Check file permissions on output directory

The CSV export functionality is designed to be robust and handle edge cases gracefully while providing comprehensive product review data in an easily analyzable format. 