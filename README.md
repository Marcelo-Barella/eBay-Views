# Simple eBay Viewbot

# How it works:

- User acquires HTTP/HTTPS proxies, inputs URL, desired amount of views, and the maximum amount of threads to run at once
- Threads created, UserAgent generated, the request will made with a random proxy from list

## Proxy quality testing
>  Proxy will be tested for:
- quality
- anonymity
- speed
- reliability
- security
- privacy
- legality
At the end of the testing, the proxy will be added to the list of proxies that are working on a file called proxies_quality.json
The proxies have 3 chances to pass the tests, if they fail, they will be removed from the list

# How to use:

### Dependencies

- Python 3.10
- fake_useragent
- requests

### How to use:

- Create a file called proxies.txt and put the proxies in the file
- Run the command below:
```sh
python proxy_quality_tester.py
```
- Run the command below:
```sh
python viewbot.py
```