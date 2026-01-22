from datetime import datetime, timedelta
import json
import requests


url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
params = {
    "format": "geojson",
    "starttime": (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
    "endtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
    "minmagnitude": 2.5,
    "limit": 100  # limit for example, can be adjusted
}

response = requests.get(url, params=params)
response.raise_for_status()


# now convert the responce to json data type 
data = response.json()
print(data)