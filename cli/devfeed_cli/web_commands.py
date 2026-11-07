"""Handler for web: opens the web app page that goes with the API address.

No API call. The web address is --web-url when given; otherwise local
runserver (port 8000) maps to the Vite dev server, and any other API
address (the live site, Docker on port 8080) serves the web app from the
same origin.
"""

import webbrowser
from urllib.parse import urlparse

from .api_client import normalize_api_url
from .errors import DevfeedError

# Vite's dev server; "localhost" (not 127.0.0.1) because the browser keeps
# its login per origin and the web app is used at localhost:5173
LOCAL_VITE_WEB_URL = "http://localhost:5173"
LOCAL_RUNSERVER_HOSTS = ("127.0.0.1:8000", "localhost:8000")

WEB_PAGE_PATHS = {"feed": "/", "saved": "/saved", "keywords": "/keywords"}


def choose_web_url(api_url, web_url_option):
    """--web-url first, then Vite for local runserver, else the API's origin."""
    if web_url_option:
        return normalize_api_url(web_url_option)
    parsed_api_url = urlparse(api_url)
    if parsed_api_url.netloc in LOCAL_RUNSERVER_HOSTS:
        return LOCAL_VITE_WEB_URL
    # Same origin: NGINX serves the web app and proxies /api/ to Django
    return f"{parsed_api_url.scheme}://{parsed_api_url.netloc}"


def handle_web(api_client, arguments):
    """Open the feed, saved or keywords page in the browser."""
    web_url = choose_web_url(api_client.api_url, arguments.web_url)
    if urlparse(web_url).scheme not in ("http", "https"):
        raise DevfeedError("Not opening this link: only http and https links are opened.")
    page_url = web_url + WEB_PAGE_PATHS[arguments.page]
    # webbrowser.open returns False when no browser could be started
    if not webbrowser.open(page_url):
        raise DevfeedError(f"Couldn't open a browser for {page_url}")
    print(f"Opened {page_url} (the browser has its own login)")
