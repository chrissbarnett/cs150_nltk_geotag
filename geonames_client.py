import requests
import time


class GeoNamesClient:
    search_url = 'http://api.geonames.org/search'
    details_url = 'http://api.geonames.org/get'

    """
    client to retrieve GeoNames info given an id.
    """
    def __init__(self, token=None, pause=0.3):
        """
        :param token: Geonames access token
        :param pause: pause between requests to the API (throttle)
        """
        self.access_token = token
        self.pause = pause

    def get_entry(self, geoname_id, style="full", retry_attempts=0):
        """
        get the raw response back from GeoNames as a dictionary

        :param geoname_id:
        :param style: API parameter that determines fields returned
        :param retry_attempts: how many times to retry the request if it fails
        :return:
        """
        # pause execution to prevent dos'ing the GeoNames server
        time.sleep(self.pause)

        params = {
            'username': self.access_token,
            'style': style,
            'geonameId': str(geoname_id)
        }
        gn_url = self.details_url  # baseurl for geonames

        try:
            response = requests.get(gn_url, params=params, timeout=5)
        except requests.exceptions.Timeout as e:
            print(e)
            if retry_attempts > 0:
                retry_attempts -= 1
                return self.get_entry(geoname_id, retry_attempts=retry_attempts)
            else:
                raise Exception('Timeout after specified retries.')

        if response.status_code == 200:
            return response.json()
        elif retry_attempts > 0:
            retry_attempts -= 1
            return self.get_entry(geoname_id, retry_attempts=retry_attempts)
        else:
            raise Exception('Status code: ' + str(response.status_code))

    def search_locale_in_state(self, locale, state, max_rows=5, country='US'):
        response = self.search_name(locale, style='FULL', max_rows=max_rows, countries=country, state_code=state)
        if 'geonames' in response:
            for r in response['geonames']:
                if r['name'].lower() == locale.lower():
                    print(r)
                    return response['geonames'], r
                # check alternate names
                if 'alternateNames' in r:
                    for a in r['alternateNames']:
                        if a['name'].lower() == locale.lower():
                            print(a)
                            return response['geonames'], a
            return response['geonames'], {}
        print('no locale found: ', locale)

    def search_state(self, name, style='medium', max_rows=5, feature_codes='ADM1', country='US'):
        response = self.search_name(name, style, max_rows=max_rows, feature_codes=feature_codes, countries=country)
        if 'geonames' in response:
            for r in response['geonames']:
                if r['name'].lower() == name.lower():
                    print(r)
                    return r
        print('no state found: ' + name)

    def search_name(self, name, style="medium", exact=False, max_rows=10, fuzz=1, feature_classes=None,
                    feature_codes=None, countries=None, state_code=None, retry_attempts=0):
        """
        get the raw response back from GeoNames as a dictionary

        :param fuzz:
        :param state_code:
        :param countries:
        :param feature_codes:
        :param exact:
        :param name:
        :param feature_classes:
        :param max_rows:
        :param style: API parameter that determines fields returned
        :param retry_attempts: how many times to retry the request if it fails
        :return:
        """
        # pause execution to prevent dos'ing the GeoNames server
        time.sleep(self.pause)

        params = {
            'username': self.access_token,
            'style': style,
            'name': name,
            'isNameRequired': True,
            'inclBbox': True,
            'type': 'json',
            'fuzzy': fuzz,
            'maxRows': max_rows
        }

        if fuzz < 1:
            params['isNameRequired'] = False

        if not exact:
            params['name'] = name
        else:
            params['name_equals'] = name

        if feature_codes is not None:
            params['featureCode'] = feature_codes

        if feature_classes is not None:
            params['featureClass'] = feature_classes

        if countries is not None:
            params['country'] = countries

        if state_code is not None:
            params['adminCode1'] = state_code

        gn_url = self.search_url  # baseurl for geonames search

        try:
            response = requests.get(gn_url, params=params, timeout=None)
        except requests.exceptions.Timeout as e:
            print(e)
            if retry_attempts > 0:
                retry_attempts -= 1
                return self.search_name(name, retry_attempts=retry_attempts)
            else:
                raise Exception('Timeout after specified retries.')

        if response.status_code == 200:
            return response.json()

        if retry_attempts > 0:
            retry_attempts -= 1
            return self.search_name(name, retry_attempts=retry_attempts)
        else:
            raise Exception('Status code: ' + str(response.status_code))

    @staticmethod
    def get_display(place):
        """
        parse json response from geonames API (medium response for each place)
        :param place:
        :return:
        """

        fcl = place['fcl']

        if fcl == 'P':
            if 'countryCode' in place:
                # populated place
                if place['countryCode'] == 'US':
                    return place['name'] + ', ' + place['adminCode1'] + ' (US city)'

                else:
                    return place['name'] + ' (city, country: ' + place['countryCode'] + ')'
            else:
                print('Populated place with no country code')
                print(place)

        elif fcl == 'A':
            # admin
            fcode = place['fcode']
            if fcode == 'PCLI':
                return place['name'] + ' (country)'

            if 'countryCode' in place:
                if place['countryCode'] == 'US':
                    if fcode == 'ADM1':
                        return place['name'] + ' (US state)'
                    elif fcode == 'ADM2':
                        return place['name'] + ', ' + place['adminCode1'] + ' (US county)'
                    elif fcode == 'ZN':
                        return place['name'] + ' (US Zone)'
                    else:
                        if 'adminCode1' not in place:
                            print(place)
                            return 'unrecognized feature type'

                        return place['name'] + ', ' + place['adminCode1'] + ' (US admin level: ' + fcode + ')'
                else:
                    adminlevel = place['fcodeName']
                    if fcode == 'ADM1':
                        adminlevel = 'admin 1'
                    elif fcode == 'ADM2':
                        adminlevel = 'admin 2'
                    elif fcode == 'ADM3':
                        adminlevel = 'admin 3'
                    elif fcode == 'ADM4':
                        adminlevel = 'admin 4'
                    elif fcode == 'ADM5':
                        adminlevel = 'admin 5'
                    return place['name'] + ' (' + adminlevel + ', country: ' + place['countryCode'] + ')'
        elif fcl == 'L' and place['toponymName'] == 'Earth':
            # special value for Earth
            return place['toponymName'] + ' (world wide)'

        else:
            # H: water bodies, L: parks, area..., T: mountain, hill..., S: spot, building
            if 'countryCode' in place:
                descriptor = place['fcodeName'] + ', country: ' + place['countryCode']
            else:
                descriptor = place['fcodeName']
            return place['toponymName'] + ' (' + descriptor + ')'

    @staticmethod
    def is_region(r):
        return r['featureCode'] in ['RGN', 'RGNH', 'OCN', 'TERR']

    @staticmethod
    def is_continent(r):
        fc = r['featureCode'] == 'CONT'
        return fc or r['preferredName'] in ['Europe', 'Africa', 'Asia', 'North America', 'South America', 'Oceania',
                                            'Antarctica']

    @staticmethod
    def is_country(r):
        m = r['preferredName'] in ['Korea']
        return m or r['featureCode'] in ['PCLI', 'PCLH', 'PCLF', 'PCLD', 'PCL', 'PCLS', 'PCLIX']

    @staticmethod
    def is_city(r):
        return r['featureClass'] == 'P'

    @staticmethod
    def is_state(r):
        return r['featureCode'] in ['ADM1']

    @staticmethod
    def get_placetype(r):
        placetype = None
        if GeoNamesClient.is_continent(r):
            placetype = 'continent'
        elif GeoNamesClient.is_region(r):
            placetype = 'region'
        elif GeoNamesClient.is_country(r):
            placetype = 'country'
        elif GeoNamesClient.is_city(r):
            placetype = 'city'
        elif GeoNamesClient.is_state(r):
            placetype = 'state'
        else:
            placetype = 'unknown'

        return placetype

