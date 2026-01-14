## HPB Wishlist Stock Checker
[![PyPI](https://img.shields.io/pypi/v/cloudscraper?logo=python&label=cloudscraper&style=flat-square&color=FFD43B)](https://pypi.org/project/cloudscraper/)
[![PyPI](https://img.shields.io/pypi/v/beautifulsoup4?logo=python&label=beautifulsoup4&style=flat-square&color=FFD43B)](https://pypi.org/project/beautifulsoup4/)
[![PyPI](https://img.shields.io/pypi/v/pgeocode?logo=python&label=pgeocode&style=flat-square&color=FFD43B)](https://pypi.org/project/pgeocode/)

> [!CAUTION]
> This tool interacts with the Half Price Books (HPB) website to check in-store availability of books. It **bypasses some of HPB's built-in safeguards**.  
> 
> ⚠️ **Risks and Important Notes:**
> - Excessive or automated use may violate HPB's terms of service and could result in **temporary or permanent blocking** of your IP address or account.  
> - This tool is intended **for personal use only** and **educational purposes**.  
> - HPB’s website structure and inventory are subject to change. The tool may **stop working at any time**.  
> - The author does **not condone abusing HPB's systems**. Use responsibly, ethically, and at your own risk.  
> 
> By using this tool, you accept full responsibility for your actions and any consequences.

This Python script allows you to:

- Retrieve book titles from a public Hardcover wishlist using their API.
- Find Half Price Books (HPB) stores nearest to you.
- Check in-store availability of the wishlist books at those HPB stores.

### Features

- Extracts all book titles from a Hardcover wishlist.
- Searches for HPB stores by ZIP code.
- Checks if books are available for in-store pickup.
- Outputs a list of stores where each book is in stock.

### Installation

1. Clone this repository or copy the script.
2. Install dependencies:
   `pip install -R requirements.txt`

### Configuration

- Set `HARDCOVER_API_KEY` to the API key associated with your account.\
This can be found [here](https://hardcover.app/account/api).\
Run `export HARDCOVER_API_KEY="<your_key>"`

### Usage

```bash
usage: stores.py [-h] --zip ZIP [--radius {15,30,50,100,300}]

Finds which Hardcover wishlist books are in stock at nearby Half Price Books stores.

options:
  -h, --help            show this help message and exit
  --zip ZIP             5-digit US ZIP code
  --radius {15,30,50,100,300}
                        Search radius in miles (default: 15)
```

Run the script:
`python stores.py --zip <zip_code>`

Example output:

```bash
Now searching store: [STORE NAME] ([STORE ID])

No results for [Book Title 1] ([Book ID]) at store [STORE ID]
No results for [Book Title 2] ([Book ID]) at store [STORE ID]
No results for [Book Title 3] ([Book ID]) at store [STORE ID]
...
Successfully found [Book Title X] ([Book ID]) at store [STORE ID]: 
[HPB Search URL]
No results for [Book Title Y] ([Book ID]) at store [STORE ID]
Successfully found [Book Title Z] ([Book ID]) at store [STORE ID]: 
[HPB Search URL]
```
