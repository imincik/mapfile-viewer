#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Create HTML mapfile viewer.

Usage:  viewer.py <http://mapserver_url> <mapfile.map> <scale,scale,scale> > file.html
        viewer.py "http://localhost/cgi-bin/mapserv" "map/example.map" "1000,500" > viewer.html
"""

import sys, os
import mapscript

MS_UNITS = {
	3: 'm',
	4: 'mi',
	6: 'px'
}

def get_resolutions(scales, units, resolution=96.0):
	factor = {'inches': 1.0, 'ft': 12.0, 'mi': 63360.0,
			'm': 39.3701, 'km': 39370.1, 'dd': 4374754.0}
	
	inches = 1.0 / resolution
	monitor_l = inches / factor[units]
	
	resolutions = []
	for m in scales:
		resolutions.append(monitor_l * int(m))
	return resolutions

def get_html(c):
	html = ''

	# head and javascript start
	html = html + """
		<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
		<html xmlns="http://www.w3.org/1999/xhtml">
		<head>
			<meta http-equiv="content-type" content="text/html; charset=utf-8" />
			<title>Mapfile viewer - %(mapfile)s</title>
			<link rel="stylesheet" type="text/css" href="static/theme/default/style.css" />
			<link rel="stylesheet" type="text/css" href="static/theme/dark/style.css" />
			<script type="text/javascript" src="static/OpenLayers.js"></script>
			<script type="text/javascript">
	""" % c

	# config object
	html = html + """
		var config = {
			projection: "%(projection)s",
			units: "%(units)s",
			resolutions: [%(resolutions)s],
			maxExtent: [%(extent)s],
		};

		var x = %(center_coord1)s;
		var y = %(center_coord2)s;
		var zoom = 0;
		var layer = null;

	""" % c

	# init function
	html = html + """
		function init(){
	"""

	# create layer objects
	for lay in c['layers']:
		html = html + """
		var %s = new OpenLayers.Layer.WMS(
		"%s",
		["%s"],
		{
			layers: "%s",
			format: "%s",
		},
		{
			isBaseLayer: true,
			visibility: true,
			singleTile: true,
			// attribution: "",
		}
	);

	""" % (lay.replace('-', '_'), lay, c['wms_url'], lay, 'image/png')

	# add controls
	html = html + """
		OpenLayers.DOTS_PER_INCH=96;
		var map = new OpenLayers.Map("map", {
			controls:[
				new OpenLayers.Control.Navigation(),
				new OpenLayers.Control.PanZoomBar({slideFactor: 250}),
				new OpenLayers.Control.ScaleLine(),
				new OpenLayers.Control.MousePosition(),
				new OpenLayers.Control.LayerSwitcher(),
				new OpenLayers.Control.Attribution(),
				new OpenLayers.Control.Scale()
			],
			theme: null,
			units: config.units,
			projection: new OpenLayers.Projection(config.projection),
			resolutions: config.resolutions,
			maxExtent: new OpenLayers.Bounds(config.maxExtent[0], config.maxExtent[1], config.maxExtent[2], config.maxExtent[3]),
		});
	"""

	# add layers
	for lay in c['layers']:
		html = html + """
		map.addLayer(%s);
	""" % lay.replace('-', '_')

	# center
	html = html + """
		map.setCenter(new OpenLayers.LonLat(x, y), zoom);
	"""

	# head and javascript end
	html = html + """
		}
	</script>
	</head>
	"""

	# body
	html = html + """
	<body onload="init()">
	<h2>Mapfile viewer</h2>
		<div id="map" style="width: 100%%; height: 700px; border: 2px solid #222;"></div>
		<p>
		File: %(mapfile)s <br />
		Scales: %(scales)s <br />
		Units: %(units)s <br />
		Center: %(center_coord1)s, %(center_coord2)s
		</p>
	</body>
	</html>
	""" % c

	return html



if __name__ == "__main__":

	try:
		mapserver = sys.argv[1]
		mapfile = sys.argv[2]
		scales = sys.argv[3]
	except IndexError:
		print __doc__
		sys.exit(1)

	# collect configuration values from mapfile
	mf = mapscript.mapObj(mapfile)

	c = {}
	c['mapfile'] = os.path.abspath(mapfile)
	c['mapserver'] = mapserver
	
	c['units'] = MS_UNITS[mf.units]
	c['projection'] = mf.web.metadata.get('wms_srs').split(' ')[0]
	c['extent'] = '%s, %s, %s, %s' % (mf.extent.minx, mf.extent.miny,
		mf.extent.maxx, mf.extent.maxy)
	c['center_coord1'] = mf.extent.getCenter().x
	c['center_coord2'] = mf.extent.getCenter().y

	c['scales'] = scales
	c['resolutions'] = ', '.join(str(r) for r in get_resolutions(c['scales'].split(','), c['units']))

	c['layers'] = []
	numlays = mf.numlayers
	for i in range(0, numlays):
		c['layers'].append(mf.getLayer(i).name)

	c['wms_url'] = '%s?map=%s' % (c['mapserver'], c['mapfile'])

	# html
	print get_html(c)



# vim: set ts=4 sts=4 sw=4 noet:
