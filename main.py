from __future__ import annotations
import requests
import csv
from pathlib import Path, WindowsPath
from bs4 import BeautifulSoup
from requests.api import request
from requests.models import Response


class Scrap:
    '''Get info from all the books on the website.

    Attributes:
        url (str): URL of the main page of Books to Scrape.
    '''

    def __init__(self, url: str) -> None:
        self.url: str = url

    def get_category_link(self):
        '''Get the link from all category on the side of the website.

        Returns:
            category_list (list): Return a list with all the category link's
        '''

        res: Response = requests.get(self.url)

        soup = BeautifulSoup(res.content, 'html.parser')

        category: list = (
            soup.find(class_='nav nav-list').find('ul').find_all('li')
        )

        category_list: list = []

        for category in category:
            category_list.append(category.find('a')['href'])

        return category_list

    def get_book_info(self, books) -> None:
        '''Get all the information asked for all the books for all category

        Args:
            books (list): This is a list of all the book available on the page, so you can iterte trhought it, go to the book page and get info.
        '''

        for book in books:
            url: str = f'{self.url}catalogue/{book.find("a")["href"][9:]}'
            res: Response = requests.get(url)
            book_page = BeautifulSoup(res.content, 'html.parser')

            info: dict = {
                'product_url': url,
                'upc': book_page.find(
                    'th', string=lambda text: 'upc' in text.lower()
                )
                .parent.find('td')
                .text,
                'title': book_page.find('h1').text,
                'price_with_tax': book_page.find(
                    'th',
                    string=lambda text: 'price (incl. tax)' in text.lower(),
                )
                .parent.find('td')
                .text,
                'price_without_tax': book_page.find(
                    'th',
                    string=lambda text: 'price (excl. tax)' in text.lower(),
                )
                .parent.find('td')
                .text,
                'available': book_page.find(
                    'th',
                    string=lambda text: 'availability' in text.lower(),
                )
                .parent.find('td')
                .text,
                'category': book_page.find(class_='active')
                .previous_sibling.previous_sibling.find('a')
                .text,
                'image_url': f'http://books.toscrape.com/{book_page.find("img")["src"][6:]}',
            }

            rating: list = book_page.find('p', class_='star-rating')['class']

            note: dict = {
                'One': 1,
                'Two': 2,
                'Three': 3,
                'Four': 4,
                'Five': 5,
            }

            info['rating'] = note.get(rating[1], 0)

            try:
                info['product_description'] = book_page.find(
                    'div', id='product_description'
                ).next_sibling.next_sibling.text
            except AttributeError as e:
                print(e)

            self.get_images_download(info)
            self.write_csv(info)

    def main(self) -> None:
        '''Iterate throught on all page of all category, so you can collect, so you can collect a list with book link's'''

        for page in self.get_category_link():

            count: int = 1

            while True:
                full_url: str = f'{self.url}{page[:-10]}page-{count}.html'
                print(full_url)
                # Juste pour savoir où j'en suis dans la boucle :), si tu lis ça t'es un boss
                res: Response = requests.get(full_url)

                if res.status_code != 200 and count == 1:
                    full_url: str = f'{self.url}{page}'
                    res: Response = requests.get(full_url)

                soup = BeautifulSoup(res.content, 'html.parser')
                books: list = soup.find_all(class_='product_pod')

                if res.status_code == 200:
                    self.get_book_info(books)
                    count += 1
                else:
                    break

    def get_images_download(self, info) -> None:
        '''This is for downloading all the images of all books on the website.

        Args:
            info (dict): So you can get the category, to open the corresponding CSV files and write infos inside it !
        '''

        url: str = info.get('image_url')

        p: WindowsPath = Path.cwd() / 'Images' / f'{info["category"]}'
        p.mkdir(exist_ok=True, parents=True)

        p: WindowsPath = p / url[44:]

        with open(p, 'wb') as f:
            img_download: Response = requests.get(
                info.get('image_url')
            ).content
            f.write(img_download)

    def write_csv(self, info: dict) -> None:
        '''This is for writing all the infos on the corresponding CSV file.

        Args:
            info (dict): So you can get the category, to open the corresponding CSV files and write the books's infos inside it !
        '''

        p: WindowsPath = Path.cwd() / 'CSV'
        p.mkdir(exist_ok=True, parents=True)

        p: WindowsPath = p / f'{info["category"]}.csv'

        if not p.exists():
            with open(p, 'w', encoding='UTF-8', newline='') as f:
                fieldnames: list = [key for key in info.keys()]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

        with open(p, 'a', encoding='UTF-8', newline='') as f:
            fieldnames: list = [key for key in info.keys()]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow(info)


test = Scrap('http://books.toscrape.com/')
test.main()
