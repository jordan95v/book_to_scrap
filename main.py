from __future__ import annotations
import re
import requests
import csv
from pathlib import Path, WindowsPath
from bs4 import BeautifulSoup
from bs4.element import Tag
from requests.api import request
from requests.models import Response


class Scrap:
    '''Get info from all the books on the website.

    Attributes:
        url (str): URL of the main page of Books to Scrape.
    '''

    def __init__(
        self, url: str, image_dir: str | Path, csv_dir: str | Path
    ) -> None:
        self.url: str = url
        self.images_dir: Path
        self.csv_dir: Path

        if isinstance(image_dir, str):
            self.images_dir = Path.cwd() / image_dir
        else:
            self.images_dir = image_dir
        self.images_dir.mkdir(exist_ok=True, parents=True)

        if isinstance(csv_dir, str):
            self.csv_dir = Path.cwd() / csv_dir
        else:
            self.csv_dir = csv_dir
        self.csv_dir.mkdir(exist_ok=True, parents=True)

    def get_category_links(self) -> dict[str, str]:
        '''Get the link from all category on the side of the website.

        Returns:
            category_list (list): Return a list with all the category link's URL
        '''

        res: Response = requests.get(self.url)

        soup = BeautifulSoup(res.content, 'html.parser')

        category: list = (
            soup.find(class_='nav nav-list').find('ul').find_all('li')
        )

        categories: dict[str, str] = {}

        for category in category:
            category_url: str = category.find('a')['href']
            category_name: str = category_url.split('/')[-2]
            category_name = re.sub(r'([^_]+)_\d+$', r'\1', category_name)
            categories[category_name] = category_url

        return categories

    def get_books_info_on_page(self, books: Tag) -> list:
        '''Get all the information asked for all the books for all category

        TODO:
            - Refactor reusable methods
            - raise_for_status
            - naming

        Args:
            books (list): This is a list of all the book available on the page, so you can iterte trhought it, go to the book page and get info.
        '''
        books_metadata: list = []
        for book in books:
            url: str = f'{self.url}catalogue/{book.find("a")["href"][9:]}'
            res: Response = requests.get(url)
            book_page: BeautifulSoup = BeautifulSoup(
                res.content, 'html.parser'
            )
            info: dict = self.get_book(book_page, url)
            books_metadata.append(info)
            try:
                self.download_image(info['image_url'], info['category'])
            except KeyError:
                pass
        return books_metadata

    def get_info(
        self, book_page: BeautifulSoup, needed_info: str
    ) -> str | None:
        '''...'''
        th: Tag = book_page.find(
            'th', string=lambda text: needed_info in text.lower()
        )
        if th.text.lower() == needed_info.lower():
            return th.parent.find('td').text

    def get_book_categorie(self, book_page: BeautifulSoup) -> str:
        return (
            book_page.find(class_='active')
            .previous_sibling.previous_sibling.find('a')
            .text
        )

    def get_rating(self, book_page: BeautifulSoup) -> int:
        rating: list = book_page.find('p', class_='star-rating')['class']
        note: dict = {
            'One': 1,
            'Two': 2,
            'Three': 3,
            'Four': 4,
            'Five': 5,
        }
        return note.get(rating[1], 0)

    def get_description(self, book_page: BeautifulSoup) -> str:
        try:
            return book_page.find(
                'div', id='product_description'
            ).next_sibling.next_sibling.text
        except AttributeError as e:
            pass

    def get_title(self, book_page: BeautifulSoup) -> str:
        return book_page.find('h1').text

    def get_image_url(self, book_page: BeautifulSoup):
        return f'http://books.toscrape.com/{book_page.find("img")["src"].replace("../../", "")}'

    def get_book(self, book_page: BeautifulSoup, url: str) -> dict:
        info: dict = {
            'product_url': url,
            'upc': self.get_info(book_page, 'upc'),
            'title': self.get_title(book_page),
            'price_with_tax': self.get_info(book_page, 'price (incl. tax)'),
            'price_without_tax': self.get_info(book_page, 'price (excl. tax)'),
            'available': self.get_info(book_page, 'availability'),
            'category': self.get_book_categorie(book_page),
            'image_url': self.get_image_url(book_page),
            'rating': self.get_rating(book_page),
            'description': self.get_description(book_page),
        }

        return info

    def main(self) -> None:
        '''Iterate throught on all page of all category, so you can collect, so you can collect a list with book link's'''

        for category_name, category_url in self.get_category_links().items():
            books_metadata: list = []
            count: int = 1

            while True:
                full_url: str = (
                    f'{self.url}{category_url[:-10]}page-{count}.html'
                )
                print(full_url)
                # Juste pour savoir où j'en suis dans la boucle :), si tu lis ça t'es un boss
                res: Response = requests.get(full_url)

                if res.status_code != 200 and count == 1:
                    full_url: str = f'{self.url}{category_url}'
                    res: Response = requests.get(full_url)

                soup = BeautifulSoup(res.content, 'html.parser')
                books: Tag = soup.find_all(class_='product_pod')

                if res.status_code == 200:
                    books_on_page = self.get_books_info_on_page(books)
                    books_metadata.extend(books_on_page)
                    count += 1
                else:
                    break
            self.write_csv(books_metadata, category_name)

    def create_image_dir(self, category: str, url: str) -> str:
        '''...'''
        filename: str = url.split('/')
        category_dir: Path = self.images_dir / category
        category_dir.mkdir(exist_ok=True, parents=True)
        category_dir = category_dir / filename[-1]
        return category_dir

    def download_image(self, url: str, category: str) -> None:
        '''This is for downloading all the images of all books on the website.

        Args:
            info (dict): So you can get the category, to open the corresponding CSV files and write infos inside it !
        '''

        p: Path = self.create_image_dir(category, url)

        with open(p, 'wb') as f:
            img_download: Response = requests.get(url).content
            f.write(img_download)

    def write_csv(self, books_metadata: list, category: str) -> Path:
        '''This is for writing all the infos on the corresponding CSV file.

        Params:
            books_metadata: [{'upc': 'a', ...}, {'upc': 'b', ...}, ...]

        Args:
            info (dict): So you can get the category, to open the corresponding CSV files and write the books's infos inside it !
        '''
        csvfile: Path = self.csv_dir / f'{category}.csv'
        with csvfile.open('w', encoding='UTF-8', newline='') as f:
            fieldnames: list[str] = books_metadata[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for book_metadata in books_metadata:
                writer.writerow(book_metadata)
        return csvfile


test = Scrap('http://books.toscrape.com/', 'Images', 'CSV')
test.main()
