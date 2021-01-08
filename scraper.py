# REST API
import pyupbit
import requests
import pprint

url = "https://api.upbit.com/v1/market/all"
resp = requests.get(url)
data = resp.json() #json
pprint.pprint(data)
