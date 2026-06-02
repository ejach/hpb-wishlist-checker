from argparse import ArgumentParser, ArgumentTypeError
from json import dumps, loads, JSONDecodeError
from logging import INFO, basicConfig, getLogger
from os import getenv
from random import choice
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from cloudscraper import create_scraper
from pgeocode import Nominatim

from hpb_wishlist_checker.spinner.spinner import Loading


basicConfig(
    level=INFO,
    format=None
)

logger = getLogger(__name__)
LOADING = Loading()

# stdout colors / unicode emojis
CYAN = '\033[36m'
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
CHECK = '\u2714'
CROSS = '\u2718'
UNDERLINE = '\033[4m'
RESET = '\033[0m'

HARDCOVER_API_KEY = getenv('HARDCOVER_API_KEY', None)

BROWSER_PROFILES = [
    {'browser': 'chrome', 'platform': 'windows', 'desktop': True},
    {'browser': 'firefox', 'platform': 'windows', 'desktop': True},
    {'browser': 'chrome', 'platform': 'linux', 'desktop': True},
    {'browser': 'firefox', 'platform': 'linux', 'desktop': True},
]


def init_scraper() -> Any:
    scraper = create_scraper(browser=choice(BROWSER_PROFILES))

    scraper.headers.update({
        'Accept': 'text/html,application/json,application/xhtml+xml',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })

    return scraper

# cloudscraper constant
SCRAPER = init_scraper()


def get_list_of_stores(zip_code: str, radius: int = 15) -> list[dict[str, object]]:    
    url = 'https://www.hpb.com/on/demandware.store/Sites-hpb-Site/en_US/Stores-FindStores'

    payload = {
        'showMap': 'false',
        'pliUUID': 'undefined',
        'usecurrentlocation': 'false',
        'fromStoreFinder': 'true',
        'radius': radius,
        'onlyAvailableStores': 'false',
        'isFromPLP': 'false',
        'hiddenPostalCode': zip_code,
    }

    nomi = Nominatim('us')
    location = nomi.query_postal_code(zip_code)

    if location.latitude and location.longitude:
        payload['lat'] = location.latitude
        payload['long'] = location.longitude

    url = f'{url}?{urlencode(payload)}'
    r = SCRAPER.get(url, data=payload, timeout=15)

    if r.status_code != 200:
        raise RuntimeError(
            f'{RED}HPB store lookup failed ({r.status_code}).{RESET}'
        )

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
        logger.info(f"{CYAN}Found store: {store_data['name']}{RESET}")

    return stores


def get_hpb_product_id(book_tuple: tuple[str, list[str]]) -> str | None:
    query = quote(f'{book_tuple[0]} {book_tuple[1][0]}')
    url = (
        'https://www.hpb.com/on/demandware.store/'
        'Sites-hpb-Site/en_US/SearchServices-GetSuggestions'
        f'?q={query}'
    )
    r = SCRAPER.get(url, timeout=10)

    soup = BeautifulSoup(r.text, 'lxml')

    first_product = soup.select_one("span[id^='product-'] a")
    if not first_product:
        return None

    aria_label = first_product.get('aria-label', '').lower()
    href = first_product.get('href', '')

    if book_tuple[0].lower() not in aria_label:
        return None

    # Extract M-XXXXX-T (Book ID) or P-XXXXX-USED (Specific Product ID)
    for part in href.split('/'):
        if part.startswith(('M-', 'P-')):
            return part.replace('.html', '')

    return None


def get_hardcover_want_to_read() -> list[dict[str, object]]:
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

    body = dumps({'query': query}).encode('utf-8')

    req = Request(
        url='https://api.hardcover.app/v1/graphql',
        data=body,
        headers={
            'Content-Type': 'application/json',
            'Authorization': HARDCOVER_API_KEY,
        },
        method='POST'
    )

    try:
        with urlopen(req, timeout=15) as resp:
            raw = resp.read().decode('utf-8')
    except HTTPError as e:
        raise RuntimeError(f'{RED}Hardcover API HTTP error {e.code}{RESET}: {e.read().decode()}')
    except URLError as e:
        raise RuntimeError(f'{RED}Hardcover API connection error{RESET}: {e.reason}')
    except Exception as e:
        raise RuntimeError(f'{RED}Unexpected error contacting Hardcover API{RESET}: {e}')

    try:
        payload = loads(raw)
    except JSONDecodeError:
        raise RuntimeError(f'{RED}Failed to decode Hardcover API response as JSON{RESET}')

    if 'errors' in payload:
        raise RuntimeError(f'{RED}Hardcover API GraphQL errors:{RESET} {payload["errors"]}')

    try:
        books = payload['data']['me'][0]['user_books']
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(f'{RED}Unexpected Hardcover API response structure{RESET}')

    books_result = []
    for b in books:
        book = b.get('book', {})
        authors = [
            c['author']['name']
            for c in book.get('contributions', [])
            if c.get('author') and c['author'].get('name')
        ]
        if book.get('title'):
            books_result.append({
                'title': book['title'],
                'authors': authors
            })

    return books_result

def check_hpb_store_availability(store_id: str, book_id: str, book_name: str) -> dict:
    url = (
        f'https://www.hpb.com/search?q={book_id}'
        f'&prefn1=instorePickUpAvailableStores'
        f'&prefv1={store_id}'
        f'&srule=best-matches&sz=20&bopisStoreId={store_id}'
    )
    r = SCRAPER.get(url, timeout=10)

    soup = BeautifulSoup(r.text, 'html.parser')
    msg_div = soup.select_one('div.msg')

    found = not (
        msg_div and 'We were not able to find any results for' in msg_div.text
    )

    return {
        'store_id': store_id,
        'book_id': book_id,
        'book_name': book_name,
        'found': found,
        'url': url,
    }


def zip_code_type(value: str) -> str:
    if not value.isdigit() or len(value) != 5:
        raise ArgumentTypeError(f'{RED}ZIP code must be exactly 5 digits{RESET}')
    return value

if __name__ == '__main__':
    if not HARDCOVER_API_KEY:
        raise SystemExit(
            f'{RED}Error: HARDCOVER_API_KEY is not set. Exiting.{RESET}'
        )

    parser = ArgumentParser(
        description='Finds which Hardcover wishlist ' \
        'books are in stock at nearby Half Price Books stores.'
    )
    parser.add_argument(
        '--zip',
        required=True,
        type=zip_code_type,
        help='5-digit US ZIP code'
    )
    parser.add_argument(
        '--radius',
        type=int,
        choices=[15, 30, 50, 100, 300],
        default=15,
        help='Search radius in miles (default: 15)'
    )

    args = parser.parse_args()
    zip_code = args.zip.strip()
    radius = args.radius

    stores = get_list_of_stores(zip_code, radius)
    if not stores:
        raise SystemExit(
            f'{RED}{CROSS}{RESET}{YELLOW} No stores found near '
            f'{zip_code} within {radius} miles. Exiting.{RESET}'
        )
    logger.info(f'\n{CYAN}Total stores: {len(stores)}{RESET}')
    book_list = [(book['title'], book['authors']) for book in get_hardcover_want_to_read()]
    found_hpb_entries = []
    for x in book_list:
        book_id = get_hpb_product_id(x)
        if book_id:
            LOADING.start(text=f'{str(len(found_hpb_entries))} -> {x[0]}')
            found_hpb_entries.append((book_id, x[0]))
    LOADING.succeed(f'Matched {len(found_hpb_entries)} wishlisted books in the Half Price Books catalog.')
    for store in stores:
        logger.info(f'\n{UNDERLINE}{CYAN}Now searching store: {store["name"]} ({store["id"]}){RESET}\n')
        for book_id, title in found_hpb_entries:
            result = check_hpb_store_availability(store['id'], book_id, title)
            if result['found']:
                logger.info(
                    f'{GREEN}{CHECK} Found {result["book_name"]} ({book_id}) at store {store["id"]}{RESET}\n'
                    f'{CYAN}{result["url"]}{RESET}'
                )
            else:
                logger.info(f"{RED}{CROSS}{RESET}{YELLOW} Not found {result['book_name']} at store {store['id']}{RESET}")
