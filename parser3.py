import urllib.request
from bs4 import BeautifulSoup
import re
from datetime import date, timedelta
from openpyxl import Workbook
import logging
from grab import Grab
import time


logging.basicConfig(filename='example.log',level=logging.DEBUG)
today = str(date.today())
yesterday = str(date.today() - timedelta(1))

def parse_ad(URL, type_of_ad):
    logging.info('запутили parse_ad')
    ob = []
    def get_html(URL):  #получили страницу
        g = Grab(url=URL, user_agent="Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11", timeout=8)

        try:
            response = g.request()
            time.sleep(2)
            # response = urllib.request.urlopen(URL, timeout=8)
            logging.info('получили какой то response')
            # return response.read()
            return response.unicode_body()
        except:
            logging.info('Сервер не ответил за 8 секунд, попробуем еще раз!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            return get_html(URL)

    soup = BeautifulSoup(get_html(URL), 'lxml') # страницу превратили в суп
    logging.info('пытаемся распарсить объявление')
    ob.append(type_of_ad)
    ob.append(soup.find(class_='title-info-title-text').text.replace('\n', ''))  # Заголовок
    desc_tmp = soup.find(class_='title-info-metadata-item').text.replace('\n', '').split(',')
    ob.append(desc_tmp[0].replace('№', ''))  # добавили ид

    # добавляем дату
    if 'сегодня' in desc_tmp[1]:
        ob.append(today)
    elif 'вчера' in desc_tmp[1]:
        ob.append(yesterday)
    else:
        ob.append(desc_tmp[1])

    ob.append(soup.find(class_='title-info-views').text.replace('\n', ''))  # количество просмотров объявления
    # ob.append(soup.find(class_='title-info-metadata-item').text.replace('\n', ''))  # номер и дата размещения
    ob.append(soup.find(class_='seller-info-label').text.replace('\n', ''))  # от кого объявление (агентство)
    try:
        ob.append(soup.find(class_='seller-info-time').text.replace('\n', '').replace('На Avito ', ''))  # дата регистрации того кто разместил объявление
    except:
        ob.append('Нет времени регистрации')

    seler_info_prop = soup.find_all(class_='seller-info-prop')  # ИНФОРМАЦИЯ ИЗ БЛОКА ПРО ПРОДАВЦА
    ob.append(seler_info_prop[int(len(seler_info_prop)/2-1)].text.replace('\n', '').replace('Адрес', ''))  # адрес объекта

    # на всякий случай: этот цикл сохраняет всю информацию из блока про продавца (там адрес объекта тоже)
    #for i in range(int(len(seler_info_prop)/2)):
        #ob.append('Seller_info' + str(i) + ':'+ seler_info_prop[i].text.replace('\n', ''))

    desc_tmp = soup.find(class_='item-params').text.replace('\n', '').split(';')  # параметры объекта такие как площадь и класс здания
    # практика показала что параметра только оди или два. чтобы столбики не ехали, когда 1 - сделал элс
    if len(desc_tmp) == 2:
        for desc in desc_tmp:
            ob.append(desc)
    else:
        for desc in desc_tmp:
            ob.append(desc)
        ob.append('Нет класса')

    ob.append(soup.find(class_='item-map-location').text.replace('\n', '').replace('Скрыть карту', "").replace('Адрес:',''))  # Описание

    tmp_price = (soup.find(class_='price-value-string').text.replace('₽', '').replace('\n', '')) # цена в неформатированном виде

    def price_str_to_int(tmp_price):  # парсим и приводим в нормальный вид цену
        logging.info('преобразовываем цену')
        tmp_price = re.findall(r'\d+',tmp_price)  # оставило только цифры, но в виде списка
        price = ''
        for i in tmp_price: # из спсика делаем единую строку
            price = price + i

        return price

    ob.append(price_str_to_int(tmp_price))
    # Берем лат и лон объекта с карты на странице объявления
    ob.append(soup.find(class_='b-search-map expanded item-map-wrapper js-item-map-wrapper').get('data-map-lat'))
    ob.append(soup.find(class_='b-search-map expanded item-map-wrapper js-item-map-wrapper').get('data-map-lon'))
    ob.append(soup.find(class_='item-description').text.replace('\n', ''))  # Описание ,бывает -html  -text

    logging.info('закончили парсить объявление')
    return ob


def get_soup(URL):
    # делаем суп из ссылки
    def get_html(URL):  # получили страницу
        g = Grab(url=URL, user_agent="Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11", timeout=8)
        try:
            response = g.request()
            # response = urllib.request.urlopen(URL, timeout=8)
            logging.info('запросили страницу со списком объявлений и сделали суп')
            # return response.read()
            time.sleep(2)
            return response.unicode_body()
        except:
            logging.warning('сервер не ответил вовремя по запросу списка объявлений, пробуем еще раз!!!!!!!!!!!!!!!!!')
            return get_html(URL)

    soup = BeautifulSoup(get_html(URL), 'lxml')  # страницу превратили в суп
    return soup

def page_handler(made_soup, j):  # Обрабатываем страницу и выясняем, добрались ли мы до последней страницы
    logging.info('выясняем добрались ли до поледней страницы')
    # print(made_soup)
    numbers = made_soup.find(class_='pagination-pages clearfix')
    pagination_page = numbers.find_all(class_='pagination-page')
    current = numbers.find(class_='pagination-page pagination-page_current').text
    # print('current', current)

    def is_the_last_page(pagination_page, j):  # опредеояем, увидели ли мы номер последней страницы в цифрах на странице
        last_text = pagination_page[-1].text  # если там все таки вылезет "последняя"
        last_href = pagination_page[-1].get('href')
        if int(current) == int(last_text):
            return current, last_href

        if int(last_text) > j:
            z = int(last_text)
        else:
            z = j
        return z, last_href

    return is_the_last_page(pagination_page, j)

def get_last_number(soup): # Выясняем, сколько страниц объявлений
    j = 1  # тут мы записываем номер текущей страницы на которую зашли
    tmp_soup = soup
    url_tmp = ''
    work = True

    while work is True:
        last_j = j
        j, url_tmp = page_handler(tmp_soup, j) # запрашиваем последний видимый на странице номер и получаем ссылку на нее
        print(j)
        if int(j) <= last_j:  # сравниваем номер текущейй страницы с последней видимой
            # номер последней == номеру текущей
            return j
        else:
            url_tmp = 'https://www.avito.ru' + url_tmp
            tmp_soup = get_soup(url_tmp)




def make_list_of_ad_links(start_url2):  #получаем список сслок на объявления на странице
    logging.info('делаем список сслок на объявления на странице')
    links = []
    soup = get_soup(start_url2)
    list_ = soup.find_all(class_='item-description-title-link')  # берем все ссылки на странице
    for i in range(len(list_)):
        logging.info('добавили ссылку')
        links.append('https://www.avito.ru' + list_[i].get('href'))
    return links


def type_of_ad_handler(start_url, type_of_ad):
    # точка начала программы!
    start_soup = get_soup(start_url + '1')  # делаем суп из первой страницы со списком объявлений
    print(start_soup)
    print('выясняем, сколько всего страниц объявлений')
    number_of_pages = get_last_number(start_soup)  # выясняем сколько всего объявлений

    # list_of_ob = []
    for i in range(int(number_of_pages)):
        # проходим по всем страницам с объявлениями
        logging.info('СТРАНИЦА НОМЕР: ' + str(i))
        print('Страница:' + str(i))
        try:
            logging.info('пытаемся составить список ссылок объявлений')
            list_of_links = make_list_of_ad_links(start_url + str(i+1))
            for link in list_of_links:
                print(link)
                # проходим по каждой ссылке на странице
                try:
                    logging.info('пытаемся распарсить объявление и добавить в рабочую книгу')
                    ob_ = parse_ad(link, type_of_ad)
                    time.sleep(1)
                    ws.append(ob_)  # добавляем объявление в эксель
                    print(ob_)
                except:
                    print(parse_ad(link, type_of_ad))
                    logging.warning('Не смогли распарсить объявление')
                    wb.save("sample.xlsx")
                    print('Ошибка при парсинге объявления')
        except:
            print(make_list_of_ad_links(start_url + str(i+1)))
            logging.warning('не смогли получить список ссылок на объявления на странице! ')
            wb.save("sample.xlsx")
            print('ощибка при парсинге страниц с объявлениями')

        wb.save("sample.xlsx")  # сохранили книгу после прохода типа объявления


# URL3 = 'https://www.avito.ru/rossiya/kommercheskaya_nedvizhimost/prodam/za_vse/ofis?p='
URL_list = [#'https://www.avito.ru/rossiya/kommercheskaya_nedvizhimost/prodam/za_vse/drugoe?p=',
            #'https://www.avito.ru/rossiya/kommercheskaya_nedvizhimost/prodam/za_vse/obshestvennoe_pitanie?p=',
            #'https://www.avito.ru/rossiya/kommercheskaya_nedvizhimost/prodam/za_vse/gostinicy?p=',
            # 'https://www.avito.ru/rossiya/kommercheskaya_nedvizhimost/prodam/za_vse/ofis?p=',
            #'https://www.avito.ru/rossiya/kommercheskaya_nedvizhimost/prodam/za_vse/proizvodstvo?p=',
            #'https://www.avito.ru/rossiya/kommercheskaya_nedvizhimost/prodam/za_vse/sklad?p=',
            'https://www.avito.ru/rossiya/kommercheskaya_nedvizhimost/prodam/za_vse/magazin?p=']

Type_list = [#'Свободное назначение',
             #'Общественное питание',
             #'Гостиницы',
             # 'офис',
             #'Производство',
             #'Склад',
             'Торговое помещение']


wb = Workbook()  # создали новый файл для записи переработанной даты
ws = wb.active

# Пытаемся обмануть и прикинуться браузером с человеком
g = Grab(user_agent="Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11", timeout=8)
g.setup(url='https://wwww.avito.ru/')
g.request()
time.sleep(4)
g.setup(url='https://www.avito.ru/rossiya/nedvizhimost')
g.request()
time.sleep(6)
g.setup(url='https://www.avito.ru/rossiya/kommercheskaya_nedvizhimost')
g.request()
time.sleep(3)


for i in range(len(URL_list)):
    print('Обрабатываем ' + Type_list[i] + ' тип объявления')
    logging.info('Начали обрабатывать новый тип объявления')
    type_of_ad_handler(URL_list[i],Type_list[i])
    logging.info('Закончили обрабатывать этот тип объявления')
    wb.save("sample_2019.xlsx")



print('запись начата')
wb.save("sample.xlsx")
print('запись закончена')