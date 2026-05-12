"""
MinIO/S3 Utility Functions
Helper functions for MinIO and S3 operations
"""

import re
from typing import List, Tuple


def validate_bucket_name(bucket_name: str) -> Tuple[bool, List[str]]:
    """
    Validate bucket name according to S3/MinIO naming conventions
    
    AWS S3 Bucket naming rules:
    - Must be between 3 and 63 characters long
    - Can contain only lowercase letters, numbers, and hyphens
    - Cannot contain uppercase characters or underscores
    - Cannot start or end with a hyphen
    - Cannot have consecutive hyphens
    - Must not be formatted as an IP address (e.g., 192.168.1.1)
    
    Args:
        bucket_name: The bucket name to validate
        
    Returns:
        Tuple of (is_valid: bool, errors: List[str])
        - is_valid: True if the bucket name is valid
        - errors: List of specific validation errors (empty if valid)
    """
    errors = []
    
    # Check if bucket_name is provided
    if not bucket_name:
        errors.append("Bucket name cannot be empty")
        return False, errors
    
    # Check length (3-63 characters)
    if len(bucket_name) < 3:
        errors.append("Bucket name must be at least 3 characters long")
    elif len(bucket_name) > 63:
        errors.append("Bucket name cannot exceed 63 characters")
    
    # Check for valid characters (lowercase letters, numbers, hyphens only)
    if not re.match(r'^[a-z0-9-]+$', bucket_name):
        invalid_chars = set(char for char in bucket_name if not re.match(r'[a-z0-9-]', char))
        if invalid_chars:
            errors.append(f"Bucket name contains invalid characters: {', '.join(sorted(invalid_chars))}. Only lowercase letters, numbers, and hyphens are allowed")
    
    # Check for uppercase letters specifically (common mistake)
    if any(char.isupper() for char in bucket_name):
        errors.append("Bucket name cannot contain uppercase letters")
    
    # Check for underscores specifically (common mistake)
    if '_' in bucket_name:
        errors.append("Bucket name cannot contain underscores. Use hyphens (-) instead")
    
    # Check start/end with hyphen
    if bucket_name.startswith('-'):
        errors.append("Bucket name cannot start with a hyphen")
    if bucket_name.endswith('-'):
        errors.append("Bucket name cannot end with a hyphen")
    
    # Check for consecutive hyphens
    if '--' in bucket_name:
        errors.append("Bucket name cannot contain consecutive hyphens")
    
    # Check if it looks like an IP address
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ip_pattern, bucket_name):
        errors.append("Bucket name cannot be formatted as an IP address")
    
    # Check for dots (not recommended for SSL/TLS)
    if '.' in bucket_name:
        errors.append("Bucket name should not contain dots (.) as they can cause SSL/TLS certificate issues")
    
    is_valid = len(errors) == 0
    return is_valid, errors


def suggest_valid_bucket_name(bucket_name: str) -> str:
    """
    Suggest a valid bucket name based on an invalid one
    
    Args:
        bucket_name: The invalid bucket name
        
    Returns:
        A suggested valid bucket name
    """
    if not bucket_name:
        return "my-bucket"
    
    # Convert to lowercase
    suggested = bucket_name.lower()
    
    # Replace underscores with hyphens
    suggested = suggested.replace('_', '-')
    
    # Remove invalid characters (keep only lowercase letters, numbers, hyphens)
    suggested = re.sub(r'[^a-z0-9-]', '', suggested)
    
    # Remove consecutive hyphens
    suggested = re.sub(r'-+', '-', suggested)
    
    # Remove leading/trailing hyphens
    suggested = suggested.strip('-')
    
    # Ensure minimum length
    if len(suggested) < 3:
        suggested = f"{suggested}-bucket"
    
    # Ensure maximum length
    if len(suggested) > 63:
        suggested = suggested[:63].rstrip('-')
    
    # Final validation to ensure it's not empty after cleaning
    if not suggested:
        suggested = "my-bucket"
    
    return suggested


def validate_and_suggest_bucket_name(bucket_name: str) -> dict:
    """
    Validate bucket name and provide suggestions if invalid
    
    Args:
        bucket_name: The bucket name to validate
        
    Returns:
        Dictionary with validation results and suggestions
    """
    is_valid, errors = validate_bucket_name(bucket_name)
    
    result = {
        "original_name": bucket_name,
        "is_valid": is_valid,
        "errors": errors
    }
    
    if not is_valid:
        result["suggested_name"] = suggest_valid_bucket_name(bucket_name)
        # Validate the suggestion
        suggestion_valid, suggestion_errors = validate_bucket_name(result["suggested_name"])
        result["suggestion_is_valid"] = suggestion_valid
        if not suggestion_valid:
            result["suggestion_errors"] = suggestion_errors
    
    return result


def format_bucket_validation_error_message(bucket_name: str) -> str:
    """
    Format a user-friendly error message for bucket name validation
    
    Args:
        bucket_name: The invalid bucket name
        
    Returns:
        Formatted error message with suggestions
    """
    result = validate_and_suggest_bucket_name(bucket_name)
    
    if result["is_valid"]:
        return f"[VALID] Bucket name '{bucket_name}' is valid"
    
    error_msg = f"[ERROR] Invalid bucket name '{bucket_name}':\n"
    for error in result["errors"]:
        error_msg += f"  • {error}\n"
    
    if "suggested_name" in result:
        if result.get("suggestion_is_valid", False):
            error_msg += f"\n[HINT] Suggested valid name: '{result['suggested_name']}'"
        else:
            error_msg += f"\n[WARN] Could not generate a valid suggestion from '{bucket_name}'"
            error_msg += f"\n[HINT] Try a name like: 'my-app-files' or 'user-data-bucket'"
    
    return error_msg


def get_bucket_naming_guidelines() -> str:
    """
    Get a formatted string with bucket naming guidelines
    
    Returns:
        String with bucket naming rules and examples
    """
    guidelines = """
📋 S3/MinIO Bucket Naming Guidelines:

[VALID] ALLOWED:
  • Lowercase letters (a-z)
  • Numbers (0-9)  
  • Hyphens (-) in the middle
  • Length: 3-63 characters

[INVALID] NOT ALLOWED:
  • Uppercase letters (A-Z)
  • Underscores (_) 
  • Starting or ending with hyphen
  • Consecutive hyphens (--)
  • Dots (.) - causes SSL issues
  • Special characters (!@#$%^&*)
  • IP address format (192.168.1.1)

[VALID] GOOD EXAMPLES:
  • my-app-files
  • user-data-2024
  • chatgpt-uploads
  • company-documents

[INVALID] BAD EXAMPLES:
  • My_App_Files (uppercase & underscores)
  • user_data (underscore)
  • -files (starts with hyphen)
  • files- (ends with hyphen)
  • my--bucket (consecutive hyphens)
  • app.files (contains dot)
    """
    return guidelines.strip()


# Example usage and testing
if __name__ == "__main__":
    # Test cases
    test_names = [
        "minio_files",  # Your problematic bucket name
        "minio-files",  # Fixed version
        "My_App_Files", # Multiple issues
        "valid-bucket-name",  # Valid
        "a",  # Too short
        "-invalid",  # Starts with hyphen
        "invalid-",  # Ends with hyphen
        "192.168.1.1",  # IP address format
        "app.bucket.name",  # Contains dots
        "very-long-bucket-name-that-exceeds-the-maximum-allowed-length-of-sixty-three-characters",  # Too long
    ]
    
    print("🧪 Testing Bucket Name Validation:\n")
    
    for name in test_names:
        print(f"Testing: '{name}'")
        print(format_bucket_validation_error_message(name))
        print("-" * 60)
