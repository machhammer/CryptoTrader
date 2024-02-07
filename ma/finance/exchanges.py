import ccxt
import credentials


def cryptocom():
    api_key = credentials.provider_2.get("key")
    api_secret = credentials.provider_2.get("secret")

    config = {"apiKey": api_key, "secret": api_secret, "enableRateLimit": True}

    exchange = ccxt.cryptocom(
        {
            "apiKey": api_key,
            "secret": api_secret,
            #'verbose': True
        }
    )
    return exchange


def coinbase():
    api_key = credentials.provider_2.get("key")
    api_secret = credentials.provider_2.get("secret")

    config = {"apiKey": api_key, "secret": api_secret, "enableRateLimit": True}

    exchange = ccxt.cryptocom(
        {
            "apiKey": api_key,
            "secret": api_secret,
            #'verbose': True
        }
    )
    return exchange