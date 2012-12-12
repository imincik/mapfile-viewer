#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
UMN Mapserver mapfile viewer.
"""

import sys, os
from optparse import OptionParser
from cgi import parse_qsl
import mapscript

MS_UNITS = {
	3: 'm',
	4: 'mi',
	6: 'px'
}

def _get_resolutions(scales, units, resolution=96):
	resolution = float(resolution)
	factor = {'inches': 1.0, 'ft': 12.0, 'mi': 63360.0,
			'm': 39.3701, 'km': 39370.1, 'dd': 4374754.0}
	
	inches = 1.0 / resolution
	monitor_l = inches / factor[units]
	
	resolutions = []
	for m in scales:
		resolutions.append(monitor_l * int(m))
	return resolutions

def get_application(c):
	html = ''

	# head and javascript start
	html = html + """
		<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
		<html xmlns="http://www.w3.org/1999/xhtml">
		<head>
			<meta http-equiv="content-type" content="text/html; charset=utf-8" />
			<title>Mapfile: %(mapfile)s</title>
			<link rel="stylesheet" type="text/css" href="static/theme/default/style.css" />
			<link rel="stylesheet" type="text/css" href="static/theme/dark/style.css" />
			<link rel="stylesheet" type="text/css" href="static/viewer.css" />

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
	<h2>Mapfile: %(mapfile)s</h2>
		<div id="map" style="width: 100%%; height: 700px; border: 2px solid #222;"></div>
		<p>
		<strong>scales</strong>: %(scales)s <br />
		<strong>units</strong>: %(units)s, <strong>resolution</strong>: %(resolution)s DPI, <strong>center</strong>: %(center_coord1)s, %(center_coord2)s <br />
		</p>
	</body>
	</html>
	""" % c

	return html


def server(environ, start_response):
	req = environ['PATH_INFO'].split('/')

	# return HTML application
	if req[1] == '':
		# collect configuration values from mapfile
		mf = mapscript.mapObj(options.mapfile)

		c = {}
		c['mapfile'] = os.path.abspath(options.mapfile)
		
		c['units'] = MS_UNITS[mf.units]
		c['resolution'] = int(mf.resolution)
		c['projection'] = mf.web.metadata.get('wms_srs').split(' ')[0]

		c['extent'] = '%s, %s, %s, %s' % (mf.extent.minx, mf.extent.miny,
			mf.extent.maxx, mf.extent.maxy)
		c['center_coord1'] = mf.extent.getCenter().x
		c['center_coord2'] = mf.extent.getCenter().y

		c['scales'] = options.scales
		c['resolutions'] = ', '.join(str(r) for r in _get_resolutions(c['scales'].split(','), c['units'], c['resolution']))


		if options.layers:
			c['layers'] = options.layers.split(',')
		else:
			c['layers'] = []
			c['layers'].append(mf.name) # add all WMS layers

			numlays = mf.numlayers
			for i in range(0, numlays):
				c['layers'].append(mf.getLayer(i).name)


		c['wms_url'] = 'http://localhost:9991/ows/?map=%s' % (c['mapfile'])

		start_response('200 OK', [('Content-type','text/html')])
		return get_application(c)


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
			mobj = mapscript.mapObj(qs.get('MAP', qs.get('map')))
		except Exception, err:
			start_response('500 ERROR', [('Content-type','text/plain')])
			return err

		mreq = mapscript.OWSRequest()
		for k,v in qs.items():
			mreq.setParameter(k, v)
		mobj.loadOWSParameters(mreq)

		start_response('200 OK', [('Content-type','image/png')])
		return mobj.draw().getBytes()

	else:
		start_response('500 ERROR', [('Content-type','text/plain')])
		return 'ERROR'


def run(port=9991):
	from wsgiref import simple_server
	httpd = simple_server.WSGIServer(('', port), simple_server.WSGIRequestHandler,)
	httpd.set_app(server)
	try:
		print "Listening on port %s." % port
		httpd.serve_forever()
	except KeyboardInterrupt:
		print "Shutting down."


if __name__ == "__main__":
	parser = OptionParser()

	parser.add_option("-m", "--mapfile", help="mapfile path [required]",
		dest="mapfile", action='store', type="string")

	parser.add_option("-s", "--scales", help="comma-separated list of scales to use in map [optional]",
		dest="scales", action='store', type="string", default="10000,5000,2000,1000,500")

	parser.add_option("-l", "--layers", help="comma-separated list of layers to use in map [optional]",
		dest="layers", action='store', type="string")

	parser.add_option("-p", "--port", help="port to run server on [optional]",
		dest="port", action='store', type="int", default=9991)

	(options, args) = parser.parse_args()

	if not options.mapfile:
		print __doc__
		parser.print_help()
		sys.exit(0)

	run(options.port)


# vim: set ts=4 sts=4 sw=4 noet:
