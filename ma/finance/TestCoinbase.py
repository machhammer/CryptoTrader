import requests

def fetch_fear_greed_index():
    url = "https://api.alternative.me/fng/"
    response = requests.get(url)
    data = response.json()
    fear_greed_index = data['data'][0]['value']
    return fear_greed_index

def main():
    fear_greed_index = fetch_fear_greed_index()
    print("Fear and Greed Index:", fear_greed_index)

if __name__ == "__main__":
    main()