HPB Wishlist Stock Checker

This Python script allows you to:

- Retrieve book titles from a public Amazon wishlist using wishlist-core.
- Find Half Price Books (HPB) stores in a specific ZIP code.
- Check in-store availability of the wishlist books at those HPB stores.

It uses Playwright to simulate a real browser session, ensuring compatibility with HPB's JavaScript-driven site.

Features:

- Extracts all book titles from a public Amazon wishlist.
- Searches for HPB stores by ZIP code.
- Checks if books are available for in-store pickup.
- Outputs a list of stores where each book is in stock.

Requirements:

- Python 3.9+
- playwright
- wishlist-core

Installation:

1. Clone this repository or copy the script.
2. Install dependencies:
   pip install playwright wishlist-core
3. Install the required browser for Playwright:
   python -m playwright install

Configuration:

- Set WISHLIST_ID to your Amazon wishlist code.
- Set ZIP_CODE to the ZIP code for nearby HPB stores.
- Set HEADLESS to False to watch the browser actions.

Usage:

Run the script:
python stores.py

Example output:

These are the stores in the zip code 46204: Half Price Books Downtown, HPB Clearwater Village, HPB Broad Ripple

In-stock at these stores:

"The Hobbit" is available at: HPB Clearwater Village
"1984" is not in stock at any stores

Notes:

- HPB’s site dynamically loads content via JavaScript. Playwright ensures that the page fully renders before checking for stock.
- The script currently checks in-store availability only (pickup at the store).
- For best results, keep HEADLESS=False when debugging.

