# Complaint Analysis Integration

This document describes the new complaint analysis features that have been integrated with the existing sentiment analysis system.

## Overview

The complaint analysis system uses advanced zero-shot classification with transformer models to automatically categorize and analyze customer complaints from product reviews. It works alongside the existing sentiment analysis to provide deeper insights into customer dissatisfaction.

## Features

### 🔍 **Automatic Complaint Detection**
- Uses Facebook's BART-large-mnli model for zero-shot classification
- Identifies complaints without requiring specific training data
- Works with any product review text

### 📊 **8 Complaint Categories**
1. **Material Quality** - Issues with build quality, durability, manufacturing
2. **Sound Quality** - Audio-related problems (for audio products)
3. **Battery Life** - Battery performance and charging issues
4. **Comfort/Fit** - Physical comfort and ergonomic issues
5. **Connectivity** - Bluetooth, wireless, and connection problems
6. **Shipping/Delivery** - Packaging, delivery, and logistics issues
7. **Price/Value** - Pricing concerns and value for money
8. **Customer Service** - Support and service-related complaints

### 🤖 **AI-Powered Analysis**
- ML-based rating prediction using ensemble models
- Confidence scoring for each complaint category
- Individual complaint analysis per review
- Aggregated complaint statistics across all reviews

## API Endpoints

### 1. **Enhanced Sentiment Analysis** 
```
POST /api/analyze-reviews
```
Now includes complaint analysis in the response along with traditional sentiment analysis.

**Request:**
```json
{
  "reviews": ["Review text 1", "Review text 2"],
  "product_info": {
    "name": "Product Name",
    "image": "https://example.com/image.jpg"
  }
}
```

**Response includes:**
```json
{
  "complaint_analysis": {
    "advanced_analysis_available": true,
    "top_complaints": [
      ["sound_quality", 5, "Issues related to audio performance"],
      ["battery_life", 3, "Issues related to battery performance"]
    ],
    "complaint_counts_by_category": {
      "sound_quality": 5,
      "battery_life": 3,
      "material_quality": 2
    },
    "total_complaint_mentions": 10,
    "ml_predicted_ratings": [1, 2, 5, 4, 3]
  }
}
```

### 2. **Detailed Complaint Analysis**
```
GET /api/complaint-analysis/{retailer}/{product_id}
```
Get comprehensive complaint analysis for a specific product.

**Response:**
```json
{
  "product_info": {...},
  "total_reviews": 50,
  "top_complaints": [...],
  "complaint_counts_by_category": {...},
  "individual_complaints": [
    {
      "review_index": 0,
      "review_text": "Review text...",
      "complaints": {
        "sound_quality": {
          "score": 0.85,
          "description": "Poor sound, muffled, distortion..."
        }
      },
      "predicted_rating": 2
    }
  ],
  "average_predicted_rating": 3.2
}
```

### 3. **Available Categories**
```
GET /api/complaints/categories
```
Get all available complaint categories and their descriptions.

### 4. **Text Analysis**
```
POST /api/complaints/analyze-text
```
Analyze complaints in a single text snippet.

**Request:**
```json
{
  "text": "The sound quality is terrible and battery dies quickly",
  "threshold": 0.5
}
```

## Integration with Existing Features

### **Backwards Compatibility**
- All existing endpoints continue to work unchanged
- New complaint analysis is added as additional data
- Fallback mechanisms ensure the system works even if complaint analysis fails

### **Enhanced Scraping**
- Target, Trendyol, and AliExpress scrapers now include complaint analysis
- Results are automatically saved to the database with complaint insights
- Web interface shows both sentiment and complaint analysis

### **Database Storage**
- Complaint analysis results are stored alongside sentiment analysis
- Historical complaint trends can be tracked
- Product comparison based on complaint patterns

## Technical Implementation

### **Zero-Shot Classification**
```python
from complaint_modal.complaint_categories_zeroshot import extract_complaints_zeroshot

# Analyze a single review
complaints = extract_complaints_zeroshot(review_text, threshold=0.5)
```

### **Bulk Analysis**
```python
from complaint_modal.inference import predict_rating_and_complaints

# Analyze multiple reviews
ratings, top_complaints = predict_rating_and_complaints(review_list)
```

### **GPU Support**
- Automatically detects and uses GPU if available
- Falls back to CPU for broader compatibility
- Significantly faster inference with GPU acceleration

## Setup and Installation

### **Dependencies**
The following new dependencies are required:
```
torch==2.1.0
transformers==4.34.0
```

### **Installation**
```bash
pip install -r requirements.txt
```

### **First Run**
On first run, the system will download the BART model (~1.6GB). This only happens once and the model is cached locally.

## Testing

Run the integration test to verify everything is working:

```bash
python test_complaint_integration.py
```

This will test:
- Enhanced sentiment analysis with complaint detection
- Complaint categories endpoint
- Text analysis endpoint

## Performance Considerations

### **Model Loading**
- Models are loaded once at startup
- GPU detection happens automatically
- Expect 10-30 seconds initial load time for transformer models

### **Inference Speed**
- **CPU**: ~1-2 seconds per review
- **GPU**: ~0.1-0.3 seconds per review
- Batch processing is more efficient for multiple reviews

### **Memory Usage**
- **CPU**: ~2-4GB RAM
- **GPU**: ~2-6GB VRAM
- Consider batch size limits for large review sets

## Examples

### **High-Level Usage**
```python
# The sentiment service now automatically includes complaint analysis
analysis = sentiment_service.analyze_reviews(reviews, product_info)

# Check if complaint analysis is available
if analysis['complaint_analysis']['advanced_analysis_available']:
    top_complaints = analysis['complaint_analysis']['top_complaints']
    for category, count, description in top_complaints:
        print(f"{category}: {count} mentions")
```

### **Direct Complaint Analysis**
```python
# Analyze complaints in specific text
complaints = extract_complaints_zeroshot(
    "The sound is muffled and the battery dies in 2 hours", 
    threshold=0.6
)
print(complaints)
# Output: {'sound_quality': {'score': 0.89, 'description': '...'}, 
#          'battery_life': {'score': 0.92, 'description': '...'}}
```

## Troubleshooting

### **Common Issues**

1. **Model Download Fails**
   - Check internet connection
   - Ensure sufficient disk space (~2GB)
   - Try running with verbose logging

2. **GPU Not Detected**
   - Verify CUDA installation
   - Check PyTorch GPU support: `torch.cuda.is_available()`
   - System will automatically fall back to CPU

3. **Out of Memory**
   - Reduce batch size
   - Process reviews in smaller chunks
   - Consider using CPU instead of GPU

### **Fallback Behavior**
If complaint analysis fails:
- System continues with keyword-based sentiment analysis
- Error is logged but doesn't break the application
- `advanced_analysis_available` will be `false` in the response

## Future Enhancements

- [ ] Custom complaint categories for specific product types
- [ ] Temporal complaint trend analysis
- [ ] Multi-language complaint detection
- [ ] Integration with product recommendation systems
- [ ] Real-time complaint monitoring and alerts 