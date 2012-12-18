#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MAPFILE DEVELOPER SCRIPT.
Minimalistic HTML viewer for UMN MapServer mapfiles in simple
standalone WSGI server.

Example:
	run $ ./viewer.py -m map/viewer.map
	and point your browser to 'http://localhost:9991'

Author: Ivan Mincik, ivan.mincik@gmail.com
"""

import sys, os
from optparse import OptionParser
from cgi import parse_qsl
import mapscript

MS_UNITS = {
	0: 'in',
	1: 'ft',
	2: 'mi',
	3: 'm',
	4: 'km',
	5: 'dd',
	6: 'px'
}


def _get_resolutions(scales, units, resolution=96):
	"""Helper function to compute OpenLayers resolutions."""

	resolution = float(resolution)
	factor = {'in': 1.0, 'ft': 12.0, 'mi': 63360.0,
			'm': 39.3701, 'km': 39370.1, 'dd': 4374754.0}
	
	inches = 1.0 / resolution
	monitor_l = inches / factor[units]
	
	resolutions = []
	for m in scales:
		resolutions.append(monitor_l * int(m))
	return resolutions


def _concatenate_mapfiles(mapfiles):
	"""Concatenate mapfiles and return resulting file path."""

	outfiledir = os.path.abspath(os.path.dirname(mapfiles[0]))
	outfilename = ''

	outdata = 'MAP\n'

	for f in mapfiles:
		outdata += open(f).read()
		outfilename += '_' + os.path.splitext(os.path.basename(f))[0]

	outdata += '\nEND'

	outfilepath = os.path.join(outfiledir, outfilename + '.map')

	outfile = open(outfilepath, 'w')
	outfile.write(outdata)
	outfile.close()

	return outfilepath


def test_mapfile(mapfile):
	"""Test mapfile syntax, print result and exit script."""

	try:
		print 'Checking mapfile.'
		m = mapscript.mapObj(mapfile)
		print 'OK, %s layers found.' % m.numlayers
	except Exception, err:
		print 'ERROR: %s' % err

	if options.concatenate:
		os.remove(mapfile)

	sys.exit(0)


def application(c):
	"""Return OpenLayers viewer application HTML code."""

	html = ''

	# head and javascript start
	html += """
		<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
		<html xmlns="http://www.w3.org/1999/xhtml">
		<head>
			<meta http-equiv="content-type" content="text/html; charset=utf-8" />
			<title>Mapfile: %(mapfile)s</title>
			<link rel="stylesheet" type="text/css" href="static/theme/default/style.css" />
			<link rel="stylesheet" type="text/css" href="static/theme/dark/style.css" />
			<link rel="stylesheet" type="text/css" href="static/viewer.css" />

			<script type="text/javascript" src="https://ajax.googleapis.com/ajax/libs/jquery/1.8.3/jquery.min.js"></script>
			<script type="text/javascript" src="https://raw.github.com/imincik/mapfile-viewer/master/static/OpenLayers-2.12.js"></script>
			<script type="text/javascript">
	""" % c

	# config object
	html += """
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
	html += """
		$(document).ready(function(){
	"""

	# automatic map window height setting
	html += """
		$("#map").height($(window).height() - 150);
		$("#legend").height($(window).height() - 150);
	"""

	# create layer objects
	for lay in c['layers']:
		html += """
		var %s = new OpenLayers.Layer.WMS(
		"%s",
		["%s"],
		{
			layers: "%s",
			format: "%s",
		},
		{
			isBaseLayer: false,
			visibility: true,
			singleTile: true,
			// attribution: "",
		}
	);

	""" % (lay.replace('-', '_'), lay, c['ows_url'], lay, 'image/png')

	# add controls
	html += """
		OpenLayers.DOTS_PER_INCH=%(resolution)s;
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
	""" % c

	html += """
		var baseLayerWhite = new OpenLayers.Layer.Image("White Background",
			'static/white.png',
			map.maxExtent,
			new OpenLayers.Size(1, 1)
		);

		map.addLayer(baseLayerWhite);
	"""

	# add layers
	for lay in c['layers']:
		html += """
		map.addLayer(%s);
	""" % lay.replace('-', '_')

	# center
	html += """
		map.setCenter(new OpenLayers.LonLat(x, y), zoom);
	"""

	# legend loading
	html += """
		function loadLegend(){

			var layers = map.getLayersBy("visibility", true);
			var overlayLayers = [];

			for (var i=0, len=layers.length; i<len;i++) {
				if (layers[i].isBaseLayer === false) {
					overlayLayers.push(layers[i].name);
				}
			}

			if (overlayLayers.length > 0) {
				$("#legendimg").attr("src", "%(ows_url)s&amp;SERVICE=WMS&amp;VERSION=1.1.1&amp;REQUEST=GetLegendGraphic&amp;LAYERS="
				+ overlayLayers.join(',') +
				"&amp;SRS=%(projection)s&amp;BBOX=%(extent)s&amp;FORMAT=image/png&amp;HEIGHT=10&amp;WIDTH=10");
			}

			else {
				$("#legendimg").attr("src", "static/white.png");
			}
		}

		map.events.register('changelayer', map, function (e) {
			loadLegend();
		});

		loadLegend();
	""" % c

	# head and javascript end
	html += """
		});
	</script>
	</head>
	"""

	# body
	html += """
	<body>
	<h2>Mapfile: %(mapfile)s</h2>
		<div id="container">
		<div id="map"></div>

		<div id="legend">
			<img id="legendimg" src="static/white.png" alt="legend" />
		</div>

		<div id="info">
			<strong>scales</strong>: %(scales)s <br />
			<strong>projection</strong>: %(projection)s, <strong>units</strong>: %(units)s, <strong>resolution</strong>: %(resolution)s DPI,
			<strong>center</strong>: %(center_coord1)s, %(center_coord2)s
		</div>
		</div>
	</body>
	</html>
	""" % c

	return html


def server(environ, start_response):
	"""Return server response."""

	req = environ['PATH_INFO'].split('/')

	# return HTML application
	if req[1] == '':

		# collect configuration values from mapfile
		c = {}
		c['mapfile'] = os.path.abspath(options.mapfile)
		m = mapscript.mapObj(c['mapfile'])
		
		c['units'] = MS_UNITS[m.units]
		c['resolution'] = int(m.resolution)

		try:
			c['projection'] = m.getProjection().split('=')[1]
		except IndexError:
			c['projection'] = 'epsg:4326'

		if options.extent:
			c['extent'] = options.extent

			e = c['extent'].split(',')
			c['center_coord1'] = mapscript.rectObj(float(e[0]), float(e[1]), float(e[2]), float(e[3])).getCenter().x
			c['center_coord2'] = mapscript.rectObj(float(e[0]), float(e[1]), float(e[2]), float(e[3])).getCenter().y
		else:
			c['extent'] = '%s, %s, %s, %s' % (m.extent.minx, m.extent.miny, m.extent.maxx, m.extent.maxy)
			c['center_coord1'] = m.extent.getCenter().x
			c['center_coord2'] = m.extent.getCenter().y

		c['scales'] = options.scales
		c['resolutions'] = ', '.join(str(r) for r in _get_resolutions(c['scales'].split(','), c['units'], c['resolution']))

		c['root_layer'] = m.name

		if options.layers:
			c['layers'] = options.layers.split(',')
		else:
			c['layers'] = []
			numlays = m.numlayers
			for i in range(0, numlays):
				c['layers'].append(m.getLayer(i).name)

		c['ows_url'] = 'http://127.0.0.1:%s/ows/?map=%s' % (options.port, c['mapfile'])

		start_response('200 OK', [('Content-type','text/html')])
		return application(c)


	# return static files as css, javascript or images
	elif req[1] == 'static':
		if req[-1][-3:] == 'css':
			headers = [('Content-type','text/css')]
		elif req[-1][-2:] == 'js':
			headers = [('Content-type','text/javascript')]
		elif req[-1][-4:] == 'html':
			headers = [('Content-type','text/html')]
		elif req[-1][-3:] == 'png':
			headers = [('Content-type','image/png')]

		start_response('200 OK', headers)
		return open('/'.join(i for i in req[1:]), 'rb').read()


	# return map image
	elif req[1] == 'ows':
		qs = dict(parse_qsl(environ['QUERY_STRING']))
		try:
			m = mapscript.mapObj(qs.get('MAP', qs.get('map')))

		except Exception, err:
			start_response('500 ERROR', [('Content-type','text/plain')])
			return err

		# set extent if requested
		if options.extent:
			e = options.extent.split(',')
			m.extent = mapscript.rectObj(float(e[0]), float(e[1]), float(e[2]), float(e[3]))

		# set connection if requested
		if options.connection:
			numlays = m.numlayers
			for i in range(0, numlays):
				m.getLayer(i).connection = options.connection

		# prepare OWS request
		mreq = mapscript.OWSRequest()
		for k,v in qs.items():
			mreq.setParameter(k, v)
		m.loadOWSParameters(mreq)

		start_response('200 OK', [('Content-type', qs["FORMAT"])])
		
		if qs["REQUEST"].upper() == 'GETMAP':
			return m.draw().getBytes()
		elif qs["REQUEST"].upper() == 'GETLEGENDGRAPHIC':
			return m.drawLegend().getBytes()

	else:
		start_response('500 ERROR', [('Content-type','text/plain')])
		return 'ERROR'


def run(port=9991):
	"""Start WSGI server."""

	from wsgiref import simple_server
	httpd = simple_server.WSGIServer(('', port), simple_server.WSGIRequestHandler,)
	httpd.set_app(server)
	try:
		print "Starting server. Point your web browser to 'http://127.0.0.1:%s'." % port
		httpd.serve_forever()
	except KeyboardInterrupt:
		if options.concatenate:
			os.remove(options.mapfile)

		print "Shutting down server."
		sys.exit(0)

if __name__ == "__main__":
	parser = OptionParser()

	parser.add_option("-m", "--mapfile", help="path to UMN MapServer mapfile OR "
		"comma-separated list of mapfiles to concatenate on-the-fly. None of the "
		"mapfiles must not contain main 'MAP' keyword and coresponding 'END' key. "
		"Example: 'map/base.map,map/layers.map' [required]",
		dest="mapfile", action='store', type="string")

	parser.add_option("-e", "--extent", help="extent in comma-separated format to override "
		"'EXTENT' parameter [optional]",
		dest="extent", action='store', type="string")

	parser.add_option("-l", "--layers", help="comma-separated list of layers to use in map. "
		"If not used, layer list is automatically detected from mapfile [optional]",
		dest="layers", action='store', type="string")

	parser.add_option("-c", "--connection", help="string to override 'CONNECTION' parameter of all layers [optional]",
		dest="connection", action='store', type="string")

	parser.add_option("-s", "--scales", help="comma-separated list of scales to use in map [optional]",
		dest="scales", action='store', type="string", default="10000,5000,2000,1000,500")

	parser.add_option("-p", "--port", help="port to run server on [optional]",
		dest="port", action='store', type="int", default=9991)

	parser.add_option("-t", "--test", help="check mapfile syntax and exit [optional]",
		dest="test", action='store_true', default=False)

	(options, args) = parser.parse_args()


	# mapfile option is required. Exit if not given.
	if not options.mapfile:
		print __doc__
		parser.print_help()
		sys.exit(0)

	# concatenate mapfiles if multiple files given
	options.concatenate = False
	if len(options.mapfile.split(',')) > 1:
		options.mapfile = _concatenate_mapfiles(options.mapfile.split(','))
		options.concatenate = True


	# test mapfile only
	if options.test:
		test_mapfile(options.mapfile)

	# run server
	else:
		run(options.port)


# vim: set ts=4 sts=4 sw=4 noet:
