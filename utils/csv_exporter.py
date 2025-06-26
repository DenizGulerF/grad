import csv
import numpy as np
import re
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CSVExporter:
    """
    CSV Export utility for scraped product reviews - uses built-in CSV module
    """
    
    def __init__(self, output_dir: str = "exports"):
        """
        Initialize CSV exporter
        
        Args:
            output_dir (str): Directory to save CSV files
        """
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"Created output directory: {self.output_dir}")
    
    def clean_text(self, text: str) -> str:
        """
        Clean text for CSV export
        
        Args:
            text (str): Raw text
            
        Returns:
            str: Cleaned text
        """
        if not text or text is None:
            return ""
        
        # Convert to string if not already
        text = str(text)
        
        # Remove or replace problematic characters
        text = text.replace('\n', ' ').replace('\r', ' ')
        text = text.replace('\t', ' ')
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single space
        text = text.strip()
        
        # Remove special characters that might cause CSV issues
        text = text.replace('"', "'")  # Replace double quotes with single quotes
        
        return text
    
    def extract_rating_from_review(self, review: str) -> Optional[float]:
        """
        Extract numerical rating from review text
        
        Args:
            review (str): Review text that might contain rating
            
        Returns:
            Optional[float]: Extracted rating or None
        """
        if not review:
            return None
            
        # Look for patterns like [5/5], [4.5/5], [★★★★★]
        rating_patterns = [
            r'\[(\d+(?:\.\d+)?)/5\]',  # [4.5/5]
            r'\[(\d+(?:\.\d+)?)/10\]',  # [8/10]
            r'\[(\d+)(?:/\d+)?\s*(?:stars?|★+)\]',  # [5 stars]
            r'(\d+(?:\.\d+)?)\s*(?:out of|/)\s*5',  # 4.5 out of 5
            r'★{1,5}',  # Count stars
        ]
        
        for pattern in rating_patterns:
            match = re.search(pattern, review)
            if match:
                if '★' in pattern:
                    # Count the stars
                    stars = len(re.findall(r'★', match.group(0)))
                    return float(stars)
                else:
                    rating = float(match.group(1))
                    # Normalize to 5-point scale if needed
                    if '/10' in pattern and rating > 5:
                        rating = rating / 2
                    return rating
        
        return None
    
    def parse_review_text(self, review: str) -> Dict[str, Any]:
        """
        Parse review text to extract components
        
        Args:
            review (str): Full review text
            
        Returns:
            Dict: Parsed review components
        """
        if not review:
            return {
                'rating': None,
                'review_text': "",
                'reviewer_name': "",
                'reviewer_location': "",
                'review_date': "",
                'variant_info': "",
                'has_images': False
            }
        
        # Extract rating
        rating = self.extract_rating_from_review(review)
        
        # Remove rating from text for clean review text
        clean_review = re.sub(r'\[[\d★]+[/\d★]*\]', '', review).strip()
        
        # Extract reviewer info (pattern: "- Name from Location (Date)")
        reviewer_name = ""
        reviewer_location = ""
        review_date = ""
        
        # Look for reviewer pattern at the end
        reviewer_pattern = r'-\s*([^-]+?)(?:\s+from\s+([^(]+?))?\s*(?:\(([^)]+)\))?\s*$'
        reviewer_match = re.search(reviewer_pattern, clean_review)
        
        if reviewer_match:
            reviewer_name = reviewer_match.group(1).strip() if reviewer_match.group(1) else ""
            reviewer_location = reviewer_match.group(2).strip() if reviewer_match.group(2) else ""
            review_date = reviewer_match.group(3).strip() if reviewer_match.group(3) else ""
            
            # Remove reviewer info from review text
            clean_review = clean_review[:reviewer_match.start()].strip()
        
        # Extract variant info (pattern: "(Variant: ...)")
        variant_info = ""
        variant_pattern = r'\(Variant:\s*([^)]+)\)'
        variant_match = re.search(variant_pattern, clean_review)
        
        if variant_match:
            variant_info = variant_match.group(1).strip()
            # Remove variant info from review text
            clean_review = re.sub(variant_pattern, '', clean_review).strip()
        
        # Check for images
        has_images = "includes product photos" in review.lower() or "review includes" in review.lower()
        
        # Clean the final review text
        clean_review = self.clean_text(clean_review)
        
        return {
            'rating': rating,
            'review_text': clean_review,
            'reviewer_name': self.clean_text(reviewer_name),
            'reviewer_location': self.clean_text(reviewer_location),
            'review_date': self.clean_text(review_date),
            'variant_info': self.clean_text(variant_info),
            'has_images': has_images
        }
    
    def export_scraped_data(self, scraped_data: Dict[str, Any], source: str, product_id: str = None) -> str:
        """
        Export scraped data to CSV
        
        Args:
            scraped_data (Dict): Data returned from scraper
            source (str): Source platform (target, aliexpress, trendyol)
            product_id (str): Product ID for filename
            
        Returns:
            str: Path to exported CSV file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Generate filename
        if product_id:
            filename = f"{source}_reviews_{product_id}_{timestamp}.csv"
        else:
            filename = f"{source}_reviews_{timestamp}.csv"
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            # Extract basic product info
            product_info = {
                'product_name': scraped_data.get('product_name', 'Unknown Product'),
                'product_image': scraped_data.get('product_image', ''),
                'product_rating': scraped_data.get('rating', 0),
                'review_count': scraped_data.get('review_count', 0),
                'source': source,
                'product_link': scraped_data.get('product_link', ''),
                'scraping_timestamp': timestamp
            }
            
            # Get comments/reviews
            comments = scraped_data.get('comments', [])
            
            # Convert numpy array to list if needed
            if isinstance(comments, np.ndarray):
                comments = comments.tolist()
            
            # Define CSV headers
            headers = [
                'product_name', 'source', 'product_rating', 'review_count',
                'review_index', 'individual_rating', 'review_text',
                'reviewer_name', 'reviewer_location', 'review_date',
                'variant_info', 'has_images', 'product_image', 'product_link',
                'scraping_timestamp'
            ]
            
            # Add rating distribution headers if available
            if 'rating_distribution' in scraped_data and scraped_data['rating_distribution']:
                for star_level in ['1', '2', '3', '4', '5']:
                    headers.append(f'rating_distribution_{star_level}_star')
            
            # Add other optional headers
            if 'recommended_percentage' in scraped_data:
                headers.append('recommended_percentage')
            
            if 'reviews_with_images_count' in scraped_data:
                headers.append('reviews_with_images_count')
            
            # Open CSV file for writing
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                
                # If no comments, create a single row with product info
                if not comments or len(comments) == 0:
                    row = {
                        **product_info,
                        'review_index': 0,
                        'individual_rating': None,
                        'review_text': 'No reviews available',
                        'reviewer_name': '',
                        'reviewer_location': '',
                        'review_date': '',
                        'variant_info': '',
                        'has_images': False
                    }
                    
                    # Add rating distribution data
                    if 'rating_distribution' in scraped_data and scraped_data['rating_distribution']:
                        rating_dist = scraped_data['rating_distribution']
                        for star_level in ['1', '2', '3', '4', '5']:
                            row[f'rating_distribution_{star_level}_star'] = rating_dist.get(star_level, 0)
                    
                    # Add other optional data
                    if 'recommended_percentage' in scraped_data:
                        row['recommended_percentage'] = scraped_data['recommended_percentage']
                    
                    if 'reviews_with_images_count' in scraped_data:
                        row['reviews_with_images_count'] = scraped_data['reviews_with_images_count']
                    
                    writer.writerow(row)
                else:
                    # Process each review
                    for idx, review in enumerate(comments):
                        # Parse the review
                        parsed_review = self.parse_review_text(str(review))
                        
                        # Create row with all info
                        row = {
                            **product_info,
                            'review_index': idx + 1,
                            'individual_rating': parsed_review['rating'],
                            'review_text': parsed_review['review_text'],
                            'reviewer_name': parsed_review['reviewer_name'],
                            'reviewer_location': parsed_review['reviewer_location'],
                            'review_date': parsed_review['review_date'],
                            'variant_info': parsed_review['variant_info'],
                            'has_images': parsed_review['has_images']
                        }
                        
                        # Add rating distribution data
                        if 'rating_distribution' in scraped_data and scraped_data['rating_distribution']:
                            rating_dist = scraped_data['rating_distribution']
                            for star_level in ['1', '2', '3', '4', '5']:
                                row[f'rating_distribution_{star_level}_star'] = rating_dist.get(star_level, 0)
                        
                        # Add other optional data
                        if 'recommended_percentage' in scraped_data:
                            row['recommended_percentage'] = scraped_data['recommended_percentage']
                        
                        if 'reviews_with_images_count' in scraped_data:
                            row['reviews_with_images_count'] = scraped_data['reviews_with_images_count']
                        
                        writer.writerow(row)
            
            total_rows = len(comments) if comments else 1
            logger.info(f"Successfully exported {total_rows} rows to {filepath}")
            logger.info(f"Product: {product_info['product_name']}")
            logger.info(f"Total reviews: {len(comments) if comments else 0}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {str(e)}")
            raise e
    
    def export_product_summary(self, scraped_data: Dict[str, Any], source: str, product_id: str = None) -> str:
        """
        Export product summary to CSV (one row per product)
        
        Args:
            scraped_data (Dict): Data returned from scraper
            source (str): Source platform
            product_id (str): Product ID
            
        Returns:
            str: Path to exported summary CSV
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if product_id:
            filename = f"{source}_product_summary_{product_id}_{timestamp}.csv"
        else:
            filename = f"{source}_product_summary_{timestamp}.csv"
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            # Get comments for analysis
            comments = scraped_data.get('comments', [])
            if isinstance(comments, np.ndarray):
                comments = comments.tolist()
            
            # Analyze reviews
            total_reviews = len(comments) if comments else 0
            reviews_with_rating = 0
            rating_sum = 0
            
            if comments:
                for review in comments:
                    parsed = self.parse_review_text(str(review))
                    if parsed['rating']:
                        reviews_with_rating += 1
                        rating_sum += parsed['rating']
            
            avg_individual_rating = rating_sum / reviews_with_rating if reviews_with_rating > 0 else None
            
            # Create summary row
            summary = {
                'product_name': scraped_data.get('product_name', 'Unknown Product'),
                'source': source,
                'product_id': product_id or 'Unknown',
                'product_link': scraped_data.get('product_link', ''),
                'product_image': scraped_data.get('product_image', ''),
                'official_rating': scraped_data.get('rating', 0),
                'official_review_count': scraped_data.get('review_count', 0),
                'scraped_review_count': total_reviews,
                'reviews_with_individual_rating': reviews_with_rating,
                'avg_individual_rating': round(avg_individual_rating, 2) if avg_individual_rating else None,
                'recommended_percentage': scraped_data.get('recommended_percentage'),
                'reviews_with_images_count': scraped_data.get('reviews_with_images_count'),
                'scraping_timestamp': timestamp
            }
            
            # Add rating distribution
            if 'rating_distribution' in scraped_data and scraped_data['rating_distribution']:
                rating_dist = scraped_data['rating_distribution']
                for star_level in ['1', '2', '3', '4', '5']:
                    summary[f'rating_distribution_{star_level}_star'] = rating_dist.get(star_level, 0)
            
            # Define headers
            headers = list(summary.keys())
            
            # Create CSV file
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                writer.writerow(summary)
            
            logger.info(f"Successfully exported product summary to {filepath}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting product summary: {str(e)}")
            raise e
    
    def export_multiple_products(self, products_data: List[Dict[str, Any]], filename_prefix: str = "multi_product") -> str:
        """
        Export multiple products to a single CSV file
        
        Args:
            products_data (List[Dict]): List of scraped product data
            filename_prefix (str): Prefix for filename
            
        Returns:
            str: Path to exported CSV file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_summary_{timestamp}.csv"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            all_summaries = []
            
            for product_data in products_data:
                # Extract source and product ID if available
                source = product_data.get('source', 'unknown')
                product_id = product_data.get('product_id', 'unknown')
                
                # Get comments for analysis
                comments = product_data.get('comments', [])
                if isinstance(comments, np.ndarray):
                    comments = comments.tolist()
                
                total_reviews = len(comments) if comments else 0
                
                summary = {
                    'product_name': product_data.get('product_name', 'Unknown Product'),
                    'source': source,
                    'product_id': product_id,
                    'product_link': product_data.get('product_link', ''),
                    'official_rating': product_data.get('rating', 0),
                    'official_review_count': product_data.get('review_count', 0),
                    'scraped_review_count': total_reviews,
                    'recommended_percentage': product_data.get('recommended_percentage'),
                    'scraping_timestamp': timestamp
                }
                
                all_summaries.append(summary)
            
            if all_summaries:
                # Define headers from the first summary
                headers = list(all_summaries[0].keys())
                
                # Create CSV file
                with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=headers)
                    writer.writeheader()
                    writer.writerows(all_summaries)
            
            logger.info(f"Successfully exported {len(all_summaries)} products to {filepath}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting multiple products: {str(e)}")
            raise e

# Global CSV exporter instance
csv_exporter = None

def get_csv_exporter(output_dir: str = "exports") -> CSVExporter:
    """
    Get or create CSV exporter instance
    
    Args:
        output_dir (str): Directory for CSV exports
        
    Returns:
        CSVExporter: Configured CSV exporter
    """
    global csv_exporter
    
    if csv_exporter is None:
        csv_exporter = CSVExporter(output_dir=output_dir)
    
    return csv_exporter 