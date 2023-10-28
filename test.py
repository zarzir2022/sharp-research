import requests

url = str(f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities")
response = requests.get(url=url)
response =  response.json()
    
print(response)