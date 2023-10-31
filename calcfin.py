
import requests
import pandas as pd

#progressBar
from time import sleep
from tqdm import tqdm

from dlbar import DownloadBar

download_bar = DownloadBar()

#------------------------------
pd.set_option('display.max_rows', None)

def tickerCollector():
    #Данные о тикерах сохраним в переменной file. Так как ссылка не меняется, то можем её захардкодить и не скачивать на компьютер эксель
    url = "https://www.moex.com/ru/listing/securities-list-csv.aspx?type=1"
    fileName = "securities-list-csv.aspx"
    download_bar.download(
        url=url,
        dest = fileName,
        title='Скачиваем тикеры с MOEX...'
        )   
    
    securityList = pd.read_csv("securities-list-csv.aspx", sep=',', encoding='cp1251')
    #headers = securityList.columns
    #Анализируем колонки, которые нам могут помочь. Внимание привлекли колонки TRADE_CODE и INSTRUMENT_CATEGORY
    #Наша задача - отобрать только акции и запомнить их тикеры, чтобы затем узнать текущие цены на инструменты
    #на бирже
    securityList = securityList[["INSTRUMENT_CATEGORY","TRADE_CODE"]]
    #Мы отберем тикеры по двум фильтрам - по слову акции в категориях инструменты
    #И по длине торгового кода - максимальная его не превышает символов (для российсих акций)
    securityList = securityList[
                                (securityList["INSTRUMENT_CATEGORY"].str.contains("акци|Акци"))&
                                (securityList["TRADE_CODE"].str.len()<=6
                                                                           )]
    
    #В итоге мы в реальном времени получили данные о тикерах, которые прямо сейчас торгуются на MOEX
    moexTickersStocks = securityList["TRADE_CODE"].reset_index(drop=True)
    return moexTickersStocks


#Наша следующая задача - это отслеживать цены на акции в реальном времени. Для этого воспользуемся АПИ МосБиржи
#К сожалению готовых библиотек нет, поэтому пришлось парсить апи через консоль разработчика и создавать свой класс,
#содержащий методы АПИ MOEX. Также нам было бы полезно получить финансовую отчётность компании и кол-во акций на бирже по её тикеру.
#Для этого также спарсим АПИ одного из сайтов, который предоставляет такую статистику, так как в MOEX не для всех
#тикеров эта информация доступна по АПИ


#Вспомогательная функция подключения к АПИ биржи. Её мы будем вызывать в методах класса AnalizeApi, когда нам потребуется информация с MOEX
def callApi(ticker):
    url = str(f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.jsonp?iss.meta=off&iss.json=extended&callback")    
    response = requests.get(url=url)
    response =  response.json()
    return response

#Class, содержащий в себе АПИ-методы
class AnalizeApi():   
    #Создаём возможность задавать всем объектам класса динамический параметр Ticker
    def __init__(self, ticker):
        self.ticker = ticker
    
    #Метод, возвращающий информацию обо всех тикерах на бирже c MOEX, принимает на вход Ticker объекта, 
    # который мы присвоили ему ранее. На выход отдаёт информацию о всех торгуемых в данных момент инструментах на бирже
    def get_stocks(self):
        result = callApi(self.ticker)
        return result

    #Метод, возвращающий информацию о конкретной бумаге по тикеру c MOEX, принимает на вход Ticker объекта, 
    # который мы присвоили ему ранее. На выход отдаёт информацию о конкретной бумаге
    def get_stock_info(self):
        result = callApi(self.ticker)
        result = result[1]["securities"][0]
        return result
    
    #Метод, возвращающий информацию об отчётности компании за конкретный год, принимает на вход Ticker объекта и год int, 
    # на выход отдаёт отчётность компании за указанный год
    def get_report(self, year):
        url = str(f"https://financemarker.ru/api/stocks/MOEX:{self.ticker}/finance")
        period = "Y"
        reportType = "МСФО"
        response = requests.get(url=url)
        reports = response.json()["data"]["reports"]
        filteredReports = list(filter(lambda d: d['year'] == year and d['period'] == period and d['type'] == reportType, reports))
        filteredReports = dict((d['year'], d) for d in filteredReports)[year]
        return filteredReports
    
    #Метод, возвращающий информацию о рыночной информации за конкретный год, принимает на вход Ticker объекта и год int, 
    # на выход отдаёт фундаментальную статистику по бумаге за указанный год. Помогает найти информацию, которую не отдаёт мосбиржа

    def get_stocks_statistics(self, year):
        url = str(f"https://financemarker.ru/api/stocks/MOEX:{self.ticker}/finance")
        period = 12
        response = requests.get(url=url)
        shares = response.json()["data"]["shares"]
        filteredShares = list(filter(lambda d: d['year'] == year and d['month'] == period and d["code"] == self.ticker, shares))
        filteredShares = dict((d['year'], d) for d in filteredShares)[year]
        return filteredShares
        
#Подготовим данные для расчёта. Для начала по всем тикерам спарсим данные с Мосбиржи:
#Нас интересует цена акции на текущий момент, которая динамически обновляется. Тикеры, для которых
#не будет хватать данных (например, цены) мы будем пропускать методом Exception

def priceCollection(moexTickersStocks):
    prices=[]
    for ticker in tqdm(moexTickersStocks):
        try:
            price = AnalizeApi(ticker).get_stock_info()['PREVPRICE']
            prices.append([ticker,price])
        except Exception:
            pass
    return prices

#В результате мы получили массив prices, который включает в себя тикер и актуальную в моменте цену акции
#Для тикеров из массива спарсим размер equity с помощью разработанного нами метода get_report(), а также объём бумаг в обращении методом get_stocks_statistics.
#  В целом логика парсинга будет аналогична методу выше. В метод мы должны передать 2022 год как тот, за который мы хотим получить отчёт. 
# В случае, если equity будет не определён, нам следует пропустить тикер и перейти к следующему. 
# Полученный тикер нам следует умножить на 1000, так как данные нам возвращаются в тыс. руб.
#В 2022-ом году некоторые компании скрыли свою отчётность, потому в таком случае будем брать данные за 2021 год по собственному капиталу
#Объём акций в обращении будем брать так же за 2022 год
    
def equityAndSharesCollection(tickersWithPrices):
    equityList=[]
    TargerYear = 2022
    for ticker in tqdm(tickersWithPrices):
        try:
<<<<<<< HEAD
<<<<<<< HEAD
            equity = int(AnalizeApi(ticker).get_report(year = 2022)["equity"])*1000
<<<<<<< HEAD
            sharesAmount = int(AnalizeApi(ticker).get_stocks_statistics(year = 2022)["num"])

            equityList.append([ticker,equity,sharesAmount])
=======
>>>>>>> 0ca4103 (Добавлен поиск отчётности за 2021)
        except Exception:
            try:
<<<<<<< HEAD
                year = 2021
                equity = int(AnalizeApi(ticker).get_report(year)["equity"])*1000
                sharesAmount = int(AnalizeApi(ticker).get_stocks_statistics(year=2022)["num"])
                equityList.append([ticker, equity, sharesAmount])
=======
                equity = int(AnalizeApi(ticker).get_report(year = 2021)["equity"])*1000
                sharesAmount = int(AnalizeApi(ticker).get_stocks_statistics(year = 2022)["num"])
                equityList.append([ticker,equity,sharesAmount])
>>>>>>> 5b78b2c (Добавлен анализ отчётности)
=======
            print(ticker)
            ErrorCheck = "OK"
            try:
                json = AnalizeApi(ticker).get_report(year = TargerYear)
                equity = int(json["equity"]) * int(json["amount"])
>>>>>>> 3f27143 (Добавлена доп проверка кода акции)
            except Exception:
                json = AnalizeApi(ticker).get_report(year = TargerYear-1)
                equity = int(json["equity"]) * int(json["amount"])
=======
            print(ticker)
            ErrorCheck = "OK"
            try:
                json = AnalizeApi(ticker).get_report(year = TargerYear)
                equity = int(json["equity"]) * int(json["amount"])
            except Exception:
<<<<<<< HEAD
<<<<<<< HEAD
                equity = int(AnalizeApi(ticker).get_report(year = TargerYear-1)["equity"])*1000
>>>>>>> 188facd (Добавлена обработка исключений, формируется xlsx)
=======
                equity = int(AnalizeApi(ticker).get_report(year = TargerYear-1)["equity"])*1000000
>>>>>>> 06e3c43 (Скорректирован размер домножения)
=======
                json = AnalizeApi(ticker).get_report(year = TargerYear-1)
                equity = int(json["equity"]) * int(json["amount"])
>>>>>>> 08f48aa (Формируется отчёт, рассчитывается BV - NPV)
                ErrorCheck = "equityException_prevYearTaken"
            try:
                sharesAmount = int(AnalizeApi(ticker).get_stocks_statistics(year = TargerYear)["num"])
            except Exception:
                    
                sharesAmount = int(AnalizeApi(ticker).get_stocks_statistics(year = TargerYear-1)["num"])
                ErrorCheck = "sharesAmountException_prevYearTaken"
        except Exception:
            pass
        else:
            equityList.append([ticker,equity,sharesAmount, ErrorCheck])
    return equityList

def analizeFunc(tickersWithPrices, equityList):
    df = pd.merge(tickersWithPrices, equityList, how = "inner", on = "Ticker") #Джойним цены, собственный капитал и объём по тикеру
    df["BV"] = df["Equity"]/df["SharesAmount"]
    df["NPV"] = df["BV"] - df["CurrentPrice"]
    return df



#Теперь будем получать датафрейм для анализа. Чтобы это сделать, нам нужно последовательно вызвать функции:
# priceCollection, equityAndSharesCollection, изменить полученный от них ответ из формата списка в тип данных DataFrame
# и сджойнить по тикерам оба массива. В результате получим датафрейм df, с которым и будем работать.

def main():
<<<<<<< HEAD
<<<<<<< HEAD
    moexTickersStocks = tickerCollector() #Для удобства возьмём первые 10 тикеров с мосбиржи, но вообще можем хоть все, просто тогда нужно будет долго ждать
<<<<<<< HEAD
<<<<<<< HEAD
    tickersWithPrices = pd.DataFrame(priceCollection(moexTickersStocks), columns = ["Ticker", "CurrentPrice"]) #Парсим цены этих тикеров с MOEX и преобразуем в датафрейм
=======
>>>>>>> 2757835 (Добавлены прогресс бары)
    
    print("Собираем данные о ценах...")
    tickersWithPrices = priceCollection(moexTickersStocks)
    tickersWithPrices = pd.DataFrame(tickersWithPrices, columns = ["Ticker", "CurrentPrice"]) #Парсим цены этих тикеров с MOEX и преобразуем в датафрейм
=======
=======
    moexTickersStocks = tickerCollector().head() #Для удобства возьмём первые 10 тикеров с мосбиржи, но вообще можем хоть все, просто тогда нужно будет долго ждать
>>>>>>> 06e3c43 (Скорректирован размер домножения)
        
    print("Собираем данные о ценах...")
    tickersWithPrices = priceCollection(moexTickersStocks)
    tickersWithPrices = pd.DataFrame(tickersWithPrices, columns = ["Ticker", "CurrentPrice"]) #Парсим цены этих тикеров с MOEX и преобразуем в датафрейм
        
>>>>>>> 188facd (Добавлена обработка исключений, формируется xlsx)
=======
    moexTickersStocks = tickerCollector().head(10) #Для удобства возьмём первые 10 тикеров с мосбиржи, но вообще можем хоть все, просто тогда нужно будет долго ждать
    
    print("Собираем данные о ценах...")
    tickersWithPrices = priceCollection(moexTickersStocks)
    tickersWithPrices = pd.DataFrame(tickersWithPrices, columns = ["Ticker", "CurrentPrice"]) #Парсим цены этих тикеров с MOEX и преобразуем в датафрейм
>>>>>>> 08f48aa (Формируется отчёт, рассчитывается BV - NPV)
    onlytickers = tickersWithPrices["Ticker"]
    
    print("Собираем данные о рынке...")
    equityList = equityAndSharesCollection(tickersWithPrices = onlytickers) #Для всех тикеров, которые нам удалось спарсить, парсим equity и объём акций в обороте
    equityList = pd.DataFrame(equityList, columns=["Ticker", "Equity", "SharesAmount", "ExceptionType"]) #Преобразуем спаршенные собственный капитал и объём акций в датафрейм
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 08f48aa (Формируется отчёт, рассчитывается BV - NPV)
    
    print("Формируем отчёт")
    df = analizeFunc(tickersWithPrices, equityList)
    
<<<<<<< HEAD
    df.to_excel("ParsedData.xlsx", index = False)

    print("Готово, проверяйте!")
=======

    df = pd.merge(tickersWithPrices, equityList, how = "inner", on = "Ticker") #Джойним цены, собственный капитал и объём по тикеру
=======
>>>>>>> 08f48aa (Формируется отчёт, рассчитывается BV - NPV)
    df.to_excel("ParsedData.xlsx", index = False)
>>>>>>> 188facd (Добавлена обработка исключений, формируется xlsx)

    print("Готово, проверяйте!")

if __name__ == "__main__":
     main()