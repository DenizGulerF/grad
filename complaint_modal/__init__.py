"""
Complaint Analysis Module

This module provides advanced complaint analysis capabilities using zero-shot classification.
It includes functions for analyzing customer complaints in product reviews and categorizing
them into specific complaint types.
"""

# Make key functions available at package level
try:
    from .complaint_categories_zeroshot import extract_complaints_zeroshot, COMPLAINT_LABELS
    from .inference import (
        predict_rating_and_complaints, 
        count_complaints_by_category, 
        get_top_complaints_zeroshot
    )
    
    __all__ = [
        'extract_complaints_zeroshot',
        'COMPLAINT_LABELS',
        'predict_rating_and_complaints',
        'count_complaints_by_category',
        'get_top_complaints_zeroshot'
    ]
    
except ImportError as e:
    print(f"Warning: Some complaint analysis features may not be available: {e}")
    __all__ = []

__version__ = "1.0.0" 