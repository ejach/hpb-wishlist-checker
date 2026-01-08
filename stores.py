from playwright.sync_api import sync_playwright
from time import sleep
from wishlist.core import Wishlist
from urllib import parse

HEADLESS = False
WISHLIST_ID = ""
ZIP_CODE = ""

def get_wishlist_titles(wishlist_id):
    w = Wishlist(wishlist_id)
    return [item.title for item in w if getattr(item, "title", None)]

def get_list_of_stores(zip_code):
    hpb_stores = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        page = browser.new_page()

        # Go to HPB store locator
        page.goto("https://www.hpb.com/stores/")
        sleep(2)

        # Fill ZIP and press Enter
        zip_input = page.locator("#store-postal-code").nth(1)
        zip_input.fill(zip_code)
        page.keyboard.press("Enter")
        sleep(3)

        # Select all divs with IDs starting with HPB-
        store_divs = page.locator("div[id^='HPB-']")
        count = store_divs.count()

        for i in range(count):
            store_id = store_divs.nth(i).get_attribute("id")
            if store_id:
                store_name = store_divs.nth(i).get_attribute("data-title")
                print(f"Found {store_name}")
                hpb_stores.append({store_id: store_name})

        browser.close()

    return hpb_stores

def check_hpb_stock(book_title, stores):
    in_stock_stores = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        page = browser.new_page()

        for store in stores:
            for store_id, store_name in store.items():
                # URL encode the book title
                print(f'Searching for {book_title} at {store_name}')
                query = parse.quote(book_title)
                url = f"https://www.hpb.com/search?q={query}&prefn1=instorePickUpAvailableStores&prefv1={store_id}&srule=best-matches&sz=20&bopisStoreId={store_id}"
                page.goto(url)

                # wait for results to load
                page.wait_for_load_state("load", timeout=3000)

                # Verify results if the .result-count is present
                result_element = page.locator(".result-count")
                if result_element.count() > 0:
                    print(f'Found {book_title} at {store_name}')
                    in_stock_stores.append(store_name)

            print(f"Checked {store_id}")

        browser.close()

    return in_stock_stores


if __name__ == "__main__":
    titles = get_wishlist_titles(WISHLIST_ID)
    stores = get_list_of_stores(ZIP_CODE)
    store_names = ", ".join(list(store.values())[0] for store in stores)
    print(f"These are the stores in the zip code {ZIP_CODE}: {store_names}\n")

    available_stores = {}
    for book_title in titles:
        available_stores[book_title] = check_hpb_stock(book_title, stores)

    print("In-stock at these stores:\n")
    for book, store_list in available_stores.items():
        if store_list:
            print(f'"{book}" is available at: {", ".join(store_list)}')
        else:
            print(f'"{book}" is not in stock at any stores')
