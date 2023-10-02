from mastodon import Mastodon
from pprint import pprint

"""
Mastodon.create_app(
    "pytooterapp",
    api_base_url="https://mastodon.social",
    to_file="pytooter_clientcred.secret",
)
"""

mastodon = Mastodon(
    client_id="pytooter_clientcred.secret",
)
mastodon.log_in(
    "machhammer@gmx.net",
    "cUgqom-5zuvco-qoqbuz",
    to_file="pytooter_usercred.secret",
)


mastodon = Mastodon(access_token="pytooter_usercred.secret")

result = mastodon.search(q="crypto", result_type="accounts")
print(result)
