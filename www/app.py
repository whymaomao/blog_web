import logging;logging.basicConfig(level=logging.INFO)

import asyncio,os,json,time
from datetime import datetime

from aiohttp import web
'''
Jinja2 使用一个名为 Environment 的中心对象。
这个类的实例用于存储配 置、全局对象，
并用于从文件系统或其它位置加载模板。
即使你通过:class:Template 类的构造函数用字符串创建模板，
也会为你自动创建一个环境，尽管是共享的。
'''
from jinja2 import Environment,FileSystemLoader

import ORM
from coroweb import add_routes, add_static

def init_jinja2(app,**kw):
	logging.info('init jinja2...')
	options = dict(
		#如果设置为true，则默认情况下启用XML / HTML自动转义功能。
		autoescape = kw.get('autoescape',True),
		#The string marking the begin of a block. Defaults to '{%'.
		block_start_string = kw.get('block_start_string','{%'),
		#The string marking the end of a block. Defaults to '%}'.
		block_end_string = kw.get('block_end_string','%}'),
		#The string marking the begin of a print statement. Defaults to '{{'.
		variable_start_string = kw.get('variable_start_string','{{'),
		variable_end_string = kw.get('variable_end_string','}}'),
		#Some loaders load templates from locations where the template sources may change 
		#(ie: file system or database). If auto_reload is set to True (default)
		# every time a template is requested the loader checks if the source changed and if yes,
		# it will reload the template.
		# For higher performance it’s possible to disable that.
		auto_reload = kw.get('auto_reload',True)
		)
	path = kw.get('path',None)
	if path is None:
		path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'templates')
	logging.info('set jinja2 template path:%s' %path)
	env = Environment(loader = FileSystemLoader(path),**options)
	filters = kw.get('filters',None)
	if filters is not None:
		for name,f in filters.items():
			env.filters[name] = f
	app['__templating__'] = env

async def logger_factory(app,handler):
	async def logger(request):
		logging.info('Request: %s %s' %(request.method, request.path))
		return (await handler(request))
	return logger

async def data_factory(app,handler):
	async def parse_data(request):
		if request.method == 'POST':
			if request.content_type.startswith('application/json'):
				request.__data__ = await request.json()
				logging.info('request json: %s' % str(request.__data__))
			elif request.content_type.startswith('application/x-www-form-urlencoded'):
				request.__data__ = await request.post()
				logging.info('request form: %s' %str(request.__data__))
		return (await handler(request))
	return parse_data

async def response_factory(app,handler):
	async def response(request):
		logging.info('Response handler...')
		r = await handler(request)

		if isinstance(r,web.StreamResponse):
			return r

		if isinstance(r,bytes):
			resp = web.Response(body = r)
			resp.content_type = 'application/octet-stream'
			return resp

		if isinstance(r,str):
			if r.startswith('redirect'):
				return web.HTTPFound(r[9:])
			resp = web.Response(body = r.encode('utf-8'))
			resp.content_type = 'text/html;charset=utf-8'
			return resp

		if isinstance(r,dict):
			template = r.get('__template__')
			logging.info('Response handler templating...')
			if template is None:
				#json.dumps将一个数据结构转换成json格式
				resp = web.Response(body = json.dumps(r,ensure_ascii = False,default = lambda o:o.__dict__).encode('utf-8'))
				resp.content_type = 'application/json;charset=utf-8'
				return resp
			else:
				resp = web.Response(body = app['__templating__'].get_template(template).render(**r).encode('utf-8'))
				resp.content_type = 'text/html;charset=utf-8'
				return resp

		if isinstance(r,int) and r>= 100 and r<600:
			return web.Response(r)

		if isinstance(r,tuple) and len(r) == 2:
			t,m = r
			if isinstance(t,int) and t >= 100 and t < 600:
				return web.Response(t,str(m))
		#default:
		resp = web.Response(body = str(r).encode('utf-8'))
		resp.content_type = 'text/plain;charset=utf-8'
		return resp
	return response

def datatime_filter(t):
	delta = int(time.time() - t)
	if delta < 60:
		#以Unicode表示的字符串
		return u'1分钟前'
	if delta < 3600:
		return u'%s分钟前'%(delta //60)
	if delta < 86400:
		return u'%s小时前'%(delta //3600)
	if delta < 604800:
		return u'%s天前'%(delta //86400)
	dt = datetime.fromtimestamp(t)
	return u'%s年%s月%s日'%(dt.year,dt.month,dt.day)

async def init(loop):
	await ORM.create_pool(loop = loop,user='www-data',password='www-data',db='awesome')
	#await ORM.create_pool(loop = loop,host='127.0.0.1',port = 3306,user='www',password='www',db='awesome')
	app = web.Application(loop = loop,middlewares=[logger_factory,response_factory])
	init_jinja2(app,filters = dict(datetime=datatime_filter))
	add_routes(app,'handlers')
	add_static(app)
	srv = await loop.create_server(app.make_handler(),'127.0.0.1',9000)
	logging.info('server started at http://127.0.0.1:9000')
	return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
'''
def index(request):
	return web.Response(body=b'<h1>Awesome</h1>',content_type='text/html',charset='UTF-8')

@asyncio.coroutine
def init(loop):
	app = web.Application(loop = loop)
	app.router.add_route('GET','/',index)
	srv = yield from loop.create_server(app.make_handler(),'127.0.0.1',9000)
	logging.info('server started at http://127.0.0.1:9000...')
	return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
'''