#https://finrange.com/ru/company/MOEX/KRSB/financial-statements

import requests
import pandas as pd

pd.set_option('display.max_rows', None)

def tickerCollector():
    file = "https://www.moex.com/ru/listing/securities-list-csv.aspx?type=1"
    securityList = pd.read_csv(file, sep=',', encoding='cp1251')
    #headers = securityList.columns
    #Анализируем колонки, которые нам могут помочь. Внимание привлекли колонки TRADE_CODE и INSTRUMENT_CATEGORY
    #Наша задача - отобрать только акции и запомнить их тикеры, что затем узнать текущие цены на инструменты
    #на бирже
    securityList = securityList[["INSTRUMENT_CATEGORY","TRADE_CODE"]]
    #Мы отберем тикеры по двум фильтрам - по слову акции в категориях инструменты
    #И по длине торгового кода - максимальная его длина составляет 6
    securityList = securityList[
                                (securityList["INSTRUMENT_CATEGORY"].str.contains("акции|Акции"))&
                                (securityList["TRADE_CODE"].str.len()<=6
                                                                           )]
    
    #В итоге мы в реальном времени получили данные о тикерах, которые прямо сейчас торгуются на MOEX
    moexTickersStocks = securityList["TRADE_CODE"].reset_index(drop=True)
    return moexTickersStocks


#Наша следующая задача - это отслеживать цены на акции в реальном времени. Для этого воспользуемся АПИ МосБиржи
#К сожалению готовых библиотек нет, поэтому пришлось парсить апи через кконсоль разработчика и создавать свой класс,
#Содержащий методы АПИ MOEX. Также нам было бы полезно получить финансовую отчётность компании по её тикеру.
#Для этого также спарсим АПИ одного из сайтов, который предоставляет такую статистику


def callApi(ticker):
    url = str(f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.jsonp?iss.meta=off&iss.json=extended&callback")    
    response = requests.get(url=url)
    response =  response.json()
    return response

#API
class AnalizeApi():   
    
    def __init__(self, ticker):
        self.ticker = ticker
    
    #Метод, возвращающий информацию обо всех тикерах на бирже c MOEX
    def get_stocks(self):
        result = callApi(self.ticker)
        return result

    #Метод, возвращающий информацию о конкретной бумаге по тикеру c MOEX
    def get_stock_info(self):
        result = callApi(self.ticker)
        result = result[1]["marketdata"][0]
        return result
    
    #Метод, возвращающий информацию об отчётности компании за конкретный год
    def get_report(self, year):
        url = str(f"https://financemarker.ru/api/stocks/MOEX:{self.ticker}/finance")
        period = "Y"
        response = requests.get(url=url)
        reports = response.json()["data"]["reports"]
        filteredReports = list(filter(lambda d: d['year'] == year and d['period'] == period, reports))
        filteredReports = dict((d['year'], d) for d in filteredReports)[year]
        return filteredReports
    
    #Метод, возвращающий информацию о рыночной информации за конкретный год
    def get_stocks_statistics(self, year):
        url = str(f"https://financemarker.ru/api/stocks/MOEX:{self.ticker}/finance")
        period = 12
        response = requests.get(url=url)
        shares = response.json()["data"]["shares"]
        filteredShares = list(filter(lambda d: d['year'] == year and d['month'] == period, shares))
        filteredShares = dict((d['year'], d) for d in filteredShares)[year]
        return filteredShares
        
    
#Подготовим данные для расчёта. Для начала по всем тикерам спарсим данные с Мосбиржи:
#Цену акции на текущий момент, её капитализацию на текущий момент и
#Количество выпущенных акций = Капитализация/Цена акции. Тикеры, для которых
#не будет хватать данных (например, цены или капитализации), мы будем пропускать

def priceCollection(moexTickersStocks):
    prices=[]
    for ticker in moexTickersStocks:
        try:
            price = AnalizeApi(ticker).get_stock_info()['LAST']
            prices.append([ticker,price])
        except Exception:
            pass
    return prices

#В результате мы получили массив prices, который включает в себя тикер, цену акции, капитализацию бумаги и количество ценных бумаг в обращении
#Для тикеров из массива спарсим размер equity с помощью разработанного нами метода get_report(). В целом логика парсинга будет аналогична
#методу выше. В метод мы должны передать 2022 год как тот, за который мы должны получить отчёт. В случае, если equity будет не определён,
#нам следует пропустить тикер и перейти к следующему. Полученный тикер нам следует умножить на 1000, так как данные нам возвращаются в тыс. руб.
    
def equityAndSharesCollection(tickersWithPrices):
    equityList=[]
    for ticker in tickersWithPrices:
        try:
            equity = int(AnalizeApi(ticker).get_report(year = 2022)["equity"])*1000
            sharesAmount = int(AnalizeApi(ticker).get_stocks_statistics(year = 2022)["num"])

            equityList.append([ticker,equity,sharesAmount])
        except Exception:
            pass
    return equityList



#Теперь будем получать датафрейм для анализа. Чтобы это сделать, нам нужно последовательно вызвать функции:
#priceCollection, equityAndSharesCollection и объединить их аутпуты по тикерам

def main():
    moexTickersStocks = tickerCollector().head(10)
    tickersWithPrices = pd.DataFrame(priceCollection(moexTickersStocks), columns = ["Ticker", "CurrentPrice"]) #Парсим цены этих тикеров с MOEX
    
    equityList = equityAndSharesCollection(tickersWithPrices = tickersWithPrices["Ticker"]) #Для всех тикеров, которые нам удалось спарсить, парсим equity
    equityList = pd.DataFrame(equityList, columns=["Ticker", "Equity", "SharesAmount"]) #Преобразуем спаршенные equity в датафрейм

    df = pd.merge(tickersWithPrices, equityList, how = "inner", on = "Ticker")
    print(df)

if __name__ == "__main__":
     main()