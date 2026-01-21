import requests

base_url = f"https://www.amazon.com/s?k=data+engineering+books"

books = []
seen_titles = set()  # To keep track of seen titles
headers = {
    "Referer": 'https://www.amazon.com/',
    "Sec-Ch-Ua": "Not_A Brand",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": "macOS",
    'User-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
}

page = 1

while len(books) < 2:
    url = f"{base_url}&page={page}"
    
    # Send a request to the URL
    response = requests.get(url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        print(response)


        page += 1
    
    else:

        print(f"Failed to retrieve the webpage. Status code: {response.status_code}")

        break
