# python-socks5-serval
Automatically exported from code.google.com/p/python-socks5

## DIRTY HACK!!! DO NOT USE!!! PROOF OF CONCEPT

python-socks5 tweaked to detect serval SIDs as target addresses. A servald binary must be present in PATH. SOCKS client must be set to resolve hostnames through the proxy.

Additional documentation: http://otg-living.blogspot.de/2016/02/one-proxy-to-rule-them-all.html

## Usage
Example:

Terminal 1:

`$ python socks5.py`

Terminal 2:

`$ curl --socks5-hostname localhost:1080 http://6A8ABC599B3BF4CA53D034C3CF4DFF0F5122A81E895FA6510EFF8939AA91C5BB`

## Tips for server side setup

Make your legacy services reachable through serval and msp:

`$ servald msp listen --forward=8000 80`

Forwards any incoming msp connection on port 80 to the local tcp port 8000.
