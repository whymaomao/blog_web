#!/usr/bin/env python3
#-*- coding:utf-8 -*-

'''
configuration
'''

import config_default

class Dict(dict):
	'''
	simple dict but support access as x.y style
	'''
	def __init__(self,names=(),values=(),**kw):
		super(Dict,self).__init__(**kw)
		for k,v in zip(names,values):
			self[k] = v

	def __getattr__(self,key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Dict' object has no attribute '%s'" %key)

	def __setattr__(self,key,value):
		self[key] = value


def merge(defaults,override):
	r = {}
	for k,v in defaults.items():
		if k in override:
			if isinstance(v,dict):
				#merge可迭代对象合并
				r[k] = merge(v,override[k])
			else:
				r[k] = override[k]

		else:
			r[k] = v
	return r
#这个toDict的主要功能是添加一种取值方式a_dict.key，相当于a_dict['key']，
#这个功能不是必要的，我的项目放弃实现这一功能
def toDict(d):
	D = Dict()
	for k,v int d.items()：
		D[k] = toDict(v) if isinstance(v,dict) else v
	return D 

configs = config_default.configs

try:
	import config_override
	configs = merge(configs,config_override.configs)
except ImportError:
	pass

configs = toDict(configs)