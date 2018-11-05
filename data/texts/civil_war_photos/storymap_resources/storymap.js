    (function ($) {
    'use strict';


    $.fn.storymap = function(options) {

        var defaults = {
            selector: '[data-place]',
            breakpointPos: '33.333%',
            maxZoom: 5,
            features: {},
            feature_options: {}
        };

        var settings = $.extend(defaults, options);

        if (typeof(L) === 'undefined') {
            throw new Error('Storymap requires Leaflet');
        }
        if (typeof(_) === 'undefined') {
            throw new Error('Storymap requires underscore.js');
        }

        function createMap(){
            // create a map in the "map" div, set the view to a given place and zoom
            var map = L.map('map').setView([0,0], settings.maxZoom);

            // add CartoDB basemap
            L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
	            attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
	            subdomains: 'abcd',
	            maxZoom: 19
            }).addTo(map);

            return map;
        }

        function getDistanceToTop(elem, top) {
            var docViewTop = $(window).scrollTop();

            var elemTop = $(elem).offset().top;

            var dist = elemTop - docViewTop;

            var d1 = top - dist;

            if (d1 < 0) {
                return $(document).height();
            }
            return d1;

        }

        function highlightTopPara(paragraphs, top) {

            var distances = _.map(paragraphs, function (element) {
                var dist = getDistanceToTop(element, top);
                return {el: $(element), distance: dist};
            });

            var closest = _.min(distances, function (dist) {
                return dist.distance;
            });

            _.each(paragraphs, function (element) {
                var paragraph = $(element);
                if (paragraph[0] !== closest.el[0]) {
                    paragraph.trigger('notviewing');
                }
            });

            if (!closest.el.hasClass('viewing')) {
                closest.el.trigger('viewing');
            }
        }

        function watchHighlight(element, searchfor, top) {
            var paragraphs = element.find(searchfor);
            highlightTopPara(paragraphs, top);
            $(window).scroll(function () {
                highlightTopPara(paragraphs, top);
            });
        }

        var makeStoryMap = function (element, markers) {

            var topElem = $('<div class="breakpoint-current"></div>')
                .css('top', settings.breakpointPos);
            $('body').append(topElem);

            var top = topElem.offset().top - $(window).scrollTop();

            var searchfor = settings.selector;

            var paragraphs = element.find(searchfor);

            paragraphs.on('viewing', function () {
                $(this).addClass('viewing');
            });

            paragraphs.on('notviewing', function () {
                $(this).removeClass('viewing');
            });


            var map = createMap();

            var initPoint = map.getCenter();
            var initZoom = map.getZoom();

            var fg = L.featureGroup().addTo(map);

            function showMapView(key) {

                var feature = settings.features[key];

                fg.clearLayers();
                if (key === 'overview') {
                    map.setView(initPoint, initZoom, true);
                } else if (feature) {

                    var zoom = settings.maxZoom;

                    if (_.has(settings.feature_options, key)){

                        if (_.has(settings.feature_options[key], 'layer')){
                            var layer = settings.feature_options[key].layer;

                            if(typeof layer !== 'undefined'){
                                fg.addLayer(layer);
                            }
                        }

                        if (_.has(settings.feature_options[key], 'maxZoom')) {

                            zoom = settings.feature_options[key].maxZoom;
                        }

                    }

                    var onEachFeature = function(feature, layer) {
                        // does this feature have a property named popupContent?
                        if (feature.properties && feature.properties.name) {
                            var popup = '<div class="popup">';
                            if (feature.properties.adm1) {
                                popup += '<div>' + feature.properties.name + ', ' + feature.properties.adm1 + '</div>';
                            } else {
                                popup += '<div>' + feature.properties.name + '</div>';
                            }
                            popup += '<div>' + feature.properties.countryCode + '</div>';
                            popup += '<div>Feature Code: ' + feature.properties.featureCode + '</div>';
                            popup += '</div>';

                            layer.bindPopup(popup);
                        }
                    };

                    fg.addLayer(L.geoJSON(feature, {'onEachFeature': onEachFeature}));

                    var bounds = fg.getBounds();
                    map.fitBounds(bounds, { maxZoom: zoom });

                }

            }

            paragraphs.on('viewing', function () {
                showMapView($(this).data('place'));
            });

            watchHighlight(element, searchfor, top);

        };

        makeStoryMap(this, settings.markers);

        return this;
    }

}(jQuery));
