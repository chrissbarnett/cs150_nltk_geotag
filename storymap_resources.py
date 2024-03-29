import json
import dominate
from dominate.tags import *
from dominate.util import raw


class StoryMapCreator:
    def __init__(self):
        self.places = {}
        self.pages = {}

    def load_places(self):
        with open('./data/texts/civil_war_photos/places.json', 'rb') as f:
            self.places = json.loads(f.read())

    def load_pages(self):
        with open('./data/texts/civil_war_photos/pages.json', 'rb') as f:
            self.pages = json.loads(f.read())

    def write_geojson_places(self, geojson_places):
        with open('./data/texts/civil_war_photos/places_geojson.json', 'w') as f:
            f.write(json.dumps(geojson_places, ensure_ascii=False))

    def create_geojson_places(self, places):
        """
        creates a json object that maps page indices to associated geojson feature collections
        :param places:
        :return:
        """
        wrapper = {}
        for k, v in places.items():
            if 'places' in v and v['places'] is not None:
                filtered_places = self.filter_places(v['places'])
                wrapper['page-' + str(k)] = self.create_feature_collection(filtered_places)

        self.write_geojson_places(wrapper)
        return wrapper

    def filter_places(self, places):
        filtered = []
        for p in places:
            if 'countryCode' in p and p['countryCode'] == 'US':
                if 'fcode' in p and p['fcode'] == 'PCLI':
                    continue
                filtered.append(p)
        return filtered

    def create_feature_collection(self, geonames):
        """
        create the geojson feature collection structure
        :param geonames:
        :return:
        """
        geojson = {'type': 'FeatureCollection',
                   'features': []}

        for g in geonames:
            geojson['features'].append(self.create_feature(g))
        return geojson

    def create_feature(self, geoname):
        feature = {'type': 'Feature', 'coordinates': [], 'properties': {}}
        '''
        if 'bbox' in geoname:
            feature['type'] = 'Polygon'
            feature['coordinates'] = self.geom_from_bbox(geoname['bbox'])
            feature['properties'] = self.properties_from_geoname(geoname)
        '''
        if 'lat' in geoname:
            feature['type'] = 'Point'
            feature['coordinates'] = self.geom_from_lat_lng(geoname['lat'], geoname['lng'])
            feature['properties'] = self.properties_from_geoname(geoname)
        else:
            print('no bbox or lat/lng')
            print(g)

        return feature

    def geom_from_bbox(self, bbox):
        e = bbox['east']
        w = bbox['west']
        s = bbox['south']
        n = bbox['north']
        # todo: if west is greater than east, this should wind the opposite direction
        return [[[w, s], [w, n], [e, n], [e, s], [w, s]]]

    def geom_from_lat_lng(self, lat, lng):
        return [lng, lat]

    def properties_from_geoname(self, geoname):
        props = {
            'name': geoname['name'],
            'countryCode': geoname.get('countryCode', ''),
            'featureCode': geoname.get('fcode', '')
        }
        if props['featureCode'] != 'ADM1':
            props['adm1'] = geoname.get('adminCode1')
        return props

    def create_book_html(self):
        self.load_pages()
        wrapper = div(id='pages')
        for k, v in self.pages.items():
            pageid = 'page-{}'.format(str(k))
            pagehtml = v['html']
            # fix some bad references to non-existent thumbnails:
            pagehtml = pagehtml.replace('t.jpg', '.jpg')
            place_section = section(a('', id=pageid), data_place=pageid)
            place_section.add(raw(pagehtml))
            wrapper.add(place_section)
        with open('./data/texts/civil_war_photos/pages.html', 'w') as f:
            f.write(wrapper.render())
