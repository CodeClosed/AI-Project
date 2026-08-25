"""
Preset Sample Menus and Demonstration Data for NutriMenu AI.
Provides realistic diverse restaurant menus for testing and user exploration.
"""

from typing import Dict, List, Any

SAMPLE_MENUS: Dict[str, List[Dict[str, Any]]] = {
    "Indian Specialties Menu": [
        {
            "name": "Palak Paneer with Multigrain Roti",
            "description": "Fresh spinach puree with cottage cheese and whole wheat flatbread",
            "price": "$13.50",
            "tags": ["vegetarian"],
        },
        {
            "name": "Steamed Sprouted Moong Salad",
            "description": "Sprouted green lentils, cucumber, tomatoes, lemon and olive oil",
            "price": "$8.99",
            "tags": ["vegetarian", "vegan"],
        },
        {
            "name": "Tandoori Vegetable Medley",
            "description": "Char-grilled bell peppers, broccoli, zucchini, and mushrooms",
            "price": "$11.99",
            "tags": ["vegetarian"],
        },
        {
            "name": "Dal Makhani with Butter Naan",
            "description": "Black lentils slow cooked in butter and cream with refined maida naan",
            "price": "$14.00",
            "tags": ["vegetarian"],
        },
        {
            "name": "Vegetable Biryani with Cucumber Raita",
            "description": "Basmati rice cooked with mixed vegetables and spices with curd dip",
            "price": "$12.50",
            "tags": ["vegetarian"],
        },
        {
            "name": "Crispy Peanut Pakora Chaat",
            "description": "Deep-fried gram flour fritters tossed with roasted peanuts and tamarind sauce",
            "price": "$7.50",
            "tags": ["vegetarian"],
        },
        {
            "name": "Butter Chicken Makhani",
            "description": "Tender chicken tikka simmered in rich cashew and butter gravy",
            "price": "$16.99",
            "tags": ["non-vegetarian"],
        },
        {
            "name": "Gulab Jamun with Rabri",
            "description": "Fried condensed milk balls soaked in sugar syrup with thickened sweet milk",
            "price": "$6.00",
            "tags": ["dessert", "vegetarian"],
        },
    ],
    "Mediterranean & Cafe Menu": [
        {
            "name": "Grilled Salmon with Steamed Asparagus",
            "description": "Wild-caught salmon filet with lemon herb drizzle and asparagus",
            "price": "$18.50",
            "tags": ["pescatarian", "gluten-free"],
        },
        {
            "name": "Greek Quinoa Salad Bowl",
            "description": "Quinoa, kalamata olives, cucumber, cherry tomatoes, and light feta",
            "price": "$12.00",
            "tags": ["vegetarian", "gluten-free"],
        },
        {
            "name": "Crispy Deep-Fried Calamari",
            "description": "Battered squid rings fried golden with garlic mayo dip",
            "price": "$11.50",
            "tags": ["pescatarian"],
        },
        {
            "name": "Hummus & Tabbouleh Platter",
            "description": "Chickpea dip with parsley bulgur salad and whole wheat pita",
            "price": "$10.50",
            "tags": ["vegan"],
        },
        {
            "name": "Loaded Bacon Cheeseburger with Fries",
            "description": "Beef patty topped with cheddar, smoked bacon, mayo and french fries",
            "price": "$15.99",
            "tags": ["non-vegetarian"],
        },
        {
            "name": "Chocolate Lava Cake",
            "description": "Molten dark chocolate cake with vanilla ice cream",
            "price": "$7.50",
            "tags": ["dessert"],
        },
    ],
    "Asian Fusion & Bowls": [
        {
            "name": "Steamed Edamame with Sea Salt",
            "description": "Young soybeans in pod steamed fresh with mineral sea salt",
            "price": "$5.50",
            "tags": ["vegan", "gluten-free"],
        },
        {
            "name": "Tofu & Bok Choy Stir Fry",
            "description": "Organic firm tofu tossed with baby bok choy and garlic ginger glaze",
            "price": "$13.00",
            "tags": ["vegan"],
        },
        {
            "name": "Crispy Chicken Katsu with White Rice",
            "description": "Panko-crusted deep fried chicken cutlet with sweet tonkatsu sauce",
            "price": "$15.00",
            "tags": ["non-vegetarian"],
        },
        {
            "name": "Pad Thai with Crushed Peanuts",
            "description": "Rice noodles stir-fried with egg, bean sprouts, tamarind and roasted peanuts",
            "price": "$14.00",
            "tags": ["contains-peanuts"],
        },
        {
            "name": "Miso Glazed Black Cod",
            "description": "Broiled Alaskan black cod with sautéed shiitake mushrooms and broccolini",
            "price": "$24.00",
            "tags": ["pescatarian", "gluten-free"],
        },
    ],
}
