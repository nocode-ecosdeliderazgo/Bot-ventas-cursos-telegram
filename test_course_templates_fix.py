#!/usr/bin/env python3
"""
Test script to validate the course templates fix.
Tests the conversion of database field types to proper display values.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.utils.course_templates import CourseTemplates

def test_course_templates_with_string_data():
    """Test templates with string data types like those coming from database."""
    
    # Simulate database data where numeric fields are stored as strings
    course_details = {
        'name': 'Experto en IA con GPT y Gemini',
        'short_description': 'Aprende a dominar las herramientas de IA más poderosas',
        'total_duration_min': '480',  # String instead of int
        'level': 'intermedio',
        'price': '297.00',  # String instead of float
        'currency': 'USD',
        'session_count': '12',  # String instead of int
        'sessions': [
            {'title': 'Introducción a ChatGPT'},
            {'title': 'Prompts Avanzados'},
            {'title': 'Automatización con IA'}
        ]
    }
    
    print("🧪 Testing course templates with string data types...")
    print("=" * 60)
    
    # Test format_course_info
    print("1. Testing format_course_info():")
    result = CourseTemplates.format_course_info(course_details)
    print(result)
    print()
    
    # Verify that "dato no encontrado" is not present
    if "dato no encontrado" in result.lower():
        print("❌ FAILED: Still showing 'dato no encontrado'")
        return False
    else:
        print("✅ SUCCESS: No 'dato no encontrado' found")
    
    # Test format_course_summary
    print("2. Testing format_course_summary():")
    result = CourseTemplates.format_course_summary(course_details)
    print(result)
    print()
    
    if "dato no encontrado" in result.lower():
        print("❌ FAILED: Still showing 'dato no encontrado'")
        return False
    else:
        print("✅ SUCCESS: No 'dato no encontrado' found")
    
    # Test format_course_details_with_benefits
    print("3. Testing format_course_details_with_benefits():")
    result = CourseTemplates.format_course_details_with_benefits(course_details)
    print(result)
    print()
    
    if "dato no encontrado" in result.lower():
        print("❌ FAILED: Still showing 'dato no encontrado'")
        return False
    else:
        print("✅ SUCCESS: No 'dato no encontrado' found")
    
    return True

def test_course_templates_with_empty_data():
    """Test templates with empty/null data."""
    
    course_details = {
        'name': None,
        'short_description': '',
        'total_duration_min': None,
        'level': '',
        'price': '',
        'currency': 'USD',
        'session_count': None,
        'sessions': []
    }
    
    print("\n🧪 Testing course templates with empty/null data...")
    print("=" * 60)
    
    # Test format_course_info
    print("1. Testing format_course_info() with empty data:")
    result = CourseTemplates.format_course_info(course_details)
    print(result)
    print()
    
    # Should show fallback text
    if "dato no encontrado" in result.lower():
        print("✅ SUCCESS: Shows fallback text for empty data")
    else:
        print("❌ FAILED: Should show fallback text for empty data")
        return False
    
    return True

def test_course_templates_with_invalid_data():
    """Test templates with invalid data types."""
    
    course_details = {
        'name': 'Test Course',
        'short_description': 'Test Description',
        'total_duration_min': 'invalid_number',  # Invalid string
        'level': 'beginner',
        'price': 'not_a_number',  # Invalid string
        'currency': 'USD',
        'session_count': 'not_a_number',  # Invalid string
        'sessions': [
            {'title': 'Test Session'}
        ]
    }
    
    print("\n🧪 Testing course templates with invalid data types...")
    print("=" * 60)
    
    # Test format_course_info
    print("1. Testing format_course_info() with invalid data:")
    result = CourseTemplates.format_course_info(course_details)
    print(result)
    print()
    
    # Should handle invalid data gracefully
    if "dato no encontrado" in result.lower():
        print("✅ SUCCESS: Handles invalid data gracefully")
    else:
        print("❌ FAILED: Should handle invalid data gracefully")
        return False
    
    return True

if __name__ == "__main__":
    print("🔧 Testing Course Templates Fix")
    print("=" * 60)
    
    success = True
    
    # Test 1: String data types
    success &= test_course_templates_with_string_data()
    
    # Test 2: Empty data
    success &= test_course_templates_with_empty_data()
    
    # Test 3: Invalid data
    success &= test_course_templates_with_invalid_data()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Course templates are now robust against different data types")
    else:
        print("❌ SOME TESTS FAILED")
        print("🔧 Additional fixes may be needed")
    
    sys.exit(0 if success else 1)