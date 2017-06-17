#!/usr/bin/python

import plistlib
import pprint

pp = pprint.PrettyPrinter(depth=None)

plist = 'com.github.krypted.precache.example-config.plist'
# configuration = plistlib.readPlist(plist)
configuration = {
    'appsCanCache': 'https://raw.githubusercontent.com/krypted/precache/master/com.github.krypted.precache.apps-list.plist',  # NOQA
    'cacheServerConfigPlist': '/Library/Server/Caching/Config/Config.plist',
    'cacheServerPort': '53612',
    'cacheServerURL': 'http://cacheserver',
    'cacheModels': ['AppleTV5,3'],
    'cacheIPSW': ['iPad6,8'],
    'cacheApps': ['Server', 'Sierra'],
    'cacheGroups': [],
    'cacheMacUpdates': [],
    'destination': '/tmp',
    'iosBaseURL': 'http://mesu.apple.com/assets/',
    'iosFeeds': {'ios': 'com_apple_MobileAsset_SoftwareUpdate/com_apple_MobileAsset_SoftwareUpdate.xml',  # NOQA
                 'tv': 'tv/com_apple_MobileAsset_SoftwareUpdate/com_apple_MobileAsset_SoftwareUpdate.xml',  # NOQA
                 'watch': 'watch/com_apple_MobileAsset_SoftwareUpdate/com_apple_MobileAsset_SoftwareUpdate.xml'},  # NOQA
    'mdmPassword': 'aPassword',
    'mdmServer': 'foo.example.org:9000',
    'mdmUser': 'aUser',
    'mdmToken': '05cf21d7f2adaf6793b9063e8e58d0ce3e21411e4f54fc79f6470d90a27a4609',  # NOQA
    'logLevel': 'debug',
    'logPath': '/tmp/precache.log',
    'masBaseURL': 'http://osxapps.itunes.apple.com/',
    'softwareUpdateFeed': {
        'all': 'content/catalogs/others/index-10.12-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog',  # NOQA
        'sierra': 'content/catalogs/others/index-10.12.merged-1.sucatalog'},
    'sucatalogExcludes': ['Voice Update',
                          'Mountain Lion',
                          'Lion',
                          'Snow Leopard',
                          'Leopard',
                          'Tiger',
                          'Panther',
                          'Jaguar',
                          'Puma',
                          'Cheetah',
                          'Kodiak',
                          'Printer',
                          'Java',
                          'Flash',
                          'Logic Pro',
                          'GarageBand',
                          'Pages',
                          'Keynote',
                          'Numbers',
                          'Speech',
                          'iPhone',
                          'Dictation',
                          'MainStage',
                          'QuickTime',
                          'Final Cut Pro',
                          'FontAssets',
                          'Bluetooth',
                          'Photo Content',
                          'VoiceOver',
                          'Motion',
                          'MRTConfig',
                          'Mac OS X Server',
                          'Chinese',
                          'Driver',
                          'Developer',
                          'Preview',
                          'Beta',
                          'iAd',
                          'Kernel',
                          '10.9',
                          '10.8',
                          '10.7',
                          '10.6',
                          '10.5',
                          '10.4',
                          '10.3',
                          '10.2',
                          '10.1',
                          '10.0',
                          'iPhoto',
                          'Rosetta',
                          'SafeView',
                          'NRT',
                          'AppleDisplays',
                          'Apple Directory',
                          'AppleConnect',
                          'App Store',
                          'BlueTooth',
                          'GateKeeper',
                          'Noticeboard',
                          'CoreSuggestions',
                          'Pro Video',
                          'Beats',
                          'XProtect',
                          'Installer Notification',
                          'Technology Preview',
                          'Remote Desktop',
                          'System Integrity',
                          'BootCamp',
                          'Configuration Data',
                          'iTunes Producer',
                          'RAW'],
    'swuBaseURL': 'https://swscan.apple.com/',
    'tetheratorConfigPlist': '/Library/Preferences/com.apple.AssetCache.plist',
    'userAgentString': 'precache'}

# pp.pprint(configuration)

plistlib.writePlist(configuration, plist)
