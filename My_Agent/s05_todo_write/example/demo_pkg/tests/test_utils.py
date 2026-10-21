"""Tests for utils module."""

import unittest
from demo_pkg.utils import greet, add_numbers, multiply_numbers


class TestGreet(unittest.TestCase):
    """Test cases for greet function."""
    
    def test_greet_simple_name(self):
        """Test greeting with a simple name."""
        result = greet("Alice")
        self.assertEqual(result, "Hello, Alice!")
    
    def test_greet_empty_string(self):
        """Test greeting with empty string."""
        result = greet("")
        self.assertEqual(result, "Hello, !")


class TestAddNumbers(unittest.TestCase):
    """Test cases for add_numbers function."""
    
    def test_add_positive_numbers(self):
        """Test adding two positive numbers."""
        result = add_numbers(3, 5)
        self.assertEqual(result, 8)
    
    def test_add_negative_numbers(self):
        """Test adding two negative numbers."""
        result = add_numbers(-3, -5)
        self.assertEqual(result, -8)
    
    def test_add_mixed_numbers(self):
        """Test adding positive and negative numbers."""
        result = add_numbers(10, -3)
        self.assertEqual(result, 7)
    
    def test_add_floats(self):
        """Test adding floating point numbers."""
        result = add_numbers(2.5, 3.7)
        self.assertAlmostEqual(result, 6.2, places=1)


class TestMultiplyNumbers(unittest.TestCase):
    """Test cases for multiply_numbers function."""
    
    def test_multiply_positive_numbers(self):
        """Test multiplying two positive numbers."""
        result = multiply_numbers(3, 4)
        self.assertEqual(result, 12)
    
    def test_multiply_by_zero(self):
        """Test multiplying by zero."""
        result = multiply_numbers(5, 0)
        self.assertEqual(result, 0)
    
    def test_multiply_negative_numbers(self):
        """Test multiplying two negative numbers."""
        result = multiply_numbers(-3, -4)
        self.assertEqual(result, 12)
    
    def test_multiply_floats(self):
        """Test multiplying floating point numbers."""
        result = multiply_numbers(2.5, 4.0)
        self.assertEqual(result, 10.0)


if __name__ == "__main__":
    unittest.main()
