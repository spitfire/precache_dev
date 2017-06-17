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
4. `./precache.py` for the help output, `./precache.py -l` for the list of updates available.

## Configuration file
`precache.py` can be configured using a configuration profile, a template (`com.github.krypted.precache.example-config.plist`) exists which can be copied and then modified to suit your needs. This is handy for circumstances where you wish to run this as a LaunchDaemon, or the items to be cached rarely change.

Copy the existing `com.github.krypted.precache.example-config.plist` and rename it to `com.github.krypted.precache.my-config.plist`.

Modify relevant settings in the file with your favourite text editor. Do not use `defaults write` on this file as it will convert it to a binary plist, which is not readable by `precache.py`

### User configurable options
| Preference Key | Type | Value |
| -------------- | ---- | ----- |
| `cacheApps` | List | Any app or macOS installer as per the `precache.py -l` output |
| `cacheGroups | List | Any from `'AppleTV', 'iPad', 'iPhone', 'iPod', 'app', 'installer', 'sucatalog'` |
| `cacheIPSW` | List | Any valid Apple model identier for Apple TV, iPad, iPhone, or iPod. In the format `iPad6,8`. To cache all IPSW files for a specifc device, simply use the model identifier without the numbers, for example: `iPad` |
| `cacheMacUpdates` | List | Any valid product ID or keyword from the `precache.py -l` output. |
