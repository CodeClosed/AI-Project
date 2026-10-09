"""
Unit and integration test suite for ExtractionValidator.
Tests all required anti-hallucination scenarios:
1. Perfect match
2. Formatting differences
3. Multi-line OCR combinations
4. OCR typo tolerance
5. Partial match (FLAG)
6. Hallucination rejection
7. Random / non-food text rejection
8. Price contamination stripping
9. Safe deduplication
10. OCR failure / degraded mode handling
11. End-to-end RecognizedMenu validation
"""

import pytest
from src.models import TextBlock, BoundingBox, MenuItem, MenuSection, RecognizedMenu
from src.extraction_validator import ExtractionValidator, ValidationResult


@pytest.fixture
def validator():
    return ExtractionValidator(
        accept_threshold=80.0,
        flag_threshold=50.0,
        enable_second_pass=False,
    )


def test_1_perfect_match(validator):
    """Test 1: Perfect Match (Gemini: Chicken Burger, OCR: Chicken Burger -> ACCEPT)"""
    ocr_evidence = ["chicken burger", "french fries"]
    res: ValidationResult = validator.validate_item(
        item_name="Chicken Burger",
        ocr_candidates=ocr_evidence,
        price=10.0,
    )
    assert res.status == "accepted"
    assert res.similarity_score >= 95.0
    assert res.confidence >= 0.85
    assert "chicken burger" in res.best_match_text.lower()


def test_2_formatting_difference(validator):
    """Test 2: Formatting Difference (Gemini: Chicken Burger, OCR: CHICKEN-BURGER -> ACCEPT)"""
    ocr_raw = ["CHICKEN-BURGER", "FRENCH_FRIES"]
    cleaned = validator.clean_ocr_evidence(ocr_raw)
    res: ValidationResult = validator.validate_item(
        item_name="Chicken Burger",
        ocr_candidates=cleaned,
        price=8.5,
    )
    assert res.status == "accepted"
    assert res.similarity_score >= 95.0
    assert res.confidence >= 0.85


def test_3_multi_line_ocr(validator):
    """Test 3: Multi-Line OCR (Gemini: Chicken Butter Masala, OCR: ['Chicken Butter', 'Masala 250'] -> ACCEPT)"""
    ocr_lines = ["Chicken Butter", "Masala 250", "Cold Coffee"]
    cleaned = validator.clean_ocr_evidence(ocr_lines)
    candidates = validator.generate_multi_line_candidates(cleaned, max_window=3)

    res: ValidationResult = validator.validate_item(
        item_name="Chicken Butter Masala",
        ocr_candidates=candidates,
        price=250.0,
    )
    assert res.status == "accepted"
    assert res.similarity_score >= 90.0
    assert "chicken butter masala" in res.best_match_text.lower()


def test_4_ocr_typo(validator):
    """Test 4: OCR Typo (Gemini: Paneer Tikka, OCR: Paneer Tika -> ACCEPT / high score)"""
    ocr_lines = validator.clean_ocr_evidence(["Paneer Tika", "Garlic Naan"])
    res: ValidationResult = validator.validate_item(
        item_name="Paneer Tikka",
        ocr_candidates=ocr_lines,
        price=180.0,
    )
    assert res.status in ("accepted", "flagged")
    assert res.similarity_score >= 80.0


def test_5_partial_match(validator):
    """Test 5: Partial Match (Gemini: Chicken Tikka Masala, OCR: Chicken Tikka -> FLAG)"""
    ocr_lines = validator.clean_ocr_evidence(["Chicken Tikka", "Butter Naan"])
    res: ValidationResult = validator.validate_item(
        item_name="Chicken Tikka Masala",
        ocr_candidates=ocr_lines,
        price=220.0,
    )
    assert res.status == "flagged"
    assert 50.0 <= res.similarity_score < 80.0


def test_6_hallucination_rejection(validator):
    """Test 6: Hallucination (Gemini: Dragon Chicken Supreme, OCR: Chicken Burger, French Fries, Cold Coffee -> REJECT)"""
    ocr_lines = validator.clean_ocr_evidence(["Chicken Burger", "French Fries", "Cold Coffee"])
    res: ValidationResult = validator.validate_item(
        item_name="Dragon Chicken Supreme",
        ocr_candidates=ocr_lines,
        price=350.0,
    )
    assert res.status == "rejected"
    assert res.similarity_score < 50.0
    assert res.confidence < 0.50


def test_7_random_and_metadata_noise_rejection(validator):
    """Test 7: Random Text / Business Noise (Gemini: FAST FOOD MENU, OCR: Welcome to ABC Restaurant -> REJECT)"""
    ocr_lines = validator.clean_ocr_evidence(["Welcome to ABC Restaurant", "Floor 2 Main Road", "Phone 555-1234"])
    
    # 1. Branding header
    res1: ValidationResult = validator.validate_item(
        item_name="FAST FOOD MENU",
        ocr_candidates=ocr_lines,
    )
    assert res1.status == "rejected"

    # 2. Contact noise
    res2: ValidationResult = validator.validate_item(
        item_name="www.restaurant.com",
        ocr_candidates=ocr_lines,
    )
    assert res2.status == "rejected"

    # 3. Gibberish
    res3: ValidationResult = validator.validate_item(
        item_name="XXXXX",
        ocr_candidates=ocr_lines,
    )
    assert res3.status == "rejected"


def test_8_price_contamination(validator):
    """Test 8: Price Contamination (Gemini: Paneer Butter Masala, OCR: Paneer Butter Masala ₹250 -> ACCEPT)"""
    ocr_lines = validator.clean_ocr_evidence(["Paneer Butter Masala ₹250", "Tandoori Roti $2.00"])
    res: ValidationResult = validator.validate_item(
        item_name="Paneer Butter Masala",
        ocr_candidates=ocr_lines,
        price=250.0,
    )
    assert res.status == "accepted"
    assert res.similarity_score >= 95.0


def test_9_menu_deduplication(validator):
    """Test 9: Safe Deduplication of duplicate items returned by LLM"""
    dummy_bbox = BoundingBox(0, 0, 100, 20)
    ocr_blocks = [
        TextBlock(text="Chicken Burger $10", bbox=dummy_bbox, confidence=0.95),
        TextBlock(text="French Fries $5", bbox=dummy_bbox, confidence=0.90),
    ]

    raw_menu = RecognizedMenu(
        image_path="test_menu.jpg",
        image_width=800,
        image_height=600,
        num_columns=1,
        sections=[
            MenuSection(
                title="Burgers",
                items=[
                    MenuItem(name="Chicken Burger", price=10.0),
                    MenuItem(name="Chicken Burger", price=10.0),  # Duplicate
                    MenuItem(name="French Fries", price=5.0),
                ],
            )
        ],
    )

    validated_menu = validator.validate_menu(raw_menu, ocr_blocks)
    burger_items = [it for s in validated_menu.sections for it in s.items if "chicken burger" in it.name.lower()]
    assert len(burger_items) == 1
    assert burger_items[0].validation_status == "accepted"


def test_10_ocr_failure_degraded_mode(validator):
    """Test 10: OCR Failure / Degraded Mode (OCR unreadable -> FLAG rather than aggressive REJECT for culinary items)"""
    # Empty / noisy OCR blocks
    ocr_blocks = []

    raw_menu = RecognizedMenu(
        image_path="test_menu.jpg",
        image_width=800,
        image_height=600,
        num_columns=1,
        sections=[
            MenuSection(
                title="Mains",
                items=[
                    MenuItem(name="Chicken Biryani", price=12.0),
                    MenuItem(name="Random Non Food Text", price=None),
                ],
            )
        ],
    )

    validated_menu = validator.validate_menu(raw_menu, ocr_blocks)
    items = validated_menu.to_flat_items()
    
    # Plausible culinary dish is flagged with provisional reason
    biryani = next((i for i in items if "Biryani" in i.name), None)
    assert biryani is not None
    assert biryani.validation_status == "flagged"
    assert "unreadable" in biryani.validation_reason.lower()

    # Non-food string in degraded OCR is dropped
    non_food = next((i for i in items if "Random Non Food" in i.name), None)
    assert non_food is None


def test_11_evidence_confidence_formula(validator):
    """Test confidence scoring bounds and weighting"""
    # High similarity + price + culinary relevance
    conf_high = validator.calculate_evidence_confidence(
        similarity_score=95.0,
        food_name="Chicken Burger",
        price=10.0,
        description="Fresh grilled patty",
        section="Mains",
        ocr_quality="HIGH",
    )
    assert 0.85 <= conf_high <= 0.98

    # Low similarity
    conf_low = validator.calculate_evidence_confidence(
        similarity_score=20.0,
        food_name="Dragon Surprise",
        price=None,
        description=None,
        section="General",
        ocr_quality="HIGH",
    )
    assert conf_low <= 0.40


def test_12_strict_food_only_filter(validator):
    """Test 12: Strict Food-Only Filter (Filters out placeholders, headers, prices, phones, drinks)"""
    ocr_evidence = [
        "Cheeseburger $12",
        "Cheese sandwich $8",
        "Spicy chicken $15",
        "Hot dog $6",
        "Fruit Salad $7",
        "Sandwich $9",
        "French Fries $4",
        "APPETIZERS",
        "MAIN COURSE",
        "RESTAURANT NAME",
        "INSERT YOUR LOCATION HERE",
        "NAME",
        "ORDER NOW",
        "+123456789",
        "$34",
        "Coffee",
        "Iced Tea",
        "Milk Shake",
        "Cocktails",
        "Orange Juice",
    ]
    cleaned_ocr = validator.clean_ocr_evidence(ocr_evidence)
    candidates = validator.generate_multi_line_candidates(cleaned_ocr)

    # 1. Non-food headers / templates / metadata should be REJECTED
    rejected_test_items = [
        "INSERT YOUR LOCATION HERE",
        "NAME",
        "RESTAURANT NAME",
        "MAIN COURSE",
        "APPETIZERS",
        "ORDER NOW",
        "+123456789",
        "$34",
        "Coffee",
        "Iced Tea",
        "Milk Shake",
        "Cocktails",
        "Orange Juice",
    ]
    for item in rejected_test_items:
        res = validator.validate_item(item, candidates)
        assert res.status == "rejected", f"Expected '{item}' to be rejected, got {res.status}"

    # 2. Genuine food dishes should be ACCEPTED
    accepted_test_items = [
        "Cheeseburger",
        "Cheese sandwich",
        "Spicy chicken",
        "Hot dog",
        "Fruit Salad",
        "Sandwich",
        "French Fries",
    ]
    for food in accepted_test_items:
        res = validator.validate_item(food, candidates)
        assert res.status in ("accepted", "flagged"), f"Expected '{food}' to be accepted/flagged, got {res.status}"

