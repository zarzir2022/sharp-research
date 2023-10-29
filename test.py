
import requests
import pandas as pd


def callApi(ticker):
    if ticker != None:
        url = str(f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.jsonp?iss.meta=off&iss.json=extended&callback")    
    else:
        url = str(f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.jsonp?iss.meta=off&iss.json=extended&callback")
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
    
    def get_report(self, year):
        url = str(f"https://financemarker.ru/api/stocks/MOEX:{self.ticker}/finance")
        period = "Y"
        response = requests.get(url=url)
        reports = response.json()["data"]["reports"]
        filteredReports = list(filter(lambda d: d['year'] == year and d['period'] == period, reports))
        filteredReports = dict((d['year'], d) for d in filteredReports)[year]
        return filteredReports
    
    #Метод, возвращающий информацию о рыночной информации за конкретный год, принимает на вход Ticker объекта и год int, 
    # на выход отдаёт фундаментальную статистику по бумаге за указанный год. Помогает найти информацию, которую не отдаёт мосбиржа

    def get_stocks_statistics(self, year):
        url = str(f"https://financemarker.ru/api/stocks/MOEX:{self.ticker}/finance")
        period = 12
        response = requests.get(url=url)
        shares = response.json()["data"]["shares"]
        filteredShares = list(filter(lambda d: d['year'] == year and d['month'] == period, shares))
        filteredShares = dict((d['year'], d) for d in filteredShares)[year]
        return filteredShares
        
        

def priceCollection(moexTickersStocks):
    equityList=[]
    for ticker in moexTickersStocks:
        try:
            if AnalizeApi(ticker).get_report(2022)["year"]==2022:
                year = 2022
            else:
                year = 2021
            equity = int(AnalizeApi(ticker).get_report(year)["equity"])*1000
            sharesAmount = int(AnalizeApi(ticker).get_stocks_statistics(year=2022)["num"])
            equityList.append([ticker,equity,sharesAmount])
        except Exception:
            pass
    return equityList

#В результате мы получили массив prices, который включает в себя тикер, цену акции, капитализацию бумаги и количество ценных бумаг в обращении
#Для тикеров из массива спарсим размер equity с помощью разработанного нами метода get_report(). В целом логика парсинга будет аналогична
#методу выше. В метод мы должны передать 2022 год как тот, за который мы должны получить отчёт. В случае, если equity будет не определён,
#нам следует пропустить тикер и перейти к следующему. Полученный тикер нам следует умножить на 1000, так как данные нам возвращаются в тыс. руб.
    
def equityAndSharesCollection(tickersWithPrices):
    equityList=[]
    for ticker in tickersWithPrices:
        try:
            year = 2022
            equity = int(AnalizeApi(ticker).get_report(year)["equity"])*1000
            sharesAmount = int(AnalizeApi(ticker).get_stocks_statistics(year=2022)["num"])
            equityList.append([ticker,equity,sharesAmount])
        except Exception:
            try:
                year = 2021
                equity = int(AnalizeApi(ticker).get_report(year)["equity"])*1000
                sharesAmount = int(AnalizeApi(ticker).get_stocks_statistics(year=2022)["num"])
                equityList.append([ticker, equity, sharesAmount])
            except Exception:
                pass
    return equityList
        

print(equityAndSharesCollection(["AFLT","LKOH", "OGKB"]))