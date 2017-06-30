# precache - development only
This is the development repo for `precache.py`. Do not use in production!

## Release notes - v2.0.2
- Implemented correct usage of `requests.head` to speed up the `already_cached()` function.
- Logging implemented. Logs to `/tmp/precache.log`.


## Release notes - v2.0.1
- Implemented switch over to the `requests` module for python. You will be prompted to install this if it isn't importable.
- Implemented Jamf/JSS and SimpleMDM as sources for MDM. See the `mdm` key in the User configurable options section below.

## Release notes - v2.0.0
### Current version changes
- Pull models from Jamf/JSS MDM. Additional MDM support slowly being added.
- Command line arguments have been simplified. Check `./precache.py --help` for more information
- Can now configure a number of options in a configuration file. See `Configuration file` section below for more information.
- Dropped the old download code in favour of using the `/usr/bin/curl` system binary.
- Fixed the bug where ipsw files would not be written to disk properly.

### Future changes
- Update 2017-06-25: Support for caching Mac App Store apps is staying,  _for now_, future versions may only support caching macOS Installer apps.
- - Support for caching Mac App Store apps is going to be removed in the next release. Keeping the URL's updated is a time consuming task that doesn't appear possible to automate. The only way this feature is likely to remain is if there are people willing to keep those URL's updated as Apple releases updates. If you're interested in finding out how to do this, raise an issue with the label `contribute`.

## What is `precache.py`?
This is an open source utility to pre cache various files in relation to iOS/watchOS/tvOS and macOS software updates.

## Why would I use this?
The caching/tetherator service provided by Apple will purge items from the cache when they meet some basic criteria:
1. Insufficient space in the cache to store any new incoming assets.
2. Existing assets have not been retrieved for more than _n_ days.

`precache.py` allows you to keep those items in your cache almost _indefinitely_, as well as a means to ensure big updates (such as iOS releases) are already cached for your eager users to download while attached to your network, thus saving precious bandwidth (spot the Aussie!).

## How do I use this?
First, you'll need to clone the repo _somewhere_.
1. `cd` into the location you wish to use this from, for example: `cd /usr/local/bin`.
2. `git clone https://github.com/carlashley/precache_dev`.
3. `cd precache_dev && chmod +x precache.py`.
4. `./precache.py` for the help output, `./precache.py -l` for the list of updates available.

## Configuration file
`precache.py` can be configured using a configuration profile, a template (`com.github.krypted.precache.example-config.plist`) exists which can be copied and then modified to suit your needs. This is handy for circumstances where you wish to run this as a LaunchDaemon, or the items to be cached rarely change.

Copy the existing `com.github.krypted.precache.example-config.plist` and rename it to `com.github.krypted.precache.my-config.plist`.

Modify relevant settings in the file with your favourite text editor. Do not use `defaults write` on this file as it will convert it to a binary plist, which is not readable by `precache.py`

### User configurable options
| Preference Key | Type | Value |
| -------------- | ---- | ----- |
| `cacheApps` | Array | Any app or macOS installer as per the `precache.py -l` output. |
| `cacheGroups` | Array | Any from `'AppleTV', 'iPad', 'iPhone', 'iPod', 'app', 'installer', 'sucatalog'`. |
| `cacheIPSW` | Array | Any valid Apple model identier for Apple TV, iPad, iPhone, or iPod. In the format `iPad6,8`. To cache all IPSW files for a specifc device, simply use the model identifier without the numbers, for example: `iPad`. |
| `cacheMacUpdates` | Array | Any valid product ID or keyword from the `precache.py -l` output. |
| `cacheModels` | Array | Any valid model identifier in the format `iPad6,8`. |
| `cacheServerPort` | Integer | The port number your cache server responds on. See note on finding the server port and address. |
| `cacheServerURL` | String | The IP address or URL of your caching server. Must include `http://`. See note on finding the server port and address. |
| `destination` | String | A folder in your local storage where you want IPSW files to be stored to. Defaults to `/tmp` of nothing is provided. |
| `mdm` | String | `jamf` or `simplemdm`. Used to specify which MDM provider to pull from. |
| `mdmPassword` | String | The password used for your MDM server. Please see support note below. |
| `mdmServer` | String | The MDM server address. In the format `foo.example.org`. If your MDM server uses a specific port, in the format of `foo.example.org:8443` Please see support note below. |
| `mdmToken` | String | The token provided by your MDM for use with the API. |
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

**Note** _Only use accounts with read only access, or other similar type of service accounts._

Any models supplied with the `-m,--models` argument are ignored when MDM arguments are used.

## Running `precache.py` as a LaunchDaemon
To run `precache.py` as a LaunchDaemon, you can do the following:
1. Make a copy of the configuration file as per steps outlined in the `Configuration File` section.
2. Make changes to the configuration file as per the `User configuration options`.
3. Copy `com.github.krypted.precache.daemon.plist` to `/Library/LaunchDaemons` and make sure ownership and permissions are correct by running `chmod 644 /Library/LaunchDaemons/com.github.krypted.precache.daemon.plist && chown root:wheel /Library/LaunchDaemons/com.github.krypted.precache.daemon.plist`.
4. If you wish to modify the day(s) or time that the daemon runs at, modify the `/Library/LaunchDaemons/com.github.krypted.precache.daemon.plist` file.
5. Run `/bin/launchctl load /Libary/LaunchDaemons/com.github.krypted.precache.daemon.plist`.


## Requirements
This is tested on a macOS Sierra system with `python 2.7.10`. No third party modules/eggs are required.

**Reminder** Future releases will require the `requests` module to be installed, so please make sure you've got this in the environment that you run this in!

## Security
Certain processes within this script rely on the `urllib2` module, and others utilise the system binary `/usr/bin/curl`; an assumption is made that these are both HTTPS capable.

If you are concerned about any data from your MDM being interecepted, then you should avoid using the MDM capability and instead maintain a list of models to cache items for within the configuration file.

## Bugs/issues/pull requests
If you see bugs or issues with this, please raise an issue that includes the arguments that `precache.py` was run with.

If you wish to contribute to testing various MDM API's, please raise an issue as well. I'm specifically looking for SimpleMDM and Meraki testers to start with. It will help if you're familiar with python.
