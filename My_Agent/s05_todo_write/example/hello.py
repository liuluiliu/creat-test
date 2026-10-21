"""
A simple greeting module demonstrating best practices.

This module provides functions for generating personalized greetings
and can be run as a script or imported as a module.
"""

from typing import List


def greet(name: str, greeting: str = "Hello") -> str:
    """
    Generate a personalized greeting message.
    
    Args:
        name: The name of the person to greet
        greeting: The greeting word to use (default: "Hello")
    
    Returns:
        A formatted greeting string
    
    Examples:
        >>> greet("Alice")
        'Hello, Alice!'
        >>> greet("Bob", "Hi")
        'Hi, Bob!'
    """
    return f"{greeting}, {name}!"


def greet_multiple(names: List[str], greeting: str = "Hello") -> List[str]:
    """
    Generate greeting messages for multiple people.
    
    Args:
        names: A list of names to greet
        greeting: The greeting word to use (default: "Hello")
    
    Returns:
        A list of formatted greeting strings
    """
    return [greet(name, greeting) for name in names]


def main() -> None:
    """
    Main entry point for the script.
    
    Demonstrates the greeting functions with sample data.
    """
    print(greet("World"))
    print(greet("Python", "Welcome to"))
    
    people = ["Alice", "Bob", "Charlie"]
    greetings = greet_multiple(people)
    
    print("\nGreeting multiple people:")
    for message in greetings:
        print(f"  {message}")


if __name__ == "__main__":
    main()
