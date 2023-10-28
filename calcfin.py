import requests
import pandas as pd

def tickerCollector():
    file = "https://www.moex.com/ru/listing/securities-list-csv.aspx?type=1"
    securityList = pd.read_csv(file, sep=',', encoding='cp1251')
    headers = securityList.columns
    print(headers)
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
    securityList = securityList["TRADE_CODE"].reset_index(drop=True)
    return securityList


def callApi(ticker):
    if ticker != None:
        url = str(f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.jsonp?iss.meta=off&iss.json=extended&callback")    
    else:
        url = str(f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.jsonp?iss.meta=off&iss.json=extended&callback")
    response = requests.get(url=url)
    response =  response.json()
    return response

#API
class MOEXApi():   
    
    def __init__(self, ticker):
        self.ticker = ticker
    
    #Метод, возвращающий информацию обо всех тикерах на бирже
    def get_stocks(self):
        result = callApi(self.ticker)
        return result

    #Метод, возвращающий информацию о конкретной бумаге по тикеру
    def get_stock_info(self):
        result = callApi(self.ticker)
        result = result[1]["marketdata"][0]

    #Метод, возвращающий информацию о цене конкретной бумаги по тикеру
    def get_stock_last_price(self):
        result = callApi(self.ticker)
        result = result[1]["marketdata"][0]["LAST"]
        return result
    

def priceCollection():
    prices=[]
    moexTickers = ["LKOH", "LENT", "PHOR"]
    for ticker in moexTickers:
        price = MOEXApi(ticker).get_stock_last_price()
        prices.append(price)
    return prices
    

def main():
    tickerCollector()
    


if __name__ == "__main__":
     main()
