# precache - development only
This is the development repo for `precache.py`. Do not use in production!

## What is `precache.py`?
This is an open source utility to pre cache various files in relation to iOS/watchOS/tvOS and macOS software updates.

## Why would I use this?
The caching/tetherator service provided by Apple will purge items from the cache when they meet some basic criteria:
1. Insufficient space in the cache to store any new incoming assets
2. Existing assets have not been retrieved for more than n days

`precache.py` allows you to keep those items in your cache almost _indefinitely_, as well as a means to ensure big updates (such as iOS releases) are already cached for your eager users to download while attached to your network, thus saving precious bandwidth (spot the Aussie!).

## How do I use this?
First, you'll need to clone the repo _somewhere_.
1. `cd` into the location you wish to use this from, for example: `cd /usr/local/bin`
2. `git clone https://github.com/carlashley/precache_dev`
3. `cd precache_dev && chmod +x precache.py`
