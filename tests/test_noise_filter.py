"""
Unit tests for the Advanced Noise & Artifact Filter.
Validates contact info, regulatory text, branding headers, entropy/gibberish, and canonical food normalizations.
"""

import pytest
from src.noise_filter import AdvancedNoiseFilter


@pytest.fixture
def filter_engine():
    return AdvancedNoiseFilter()


def test_contact_and_metadata_noise_filtering(filter_engine):
    noise_samples = [
        "FASTFOODRESTAURANT.SITE.COM",
        "www.bestpizza.com",
        "info@restaurant.com",
        "+1 (555) 123-4567",
        "GSTIN: 27AADCB2230M1ZT",
        "All prices exclusive of 5% GST and 10% Service Charge",
        "Opening Hours: Mon-Sat 10:00 AM - 11:00 PM",
        "Free Home Delivery on orders above $20",
        "Table No: 14",
    ]
    for sample in noise_samples:
        assert filter_engine.is_metadata_or_business_noise(sample), f"Failed to filter metadata noise: {sample}"


def test_branding_and_decorative_noise_filtering(filter_engine):
    branding_samples = [
        "FAST FOOD MENU",
        "RESTAURANT",
        "OUR MENU",
        "XX",
        "***",
        "===",
        "Delicious & Tasty",
        "Your Logo Here",
    ]
    for sample in branding_samples:
        assert filter_engine.is_branding_or_decorative_noise(sample), f"Failed to filter branding noise: {sample}"


def test_gibberish_and_low_entropy_filtering(filter_engine):
    gibberish_samples = [
        "zxcvb",
        "XXXXX",
        "qrtsd",
        "X",
        "-",
    ]
    for sample in gibberish_samples:
        assert filter_engine.is_gibberish_or_low_entropy(sample), f"Failed to filter gibberish noise: {sample}"


def test_culinary_semantic_relevance_validation(filter_engine):
    food_samples = [
        "Cheese Burger",
        "Spicy Chicken Burger",
        "Steamed Edamame",
        "Palak Paneer",
        "Milkshake",
        "Orange Juice",
        "Hot Dog",
        "French Fries",
    ]
    for food in food_samples:
        assert filter_engine.has_culinary_semantic_relevance(food), f"Culinary vocabulary missed: {food}"

    non_food_samples = [
        "FASTFOODRESTAURANT",
        "TERMS & CONDITIONS",
        "FLOOR 2 MAIN ROAD",
    ]
    for non_food in non_food_samples:
        assert not filter_engine.has_culinary_semantic_relevance(non_food), f"Incorrectly marked as food: {non_food}"


def test_canonical_food_normalization(filter_engine):
    test_cases = [
        ("French Friea", "French Fries"),
        ("Dog", "Hot Dog"),
        ("Cheese Cake", "Cheesecake"),
        ("Ice Tea", "Iced Tea"),
        ("ohicken tikka", "Chicken tikka"),
        ("panner masala", "Paneer masala"),
    ]
    for raw, expected in test_cases:
        cleaned = filter_engine.clean_and_normalize_food_name(raw)
        assert cleaned.lower() == expected.lower(), f"Expected '{expected}', got '{cleaned}' from '{raw}'"


def test_master_should_filter_decision(filter_engine):
    # Unpriced noise -> should filter
    assert filter_engine.should_filter_out("FAST FOOD MENU XX", has_price=False, is_in_section=False)
    assert filter_engine.should_filter_out("FASTFOODRESTAURANT.SITE.COM", has_price=False, is_in_section=False)
    assert filter_engine.should_filter_out("XX", has_price=False, is_in_section=False)

    # Authentic priced item -> should preserve
    assert not filter_engine.should_filter_out("Hot Dog", has_price=True, is_in_section=True)
    assert not filter_engine.should_filter_out("Cheese Burger", has_price=True, is_in_section=True)
