# precache - development only
This is the development repo for `precache.py`. Do not use in production!

# NOTE!!!!!
### There have been some changes made to how `precache.py` runs, please read this thoroughly and read `./precache.py --help`

## What is `precache.py`?
This is an open source utility to pre cache various files in relation to iOS/watchOS/tvOS and macOS software updates.

## Why would I use this?
The caching/tetherator service provided by Apple will purge items from the cache when they meet some basic criteria:
1. Insufficient space in the cache to store any new incoming assets
2. Existing assets have not been retrieved for more than _n_ days

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
| `cacheGroups` | List | Any from `'AppleTV', 'iPad', 'iPhone', 'iPod', 'app', 'installer', 'sucatalog'` |
| `cacheIPSW` | List | Any valid Apple model identier for Apple TV, iPad, iPhone, or iPod. In the format `iPad6,8`. To cache all IPSW files for a specifc device, simply use the model identifier without the numbers, for example: `iPad` |
| `cacheMacUpdates` | List | Any valid product ID or keyword from the `precache.py -l` output. |
| `cacheModels` | List | Any valid model identifier in the format `iPad6,8`. |
| `cacheServerPort` | Integer | The port number your cache server responds on. See note on finding the server port and address. |
| `cacheServerURL` | String | The IP address or URL of your caching server. Must include `http://`. See note on finding the server port and address. |
| `destination` | String | A folder in your local storage where you want IPSW files to be stored to. Defaults to `/tmp` of nothing is provided. |
| `mdmPassword` | String | The password used for your MDM server. Please see support note below. |
| `mdmServer` | String | The MDM server address. In the format `foo.example.org`. If your MDM server uses a specific port, in the format of `foo.example.org:8443` Please see support note below. |
| `mdmToken` | String | Currently unsupported. |
| `mdmUser` | String | The username used for your MDM server. Please see support note below. |

#### Finding your server port and address
If `/usr/bin/AssetCacheLocatorUtil` exists on your computer and no server information exists in the configuration files, or provided at the command line, `.precache.py` will attempt to find the right caching server.

#### Manually finding your server port and address
If you are running macOS Sierra or later, you can find the server your machine uses by running `/usr/bin/AssetCacheLocatorUtil 2>&1 | awk '/rank 1/ {print $4 $5}' | sed 's/,rank//g' | uniq`.

If you get more than one server list back, select the one that you wish to run `precache.py` against.

If you are using macOS Server.app you can also get the information for that server by running `sudo serveradmin fullstatus caching` on the caching server.

#### MDM support
iOS and tvOS model information can be retrieved from an MDM. Presently only Jamf Cloud/JSS instances are supported.

You can configure the credentials and server in the configuration file as outlined in the User configurable options section above, or provide them from the command line.

Any models supplied with the `-m,--models` argument are ignored when MDM arguments are used.

## Running `precache.py` as a LaunchDaemon
To run `precache.py` as a LaunchDaemon, you can do the following:
1. Make a copy of the configuration file as per steps outlined in the `Configuration File` section.
2. Make changes to the configuration file as per the `User configuration options`.
3. Copy `com.github.krypted.precache.daemon.plist` to `/Library/LaunchDaemons` and make sure ownership and permissions are correct by running `chmod 644 /Library/LaunchDaemons/com.github.krypted.precache.daemon.plist && chown root:wheel /Library/LaunchDaemons/com.github.krypted.precache.daemon.plist`
4. If you wish to modify the day(s) or time that the daemon runs at, modify the `/Library/LaunchDaemons/com.github.krypted.precache.daemon.plist` file.
5. Run `/bin/launchctl load /Libary/LaunchDaemons/com.github.krypted.precache.daemon.plist`
