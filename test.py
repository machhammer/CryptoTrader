import requests

url = "https://cryptopanic.com/api/v1/posts/"
params = {
    "auth_token": "baa901ccc69f264d33369c021ac1012205eefb62",  # replace with your key
    "filter": "hot",               # hot | rising | bullish | bearish | important | lol
    "public": "true"               # public news only
}

response = requests.get(url, params=params)
data = response.json()

# Display some results
for post in data.get('results', []):
    print(f"{post['published_at']} - {post['title']}")