from bs4 import BeautifulSoup
from urllib.parse import quote, urlencode
from os import getenv
from sys import exit

from requests import post
from cloudscraper import create_scraper
from pgeocode import Nominatim

# stdout colors
CYAN = '\033[36m'
RED = '\033[31m'
GREEN = '\033[32m'
UNDERLINE = '\033[4m'
RESET = '\033[0m'

HARDCOVER_API_KEY = getenv('HARDCOVER_API_KEY', None)

# cloudscraper constant
SCRAPER = create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)


def get_list_of_stores(zip_code, radius=15):
    url = 'https://www.hpb.com/on/demandware.store/Sites-hpb-Site/en_US/Stores-FindStores'

    nomi = Nominatim('us')
    location = nomi.query_postal_code(zip_code)

    lat = location.latitude
    lon = location.longitude

    payload = {
        'showMap': 'false',
        'pliUUID': 'undefined',
        'usecurrentlocation': 'false',
        'fromStoreFinder': 'true',
        'radius': radius,
        'onlyAvailableStores': 'false',
        'isFromPLP': 'false',
        'hiddenPostalCode': zip_code,
        'lat': lat,
        'long': lon,
    }

    fin = f"{url}?{urlencode(payload)}"
    r = SCRAPER.get(fin, data=payload, timeout=15)
    r.raise_for_status()

    data = r.json()
    stores = []

    for store in data.get('stores', []):
        distance = store.get('distanceinMI')
        if distance is None or distance > radius:
            continue

        store_data = {
            'id': store.get('ID'),
            'name': store.get('name'),
            'city': store.get('city'),
            'state': store.get('stateCode'),
            'distance': distance,
            'pickup': store.get('storePickupEnabled'),
        }

        stores.append(store_data)
        print(f"{CYAN}Found store: {store_data['name']}{RESET}")

    return stores


def get_hpb_product_id(book_title):
    query = quote(f'{book_title[0]} {book_title[1][0]}')
    url = (
        'https://www.hpb.com/on/demandware.store/'
        'Sites-hpb-Site/en_US/SearchServices-GetSuggestions'
        f'?q={query}'
    )
    r = SCRAPER.get(url, timeout=10)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, 'html.parser')

    first_product = soup.select_one('span[id^="product-"] a')
    if not first_product:
        return None

    aria_label = first_product.get('aria-label', '').lower()
    href = first_product.get('href', '')

    if book_title[0].lower() not in aria_label:
        return None

    # Extract M-XXXXX-T (Book ID) or P-XXXXX-USED (Specific Product ID)
    for part in href.split('/'):
        if part.startswith(('M-', 'P-')):
            return part.replace('.html', '')

    return None


def get_hardcover_want_to_read():
    # StatusId == 1 -> "Want to Read"
    query = '''
    query GetWantToRead {
      me {
        user_books(where: {status_id: {_eq: 1}}) {
          book {
            title
            contributions {
              author {
                name
              }
            }
          }
        }
      }
    }
    '''

    response = post(
        'https://api.hardcover.app/v1/graphql',
        headers={
            'Content-Type': 'application/json',
            'Authorization': HARDCOVER_API_KEY
        },
        json={'query': query}
    )
    response.raise_for_status()
    payload = response.json()

    books = payload['data']['me'][0]['user_books']  # note the [0] here
    simplified_books = []

    for b in books:
        book = b['book']
        authors = [c['author']['name'] for c in book.get('contributions', [])]
        simplified_books.append({
            'title': book['title'],
            'authors': authors
        })

    return simplified_books

def check_hpb_store_availability(store_id, book_id, book_name):
    url = (
        f'https://www.hpb.com/search?q={book_id}'
        f'&prefn1=instorePickUpAvailableStores'
        f'&prefv1={store_id}'
        f'&srule=best-matches&sz=20&bopisStoreId={store_id}'
    )
    r = SCRAPER.get(url, timeout=10)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, 'html.parser')
    # look for the 'no results' message
    msg_div = soup.select_one('div.msg')
    if msg_div and 'We were not able to find any results for' in msg_div.text:
        print(f'{RED}No results for {book_name} ({book_id}) at store {store_id}{RESET}')
    else:
        print(f'{GREEN}Successfully found {book_name} ({book_id}) at store {store_id}: \n{RESET}{CYAN}{url}{RESET}')
    return url


if __name__ == '__main__':
    if not HARDCOVER_API_KEY:
        print(f'{RED}Error: HARDCOVER_API_KEY is not set. Exiting.{RESET}')
        exit(1)
    zip_code = input(f'{CYAN}Enter your Zip Code:{RESET}\n').strip()
    if not zip_code or not zip_code.isdigit() or len(zip_code) != 5:
        print(f'{RED}Error: A valid 5-digit ZIP code is required.{RESET}')
        exit(1)
    radius_input = input(
        f'{CYAN}Enter search radius in miles '
        f'(press Enter for default: 15 | options: 15, 30, 50, 100, 300){RESET}\n'
    ).strip()
    if radius_input == '':
        radius = 15
    elif radius_input in {'15', '30', '50', '100', '300'}:
        radius = int(radius_input)
    else:
        print(f'{RED}Error: Radius must be one of 15, 30, 50, 100, or 300 miles.{RESET}')
        exit(1)
    stores = get_list_of_stores(zip_code, radius)
    print(f'\n{CYAN}Total stores: {len(stores)}{RESET}')
    book_list = [(book['title'], book['authors']) for book in get_hardcover_want_to_read()]
    found_hpb_entries = []
    for x in book_list:
        book_id = get_hpb_product_id(x)
        if book_id:
            found_hpb_entries.append((book_id, x[0]))
    for store in stores:
        print(f'\n{UNDERLINE}{CYAN}Now searching store: {store["name"]} ({store["id"]}){RESET}\n')
        for book_id, title in found_hpb_entries:
            check_hpb_store_availability(store['id'], book_id, title)
