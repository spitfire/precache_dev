#!/usr/bin/python
import argparse
import collections
import hashlib
import logging
import os
import subprocess
import sys
# import xml.etree.ElementTree as ET

try:
    import requests
    from requests.auth import HTTPBasicAuth
except:
    print 'Please install the requests module: sudo pip install requests'  # NOQA
    print 'Information about the module: http://docs.python-requests.org/en/master/'  # NOQA
    sys.exit(1)

from datetime import datetime
from logging.handlers import RotatingFileHandler
from operator import attrgetter
from plistlib import readPlist
from plistlib import readPlistFromString
from random import uniform
from time import sleep
from urlparse import urljoin
from urlparse import urlparse

script_name = 'precache.py'
__author__ = 'Charles Edge and Carl Windus'
__copyright__ = 'Copyright 2016, Charles Edge, Carl Windus'
__version__ = '2.0.1'
__date__ = '2017-06-25'

__license__ = 'Apache License, Version 2.0'
__maintainer__ = 'Carl Windus: https://github.com/carlashley/precache_dev'
__status__ = 'development'


class PreCache():
    def __init__(self, destination=None, dry_run=None, server=None, use_config=None):  # NOQA
        '''Initialises the class with supplied arguments, and loads
        configuration information if present in the config plist.'''
        # Logging
        self.log_file = '/tmp/precache.log'
        self.log = logging.getLogger('precache')
        self.log.setLevel(logging.DEBUG)
        self.log_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")  # NOQA
        self.fh = RotatingFileHandler(self.log_file, maxBytes=(1048576*5), backupCount=7)  # NOQA Logs capped at ~5MB
        self.fh.setFormatter(self.log_format)
        self.log.addHandler(self.fh)

        # Configuration variables
        # This is an example configuration file, please copy this plist and
        # modify it with your own configuration data, and update this variable
        # to point to the right file.

        custom_config_file = 'com.github.krypted.precache.my-config.plist'
        default_config_file = 'com.github.krypted.precache.example-config.plist'  # NOQA

        try:
            self.configuration = self.load_config(custom_config_file)
            self.log.info('Loaded configuration from %s' % custom_config_file)
        except:
            try:
                self.configuration = self.load_config(default_config_file)
                self.log.info('Loaded configuration from %s' % default_config_file)  # NOQA
            except:
                print 'No configuration file found.'
                self.log.info('No configuration file found.')
                sys.exit(1)

        if dry_run:
            self.dry_run = dry_run
            self.log.debug('Dry run enabled')
        else:
            self.dry_run = False

        # Storage destination for downloaded items
        if destination:
            self.destination = destination
        else:
            try:
                self.destination = self.configuration['destination']
            except:
                self.destination = '/tmp'
        self.log.debug('Output destination: %s' % self.destination)

        try:
            self.user_agent = '%s/%s' % (configuration['userAgentString'], __version__)  # NOQA
        except:
            self.user_agent = 'precache/%s' % __version__
        self.log.debug('User Agent: %s' % self.user_agent)

        self.write_out('Locating caching/tetherator server')
        if server:
            self.server = self.valid_server(server)
        else:
            try:
                self.server = self.valid_server('%s:%s' % (self.configuration['cacheServerURL'], self.configuration['cacheServerPort']))  # NOQA
            except:
                self.server = self.valid_server(self.cache_server())
        self.log.info('Caching server: %s' % self.server)

        # Update location and destination.
        self.write_out('Locating caching/tetherator server %s. Destination: %s' % (self.server, self.destination))  # NOQA
        print ''

        self.mac_model = self.hardware_model()
        self.sucatalog = urljoin(self.configuration['swuBaseURL'], self.configuration['softwareUpdateFeed']['all'])  # NOQA

        # iOS Devices
        self.ios_devices = ['iPad', 'iPhone', 'iPod']

        # Asset groups
        self.asset_groups = ['AppleTV', 'iPad', 'iPhone', 'iPod', 'app', 'installer', 'sucatalog']  # NOQA

        # Models that have ipsw files downloadable from Apple
        self.ipsw_capable = ['AppleTV', 'iPad', 'iPhone', 'iPod']

        # Source URLs that apple uses
        self.apple_sources = ['appldnld.apple.com', 'mesu.apple.com', 'osxapps.itunes.apple.com', 'swcdn.apple.com', 'swscan.apple.com']  # NOQA
        # Named Tuple for the item. This is as wide catching as possible.
        self.Asset = collections.namedtuple('Asset', ['model',
                                                      'model_description',
                                                      'version',
                                                      'urls',
                                                      'group',
                                                      'product_id',
                                                      'product_title',
                                                      'release_date',
                                                      'sha_digest'])

        # Stops models/ipsw files/apps etc being used from the configuration
        # file if this is being used with arguments
        if use_config:
            self.use_config = True
        else:
            self.use_config = False

    def already_cached(self, asset_url):
        '''Checks if an item is already cached. This is indicated in the
        headers of the file being checked.'''
        try:
            req = requests.get(asset_url, headers={'user-agent': self.user_agent}, timeout=10)  # NOQA
            if req.headers.get('Content-Type') is not None:
                # Item is not in cache
                self.log.debug('Not in cache: %s' % asset_url)
                return False
            else:
                # Item is already cached
                self.log.info('Already in cache: %s' % asset_url)
                return True
        except:
            # In case there is an error, we should return false anyway as there
            # is no harm in re-downloading the item if it's already downloaded.
            return False

    def app_updates(self):
        '''Returns a generator object with all macOS apps that we can cache.
        Note, this list may not be up to date with the Mac App Store versions
        as this relies on manually updating the remote feed.'''
        try:
            app_feed = self.configuration['appsCanCache']
            apps = self.read_feed(app_feed)
            for item in apps:
                asset = self.asset(
                    model=self.mac_model,
                    version=apps[item]['version'],
                    urls=[self.reformat_url(apps[item]['url'])],
                    group=apps[item]['type'],
                    product_title=item,
                )
                yield asset
            self.log.debug('Loaded apps from feed: %s' % app_feed)
        except:
            self.log.debug('Unable to load apps from GitHub feed.')
            raise

    def asset(self, model=None, model_description=None, version=None, urls=None, group=None, product_id=None, product_title=None, release_date=None, sha_digest=None):  # NOQA
        return self.Asset(
            model=model,
            model_description=model_description,
            version=version,
            urls=urls,
            group=group,
            product_id=product_id,
            product_title=product_title,
            release_date=release_date,
            sha_digest=sha_digest
        )

    def cache_server(self):
        '''Gets the Caching/Tetherator server address, by checking
        Caching/Tetherator configurations.'''
        # Two places a config file can exist depending on whether this is
        # Caching Server in Server.app or a tetherator machine.
        config_plists = [self.configuration['tetheratorConfigPlist'],
                         self.configuration['cacheServerConfigPlist']]
        try:
            plist = [x for x in config_plists if os.path.exists(x)][0]
            self.log.debug('Found caching server plist: %s' % plist)
        except:
            plist = False
            self.log.debug('No caching server plist found.')

        if plist:
            # Fall back to testing if Caching Server/Server.app or tetherator
            try:
                port = readPlist(plist)['LastPort']
            except:
                try:
                    port = readPlist(plist)['Port']
                except:
                    self.log.debug('No port for caching server found in %s' % plist)  # NOQA
                    raise Exception('No port found.')
            if port:
                return 'http://localhost:%s' % port
            else:
                return self.cache_locator()
        else:
            return self.cache_locator()

    def cache_locator(self):
        '''Returns a formatted server address from the AssetCacheLocatorUtil
        binary output'''
        cmd = ['/usr/bin/AssetCacheLocatorUtil']
        try:
            result, error = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()  # NOQA
            if error:
                result = []
                host_addrs = ('localhost', '127.', '10.', '172.16', '192.168.')
                for item in error.split():
                    if item.startswith(host_addrs):
                        if item.replace(',', '') not in result:
                            result.append(item.replace(',', ''))
                if len(result) > 0:
                    self.log.debug('Success finding caching server: %s' % cmd)
                    return 'http://%s' % result[0]
                else:
                    # If all else fails, raise an exception
                    self.log.debug('No caching server found.')
                    raise Exception('No caching server found.')
        except:
            raise

    # Compare two digests
    def compare_digests(self, digest_a, digest_b):
        if digest_a == digest_b:
            return True
        else:
            return False

    def correct_package_filename(self, package_filename):
        '''Returns the correct package filename for display purposes only'''
        for source in self.apple_sources:
            if source in package_filename:
                return package_filename.replace('?source=%s' % source, '')

    def download(self, url):
        '''Downloads the specified file using the curl binary.'''
        # Change destination for package files to /tmp so we don't clutter
        # ipsw destination
        if '.pkg' in url:
            self.destination = '/tmp'

        # Basename the URL for curl file output
        output_file = os.path.join(self.destination, self.correct_package_filename(os.path.basename(url)))  # NOQA

        # curl called with minimal progress bar, and create directories if they
        # don't exist, as well as provide a user agent string.
        cmd = ['/usr/bin/curl', '--progress-bar', url, '-o', output_file, '--create-dirs', '--user-agent', self.user_agent]  # NOQA

        if self.dry_run:
            print cmd
        else:
            subprocess.check_call(cmd)

        # Because curl doesn't like /dev/null as a file path, delete items
        # downloaded if they're not IPSW files. Don't use shutil becase we only
        # want to remove the file, not the complete path!
        if not output_file.endswith('.ipsw'):  # NOQA
            try:
                os.remove(output_file)
                self.log.debug('Deleted: %s' % output_file)
            except Exception as e:
                self.log.debug('Unable to delete %s: %s' % (output_file, e))
                raise e

        sleep(uniform(1, 2))

    # Build digest for a specific file
    def file_digest(self, file_path, digest_type=None):
        '''Creates a digest based on the digest_type argument.
        digest_type defaults to SHA256.'''
        valid_digests = ['md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512']
        block_size = 65536

        if not digest_type:
            digest_type = 'sha256'

        if digest_type in valid_digests:
            h = hashlib.new(digest_type)
            with open(file_path, 'rb') as f:
                for block in iter(lambda: f.read(block_size), b''):
                    h.update(block)
                return h.hexdigest()
        else:
            raise Exception('%s not a valid digest - choose from %s' %
                            (digest_type, valid_digests))

    def hardware_model(self):
        '''Returns the hardware model of the Mac being used. This is used for
        the namedtuple in software updates for macOS, mostly for pretty
        output.'''
        cmd = ['/usr/sbin/sysctl', 'hw.model']
        result, error = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()  # NOQA
        if result:
            self.log.debug('Found Mac hardware model.')
            return result.strip('\n').split(' ')[1]
        else:
            self.log.debug('No Mac hardware model found.')
            return None

    def ios_updates(self, iOS=False, watchOS=False, tvOS=False, models=None, groups=None):  # NOQA
        '''Returns a generator object with all the iOS/watchOS/tvOS updates.
        Any additional manipulation should be done by another
        worker function.
        iOS=False, watchOS=False, tvOS=False: change these to True for each
        "asset" group you want to pull update info for.'''
        # This list gets extended by the ios, watch, and tv feeds below.
        updates = []

        if iOS:
            ios_feed = urljoin(self.configuration['iosBaseURL'], self.configuration['iosFeeds']['ios'])  # NOQA
            updates.extend(self.read_feed(ios_feed)['Assets'])
            self.log.debug('Extended udpates list with iOS feed')

        if watchOS:
            watch_feed = urljoin(self.configuration['iosBaseURL'], self.configuration['iosFeeds']['watch'])  # NOQA
            updates.extend(self.read_feed(watch_feed)['Assets'])
            self.log.debug('Extended udpates list with watchOS feed')

        if tvOS:
            tv_feed = urljoin(self.configuration['iosBaseURL'], self.configuration['iosFeeds']['tv'])  # NOQA
            updates.extend(self.read_feed(tv_feed)['Assets'])
            self.log.debug('Extended udpates list with tvOS feed')

        def cacheable(asset):
            try:
                if asset['__CanUseLocalCacheServer']:
                    return True
            except:
                return False

        def beta(asset):
            try:
                if asset['ReleaseType'] == 'Beta':
                    return True
            except:
                return False

        def device_model(asset):
            if asset['SupportedDevices']:
                return asset['SupportedDevices'][0]

        def device_group(asset):
            model = device_model(asset).replace(',', '')
            model = ''.join(map(lambda c: '' if c in '0123456789' else c, model))  # NOQA
            return model

        def update_version(asset):
            # Some updates are prefixed with '9.9.', not sure why, possible
            # beta release? This tidies that up.
            if asset.get('OSVersion') and asset['OSVersion'].startswith('9.9.'):  # NOQA
                return asset['OSVersion'].replace('9.9.', '')
            elif asset.get('OSVersion') and not asset['OSVersion'].startswith('9.9.'):  # NOQA
                return asset['OSVersion']

        def update_build(asset):
            try:
                return asset['Build']
            except:
                return 'No build found'

        def update_url(asset):
            try:
                return [self.reformat_url(asset['RealUpdateAttributes']['RealUpdateURL'])]  # NOQA
            except:
                return [self.reformat_url(urljoin(asset['__BaseURL'], asset['__RelativePath']))]  # NOQA

        def update_title(asset):
            try:
                if any(device in device_model(asset) for device in self.ios_devices):  # NOQA
                    prefix = 'iOS'
                elif 'Watch' in device_model(asset):
                    prefix = 'watchOS'
                elif 'TV' in device_model(asset):
                    prefix = 'tvOS'

                return '%s %s build %s' % (prefix, update_version(asset), update_build(asset))  # NOQA
            except:
                return '%s Update' % device_model(asset)

        for update in updates:
            asset = self.asset(
                model=device_model(update),
                version=update_version(update),
                urls=update_url(update),
                group=device_group(update),
                product_title=update_title(update)
            )
            yield asset

    def load_config(self, config_file):
        '''Loads configuration from the local configuration plist'''
        # Make sure configuration plist is in the same directory as script
        try:
            self.log.debug('load_config() success')
            return readPlist(config_file)
        except Exception as e:
            self.log.debug('load_config() failed: %s' % e)
            raise e

    def list_assets(self, verbose=False):
        '''A list of assets that can be cached.'''
        # Warn that this can take some time to generate due to the large
        # size of the sucatalog + getting all the product metadata.
        # If verbose is True, then the mobile devices will have include a
        # description of the device.
        print 'Building and processing this list output can take a few minutes. Please be patient.'  # NOQA

        # Lists, lists everywhere.
        ios_cacheable = []
        mac_os_cacheable = []
        apps_cacheable = []

        def device_description(asset):
            if 'Watch' not in asset:
                url = 'https://api.ipsw.me/v2.1/%s/latest/name' % asset
                self.log.debug('Getting device description: %s' % asset)
                return requests.get(url, headers={'user-agent': self.user_agent}, timeout=10).text  # NOQA
            else:
                return 'Apple Watch'

        # Get iOS assets we can cache
        ios_assets = self.ios_updates(iOS=True, watchOS=True, tvOS=True)

        # It can take a while to get the human readable model description, so
        # only get this if verbose is supplied as an argument.
        # Otherwise, just output model numbers
        if verbose:
            garbage_list = []
            for asset in ios_assets:
                asset_description = '%s' % asset.model
                if asset_description not in garbage_list:
                    garbage_list.append(asset_description)

            # List comprehension over the garbage_list builds ios_cacheable
            # list with the device model and human readable description.
            ios_cacheable = ['%s: %s' % (x, device_description(x)) for x in garbage_list]  # NOQA
        else:
            for asset in ios_assets:
                asset_description = '%s' % asset.model
                if asset_description not in ios_cacheable:
                    ios_cacheable.append(asset_description)
                    ios_cacheable.sort()

        ios_cacheable.sort()

        # Get macOS Apps we can cache
        app_assets = self.app_updates()
        for asset in app_assets:
            asset_description = '%s: %s' % (asset.product_title, asset.version)  # NOQA
            if asset_description not in apps_cacheable:
                apps_cacheable.append(asset_description)

        # Get macOS Updates we can cache
        mac_assets = self.software_updates()
        for asset in mac_assets:
            asset_description = '%s: %s' % (asset.product_id, asset.product_title)  # NOQA
            if asset.version:
                asset_description = '%s %s' % (asset_description, asset.version)  # NOQA
            if asset_description not in mac_os_cacheable:
                mac_os_cacheable.append(asset_description)

        if verbose:
            print '\niOS, watchOS, tvOS devices (model: description):'
        else:
            print '\niOS, watchOS, tvOS devices'
        for item in ios_cacheable:
            print item

        print '\nApps (app: version):'
        for item in apps_cacheable:
            print item

        print '\nmacOS Software Updates (product id: description):'
        for item in mac_os_cacheable:
            print item

        # Some usage instructions
        print '\nNote for iOS/watchOS/tvOS: Please use the model number (example: iPad6,7) when caching those items.'  # NOQA
        print 'Note for apps/macOS installers: Please use the app/installer name without the version when caching those items.'  # NOQA
        print 'Note for macOS Software updates: You can use the Product ID or part/all of the description to cache those items.'  # NOQA

    def main_processor(self, apps=None, groups=None, ipsw=None, mac_updates=None, models=None):  # NOQA
        '''Main processor that handles figuring out whether an item should be
        downloaded or not'''
        print 'Processing items to cache can take a few minutes. Please be patient.'  # NOQA
        # Creating an empty list for updates to exist in for processing
        updates = []

        # Always need these in the updates list, and these are very lightweight
        # to process compared to the sucatalog for macOS
        updates.extend(self.ios_updates(iOS=True, watchOS=True, tvOS=True))
        self.log.debug('updates list extended with all iOS update feeds.')

        # Test if IPSW's have numbers
        def has_digits(string):
            return any(char.isdigit() for char in string)

        # This is to handle instances where downloading a number of IPSW's
        # for a specific set of models might be required.
        ipsw_model_list = []
        for item in updates:
            if any(i in item.model for i in self.ipsw_capable) and item.model not in ipsw_model_list:  # NOQA
                ipsw_model_list.append(item.model)
                self.log.debug('Building IPSW model list %s' % item.model)
        ipsw_model_list.sort()

        # If no arguments are provided to main_processor() try and load from configuration  # NOQA
        if self.use_config:
            if not models:
                try:
                    if len(self.configuration['cacheModels']) >= 1:
                        models = self.configuration['cacheModels']
                        self.log.debug('No CLI arguments, loading models from configuration file.')  # NOQA
                except:
                    pass

            if not ipsw:
                try:
                    if len(self.configuration['cacheIPSW']) >= 1:
                        ipsw = self.configuration['cacheIPSW']
                        self.log.debug('No CLI arguments, loading IPSW from configuration file.')  # NOQA
                except:
                    pass

            if not groups:
                try:
                    if len(self.configuration['cacheGroups']) >= 1:
                        groups = self.configuration['cacheGroups']
                        self.log.debug('No CLI arguments, loading groups from configuration file.')  # NOQA
                except:
                    pass

            if not apps:
                try:
                    if len(self.configuration['cacheApps']) >= 1:
                        apps = self.configuration['cacheApps']
                        self.log.debug('No CLI arguments, loading apps from configuration file.')  # NOQA
                except:
                    pass

            if not mac_updates:
                try:
                    if len(self.configuration['cacheMacUpdates']) >= 1:
                        apps = self.configuration['cacheMacUpdates']
                        self.log.debug('No CLI arguments, loading Mac updates from configuration file.')  # NOQA
                except:
                    pass

        # Because processing software updates can take a while, only do this if
        # the sucatalog exists in groups or if software_updates exists
        if (groups and 'sucatalog' in groups) or mac_updates:  # NOQA
            updates.extend(self.software_updates())
            self.log.debug('Loaded: sucatalog')

        # Handle cacheable apps or macOS Installers
        if (groups and any(group in groups for group in self.asset_groups)) or apps:  # NOQA
            updates.extend(self.app_updates())
            self.log.debug('Loaded: app updates')

        # Sort by model
        updates = sorted(updates, key=attrgetter('model'))
        self.log.debug('Sorted updates list')

        def load_all_ipsw_files():
            self.log.debug('load_all_ipsw_files() called')
            for model in ipsw_model_list:
                if any(item in model for item in ipsw):
                    _ipsw = self.request_ipsw(model)
                    if _ipsw not in updates:
                        updates.extend(_ipsw)

        # Process IPSW's if requested
        if ipsw:
            if not any(has_digits(item) for item in ipsw):
                load_all_ipsw_files()
            else:
                for item in ipsw:
                    if item in ipsw_model_list:
                        _ipsw = self.request_ipsw(item)
                        if _ipsw not in updates:
                            updates.extend(_ipsw)
                    else:
                        print '%s is not a valid model. Pick from %s' % (item, ipsw_model_list)  # NOQA

        def cache(item):
            for url in item.urls:
                # Text that will be displayed in output
                if any(group in item.group for group in ['app', 'installer']):  # NOQA
                    caching_text = '%s %s (%s)' % (item.product_title, item.version, item.group)  # NOQA
                elif 'sucatalog' in item.group:
                    caching_text = '%s: %s - %s' % (item.product_id, item.product_title, self.correct_package_filename(os.path.basename(url)))  # NOQA
                else:
                    if item.model_description:
                        caching_text = '%s: %s - %s' % (item.model, item.model_description, item.product_title)  # NOQA
                    else:
                        caching_text = '%s: %s' % (item.model, item.product_title)  # NOQA

                # Output filename for IPSW's
                output_file = os.path.join(self.destination, self.correct_package_filename(os.path.basename(url)))  # NOQA

                # Normal 'pkg' files get processed by this bracket
                if not self.already_cached(url):  # NOQA
                    if self.dry_run:
                        print 'Cache: %s' % caching_text
                    else:
                        print 'Caching: %s' % caching_text
                        self.download(url)
                else:
                    print 'Already cached: %s' % caching_text

                # IPSW files are a little differnt. They may already be
                # cached, but may still need to be re-downloaded.
                if output_file.endswith('.ipsw'):
                    if not self.already_cached(url):
                        dry_download_text = 'Cache'
                        download_text = 'Caching'
                    else:
                        dry_download_text = 'Re-download'
                        download_text = 'Re-downloading'

                    if os.path.exists(output_file) and item.sha_digest:
                        print '  A file already exists, comparing digest for %s' % caching_text  # NOQA
                        # SHA1 or MD5 digest for ipsw files
                        if self.compare_digests(self.file_digest(output_file, digest_type='sha1'), item.sha_digest):  # NOQA
                            if self.dry_run:
                                print '  Skip: %s' % caching_text
                            else:
                                print '  Skipping: %s' % caching_text
                        else:
                            if self.dry_run:
                                print '%s: %s' % (dry_download_text, caching_text)  # NOQA
                            else:
                                print '%s: %s' % (download_text, caching_text)
                                self.download(url)
                    elif not os.path.exists(output_file):
                        if self.dry_run:
                            print '%s: %s' % (dry_download_text, caching_text)
                        else:
                            print '%s: %s' % (download_text, caching_text)
                            self.download(url)

        # Iterate the updates and do the thing!
        # This particular approach is used to avoid duplicating downloads where
        # possible.
        for update in updates:
            if models:
                if (any(item in update.model for item in models)) and ('ipsw' not in update.group):  # NOQA
                    self.log.debug('Model match, caching: %s' % update.model)
                    cache(update)

            if ipsw and update.group == 'ipsw':
                if any(item in update.model for item in ipsw):
                    self.log.debug('IPSW match, caching: %s' % update.model)
                    cache(update)

            if groups:
                if (any(item in update.group for item in groups)):  # NOQA
                    self.log.debug('Group match, caching: %s' % update.model)
                    cache(update)

            if mac_updates:  # or 'sucatalog' in update.group:
                # Compare against produdct id and product title
                if 'sucatalog' in update.group and ((any(item in update.product_id for item in mac_updates)) or any(item in update.product_title for item in mac_updates)):  # NOQA
                    self.log.debug('Mac update match, caching: %s' % update.model)  # NOQA
                    cache(update)

            if apps:
                if any(item in update.product_title for item in apps):
                    self.log.debug('App/installer match, caching: %s' % update.model)  # NOQA
                    cache(update)

    def mdm_models(self, mdm=None, mdm_url=None, mdm_user=None, mdm_pass=None, mdm_token=None):  # NOQA
        '''Returns a list of iOS devices from an MDM instance.'''

        # Default deaders for requests
        _headers = {
            'user-agent': '%s' % self.user_agent
        }

        # MDM methods as API calls differ
        def jamf(mdm_url=None, username=None, password=None):
            '''Returns models from Jamf based MDM.
            Hosted Jamf URL example:
                https://precache.jamfcloud.com
            Self hosted Jamf URL example (where specific port is required):
                https://example.org:8443
            '''
            # Default response is XML, change to JSON
            _headers['Accept'] = 'application/json'

            # Try and load from configuration file.
            if not mdm_url:
                try:
                    mdm_url = self.configuration['mdmServer']
                except:
                    self.log.info('Could not load MDM server from configuration file')  # NOQA
                    print 'Could not load MDM server from configuration file'  # NOQA
                    sys.exit(1)

            # Try and load from configuration file.
            if not username:
                try:
                    username = self.configuration['mdmUser']
                except:
                    self.log.info('Could not load MDM username from configuration file')  # NOQA
                    print 'Could not load MDM username from configuration file'  # NOQA
                    sys.exit(1)

            # Try and load from configuration file.
            if not password:
                try:
                    password = self.configuration['mdmPassword']
                except:
                    self.log.info('Could not load MDM password from configuration file')  # NOQA
                    print 'Could not load MDM password from configuration file'  # NOQA
                    sys.exit(1)

            if mdm_url.startswith('https://'):
                # Strips trailing slash and joins the JSSresources API path
                mdm_url = '%s/JSSResource/mobiledevices' % mdm_url.rstrip('/')
                try:
                    # The requests module automatically base64 encodes the
                    # supplied username & password)
                    self.log.info('Requesting models from: %s' % mdm_url)
                    req = requests.get(mdm_url, auth=HTTPBasicAuth(username, password), headers=_headers)  # NOQA
                    if req.status_code == 401:
                        self.log.info('401 error: Unauthorized request. Invalid username or password.')  # NOQA
                        print '401 error: Unauthorized request. Invalid username or password.'  # NOQA
                        sys.exit(1)
                    elif req.status_code == 200:
                        req = req.json()['mobile_devices']
                        # Make a unique list
                        models = list(set([x['model_identifier'] for x in req]))  # NOQA
                        if models:
                            return models
                        else:
                            self.log.info('No models found in MDM.')
                            return None
                except Exception as e:
                    self.log.debug('Jamf Exception: %s' % e)
                    pass

        def simplemdm(auth_token=None):
            # No URL required as an argument as SimpleMDM is cloud only
            mdm_url = 'https://a.simplemdm.com/api/v1/devices'

            # Try and load from configuration file.
            if not auth_token:
                try:
                    auth_token = self.configuration['mdmToken']
                except:
                    self.log.info('Could not load MDM token from configuration file.')  # NOQA
                    print 'Could not load MDM token from configuration file.'  # NOQA
                    sys.exit(1)

            try:
                req = requests.get(mdm_url, auth=(auth_token, ""), headers=_headers).json()  # NOQA
                if req['errors']:
                    print req['errors'][0]['title']
                    self.log.info(req['errors'][0]['title'])
                    sys.exit(1)
                else:
                    req = req['data']  # NOQA
                    self.log.info('Requesting models from: %s' % mdm_url)
                    # Make a unique list
                    models = list(set([x['attributes']['product_name'] for x in req]))  # NOQA
                    if models:
                        return models
                    else:
                        self.log.info('No models found in MDM.')
                        return None
            except Exception as e:
                self.log.debug('SimpleMDM Exception: %s' % e)
                pass

        if not mdm:
            try:
                mdm = self.configuration['mdm']
            except:
                self.log.info('MDM not found in configuration file. Please specify.')  # NOQA
                print 'MDM not found in configuration file. Please specify.'
                sys.exit(1)
        elif mdm:
            self.log.info('Specified MDM is: %s' % mdm)
            if 'simplemdm' in mdm:
                if mdm_token:
                    try:
                        return simplemdm(mdm_token)
                    except:
                        raise
                else:
                    print 'Must provide auth token for SimpleMDM.'
                    self.log.info('Must provide auth token for SimpleMDM.')
                    sys.exit(1)
            elif 'jss' in mdm or 'jamf' in mdm:
                if mdm_url and mdm_user and mdm_pass:  # NOQA
                    try:
                        return jamf(mdm_url, mdm_user, mdm_pass)
                    except:
                        raise
                else:
                    print 'Must provide Jamf MDM server URL, username, and password.'  # NOQA
                    self.log.info('Must provide Jamf MDM server URL, username, and password.')  # NOQA
                    sys.exit(1)
            else:
                print 'Must specify MDM. Choose either \'simplemdm\' or \'jamf\'.'  # NOQA
                self.log.info('Must specify MDM. Choose either \'simplemdm\' or \'jamf\'.')  # NOQA
                sys.exit(1)

    def read_feed(self, url):
        '''Reads any of the Apple XML/plist feeds required for software updates or
        iOS updates'''
        return readPlistFromString(requests.get(url, headers={'user-agent': self.user_agent}, timeout=10).text)  # NOQA

    def reformat_url(self, url):
        '''Formats the URL into the format required by the caching service:
           http://cacheserver:1234?source=source.apple.com'''
        cache_server = 'http://thor:49672'
        url = urlparse(url)
        return '%s%s?source=%s' % (cache_server, url.path, url.netloc)  # NOQA

    def request_ipsw(self, device_model):
        '''Returns the URL for the IPSW of the specified model, as well as the
        version of the IPSW.'''
        if 'Watch' not in device_model:
            url = 'https://api.ipsw.me/v2.1/%s/latest/info.json' % device_model
            try:
                ipsw_json = requests.get(url, headers={'user-agent': self.user_agent}, timeout=10).json()[0]  # NOQA

                try:
                    rel_date = ipsw_json['releasedate']
                except:
                    rel_date = ipsw_json['uploaddate']

                # Fix title prefix for the product_title attribute
                if any(device in device_model for device in self.ios_devices):  # NOQA
                    prefix = 'iOS'
                elif 'Watch' in device_model:
                    prefix = 'watchOS'
                elif 'TV' in device_model:
                    prefix = 'tvOS'

                asset = self.asset(
                    model=device_model,
                    model_description=ipsw_json['device'],
                    version=ipsw_json['version'],
                    urls=[self.reformat_url(ipsw_json['url'])],
                    group='ipsw',
                    product_title='%s %s build %s (ipsw)' % (prefix, ipsw_json['version'], ipsw_json['buildid']),  # NOQA
                    release_date=rel_date,
                    sha_digest=ipsw_json['sha1sum']
                )

                yield asset
            except:
                pass

    def software_updates(self):
        '''Returns a generator object with all the software updates
        (filtered). Any additional manipulation should be done by another
        worker function.'''
        # Empty list used so we can later sort all items by release date
        # (newest first)
        software_updates = []
        products = self.read_feed(self.sucatalog)['Products']
        # This is the release date for El Capitan, base all date comparisons
        # from this point in time. At least it's not datetime(1970, 1, 1, 0, 0)
        min_date = datetime(2015, 9, 30, 0, 0)

        # Get all the metadata for a product
        def metadata(product_id):
            return self.read_feed(metadata_url(product_id))  # NOQA

        # Get the product title from the software update
        def su_title(product_metadata):
            try:
                # product_metadata = metadata(product_id)  # NOQA
                if 'localization' in product_metadata.keys():
                    for key in product_metadata['localization'].keys():
                        # Looking for English titles, use
                        # .startswith() or other locales are returned
                        if key.startswith('English') or key.startswith('en'):
                            if 'title' in product_metadata['localization'][key].keys():  # NOQA
                                _title = product_metadata['localization'][key]['title']  # NOQA

                            return _title
            except:
                pass

        # Get product version
        def product_version(product_metadata):
            try:
                if 'CFBundleShortVersionString' in product_metadata.keys():
                    return product_metadata['CFBundleShortVersionString']
            except:
                pass

        # Get the metadata URL for the product
        def metadata_url(product_id):
            if 'ServerMetadataURL' in products[product_id].keys():
                return products[product_id]['ServerMetadataURL']
            else:
                return False

        def split_text(text):
            '''Split text into seperate words based on uppercase, i.e.
            transform ElCapitan to El Capitan'''
            # I really hate regex.
            chars = [x for x in text]
            for char in chars:
                if char != chars[0] and char.isupper():
                    chars[chars.index(char)] = ' ' + char
            return ''.join(chars)

        # Work through product updates and generate the namedtuple
        for product_id in products:
            try:
                _metadata = metadata(product_id)
            except:
                pass
            # List comprehension for all urls ending with '.pkg' as many updats
            # have more than one package file.
            urls = [self.reformat_url(pkg['URL']) for pkg in products[product_id]['Packages'] if pkg['URL'].endswith('.pkg')]  # NOQA
            try:
                title = su_title(_metadata)
            except:
                title = None
            try:
                _version = product_version(_metadata)
            except:
                _version = None

            # There are _so many updates_, so this is a filter to exclude.
            # Most of this is old cruft, some of it is stuff that really can be
            # managed by clients just requesting it as they update. We really
            # only care about the "big" stuff.
            # You can edit this if you want, but it reverts when you update via
            # `git pull`
            # If any products are missed as a result of the filter, it's not
            # _that_ big an issue as the product _should_ get cached on first
            # request anyway.
            exclude = self.configuration['sucatalogExcludes']
            if not any(item in title for item in exclude):
                # Clarify what release the Safari packge is for, pass if this
                # isn't possible.
                for url in urls:
                    if 'Safari' in title:
                        try:
                            url = os.path.basename(url.replace('?source=swcdn.apple.com', '')).replace('.pkg', '').replace('Safari', '').replace('.', '')  # NOQA
                            url = ''.join(map(lambda c: '' if c in '0123456789' else c, url))  # NOQA
                            title = '%s %s' % (title, split_text(url))
                        except:
                            pass

                # Don't care for updates before the El Capitan release date.
                if products[product_id]['PostDate'] >= min_date:
                    asset = self.asset(
                        model=self.mac_model,
                        version=_version,
                        urls=urls,
                        group='sucatalog',
                        product_id=product_id,
                        product_title=title,
                        release_date=products[product_id]['PostDate']
                    )
                    if asset not in software_updates:
                        software_updates.append(asset)

        # Sorting through the assets, newest first.
        software_updates = sorted(software_updates, key=attrgetter('release_date'), reverse=True)  # NOQA
        for update in software_updates:
            yield update

    def write_out(self, message):
        '''Dynamic output on screen that overwrites itself.'''
        sys.stdout.write("\r ")
        sys.stdout.flush()
        sys.stdout.write("\r%s\t" % message)
        sys.stdout.flush()

    # This isn't used yet, but may in the future
    def tetherator_status(self, plist):
        '''Gets the status of tethered cache server, returns True if running, False
        if not'''
        try:
            if readPlist(plist)['Activated']:
                return True
            else:
                return False
        except:
            return False

    def valid_server(self, cache_server):
        # If cache_server argument is supplied, check it is formatted
        # properly and return it, otherwise raise an error.
        # Note: tetherator/Caching Server runs as http only.
        if (urlparse(cache_server).scheme == 'http' and urlparse(cache_server).port):  # NOQA
            return cache_server
        else:
            raise Exception('Invalid Caching Server URL: %s' % cache_server)  # NOQA


# Main
def main():
    # Version info
    version = '%s (%s) version %s, updated on %s. %s' % (script_name, __status__,  __version__, __date__, __license__)  # NOQA

    # Class for tidier help output
    class SaneUsageFormat(argparse.HelpFormatter):
        '''
        Matt Wilkie on SO
        http://stackoverflow.com/questions/9642692/argparse-help-without-duplicate-allcaps/9643162#9643162
        '''
        def _format_action_invocation(self, action):
            if not action.option_strings:
                default = self._get_default_metavar_for_positional(action)
                metavar, = self._metavar_formatter(action, default)(1)
                return metavar

            else:
                parts = []

                # if the Optional doesn't take a value, format is:
                #    -s, --long
                if action.nargs == 0:
                    parts.extend(action.option_strings)

                # if the Optional takes a value, format is:
                #    -s ARGS, --long ARGS
                else:
                    default = self._get_default_metavar_for_optional(action)
                    args_string = self._format_args(action, default)
                    for option_string in action.option_strings:
                        parts.append(option_string)

                    return '%s %s' % (', '.join(parts), args_string)

                return ', '.join(parts)

        def _get_default_metavar_for_optional(self, action):
            return action.dest.upper()

    parser = argparse.ArgumentParser(formatter_class=SaneUsageFormat)

    # Used in the choices options for groups to cache
    asset_groups = ['AppleTV', 'iPad', 'iPhone', 'iPod', 'Watch', 'app', 'installer', 'sucatalog']  # NOQA
    apps = ['Keynote', 'Xcode', 'iMovie', 'MainStage', 'Server', 'Sierra', 'Numbers', 'ElCapitan', 'GarageBand', 'FinalCutPro', 'LogicProX', 'Pages']  # NOQA
    supported_mdm = ['jamf', 'simplemdm']

    # All the args!
    parser.add_argument('--apps',
                        type=str,
                        nargs='+',
                        dest='apps',
                        choices=(apps),
                        metavar='<product name>',
                        help='Cache specific apps',
                        required=False)

    parser.add_argument('--cache-group',
                        type=str,
                        nargs='+',
                        dest='cache_group',
                        choices=(asset_groups),
                        metavar='<product name>',
                        help='Cache assets based on group',
                        required=False)

    parser.add_argument('-cs', '--cache-server',
                        type=str,
                        nargs=1,
                        dest='cache_server',
                        metavar='http://cacheserver:port',
                        help='Specify the cache server to use.',
                        required=False)

    parser.add_argument('-d', '--destination',
                        type=str,
                        nargs=1,
                        dest='destination_dir',
                        metavar='file path',
                        help='Path to save IPSW files to.',
                        required=False)

    parser.add_argument('-i', '--ipsw',
                        type=str,
                        nargs='+',
                        dest='ipsw_model',
                        metavar='model',
                        help='Cache IPSW for provided model/s.',
                        required=False)

    parser.add_argument('--mdm',
                        type=str,
                        nargs=1,
                        dest='mdm',
                        choices=(supported_mdm),
                        metavar='mdm',
                        help='Specify which MDM to use.',  # NOQA
                        required=False)

    parser.add_argument('--mdm-server',
                        type=str,
                        nargs=1,
                        dest='mdm_server',
                        metavar='server',
                        help='MDM server address.',  # NOQA
                        required=False)

    parser.add_argument('--mdm-user',
                        type=str,
                        nargs=1,
                        dest='mdm_user',
                        metavar='username',
                        help='MDM username',
                        required=False)

    parser.add_argument('--mdm-password',
                        type=str,
                        nargs=1,
                        dest='mdm_password',
                        metavar='password',
                        help='MDM password',
                        required=False)

    parser.add_argument('--mdm-token',
                        type=str,
                        nargs=1,
                        dest='mdm_token',
                        metavar='token',
                        help='MDM token',
                        required=False)

    parser.add_argument('-l', '--list',
                        action='store_true',
                        dest='list',
                        help='Lists all assets available for caching.',
                        required=False)

    parser.add_argument('-m', '--model',
                        type=str,
                        nargs='+',
                        dest='models',
                        metavar='model',
                        help='Provide model(s). For example: iPad6,8',
                        required=False)

    parser.add_argument('-u', '--updates',
                        type=str,
                        nargs='+',
                        dest='mac_updates',
                        metavar='product id/keyword',
                        help='Provide a product id or keyword from an update. Use the -l,--list command to get a list of updates.',  # NOQA
                        required=False)

    parser.add_argument('-n', '--dry-run',
                        action='store_true',
                        dest='dry_run',
                        help='Shows what would be cached.',
                        required=False)

    parser.add_argument('--version',
                        action='store_true',
                        dest='ver',
                        help='Version info.',
                        required=False)

    # Process arguments
    args = parser.parse_args()

    # If no arguments are supplied, initialise and run with best effort to detect configuration and caching server  # NOQA
    if len(sys.argv) == 1:
        p = PreCache(use_config=True)
        p.main_processor()
    # If arguments are supplied, process them.
    elif len(sys.argv) > 1:
        if args.ver:
            print '%s' % version
            sys.exit(0)

        if args.destination_dir:
            _destination = args.destination_dir[0]
        else:
            _destination = None

        if args.cache_server:
            _cache_server = args.cache_server[0]
        else:
            _cache_server = None

        # This deals with "mutually exclusive" arguments better than argparse
        if args.list and (args.models or args.ipsw_model or args.ver or args.cache_group or args.mdm_server or args.mdm_user or args.mdm_password):  # NOQA
            print 'Cannot combine these arguments with -l,--list'
            sys.exit(1)
        else:
            if args.list:
                p = PreCache(server=_cache_server, destination=_destination, dry_run=True)  # NOQA
                p.list_assets(verbose=True)
            else:
                if args.apps:
                    _apps = args.apps
                else:
                    _apps = None

                if args.cache_group:
                    _groups = args.cache_group
                else:
                    _groups = None

                if args.dry_run:
                    _dry_run = True
                else:
                    _dry_run = False

                if args.ipsw_model:
                    _ipsw_models = args.ipsw_model
                else:
                    _ipsw_models = None

                if args.mac_updates:
                    _mac_updates = args.mac_updates
                else:
                    _mac_updates = None

                # Init class here so we can use p.mdm_models later.
                p = PreCache(server=_cache_server, destination=_destination, dry_run=_dry_run)  # NOQA

                # Continue processing args.
                if args.models:
                    if args.mdm:
                        print 'MDM argument not supported with models argument.'  # NOQA
                        sys.exit(1)
                    else:
                        _models = args.models
                else:
                    _models = None

                # If any details have been provided
                if args.mdm:
                    if args.models:
                        print 'Models argument not supported with MDM argument.'  # NOQA
                        sys.exit(1)
                    else:
                        if args.mdm:
                            _mdm = args.mdm[0]
                        else:
                            _mdm = None

                    if args.mdm_server:
                        if 'jamf' in args.mdm:
                            _mdm_server = args.mdm_server[0]
                        else:
                            print 'MDM server URL not required.'
                            sys.exit(1)
                    else:
                        _mdm_server = None

                    if args.mdm_user:
                        if 'jamf' in args.mdm:
                            _mdm_user = args.mdm_user[0]
                        else:
                            print 'MDM username not required.'
                            sys.exit(1)
                    else:
                        _mdm_user = None

                    if args.mdm_password:
                        if 'jamf' in args.mdm:
                            _mdm_pass = args.mdm_password[0]
                        else:
                            print 'MDM password not required.'
                            sys.exit(1)
                    else:
                        _mdm_pass = None

                    if args.mdm_token:
                        if 'jamf' in args.mdm:
                            print 'Jamf requires username and password authentication.'  # NOQA
                            sys.exit(1)
                        else:
                            _mdm_token = args.mdm_token[0]
                    else:
                        _mdm_token = None

                    # Avengers assemble! Well, just models anyways.
                    _models = p.mdm_models(mdm=_mdm, mdm_url=_mdm_server, mdm_user=_mdm_user, mdm_pass=_mdm_pass, mdm_token=_mdm_token)  # NOQA
                else:
                    _models = None

                # Call the main processor method to actually do the caching
                p.main_processor(apps=_apps, groups=_groups, ipsw=_ipsw_models, mac_updates=_mac_updates, models=_models)  # NOQA


# Run main()
if __name__ == '__main__':
    main()
