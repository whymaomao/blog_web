import inspect

def a(a,b=0,*c,d,e=1,**f):
	pass

aa = inspect.signature(a)
print("inspect.signature (fn)是:%s" %aa)
print("inspect.signature (fn)的类型是:%s" %(type(aa)))
print("\n")

bb = inspect.signature(a).parameters
print("signature.parameters属性是:%s" %bb)
print("signature.parameters属性的类型是:%s" %type(bb))
print("\n")

for cc,dd in bb.items():
	print("mappingproxy.items()返回的两个值分别是:%s和%s" %(cc,dd))
	print("mappingproxy.items()返回的两个值的类型分别是：%s和%s" % (type(cc), type(dd)))
	print("\n")
	ee = dd.kind
	print("Parameter.kind属性是:%s" %ee)
	print("Parameter.kind属性的类型是:%s"%type(ee))
	print("\n")
	gg = dd.default
	print("Parameter.default属性是:%s"%gg)
	print("Parameter.default属性的类型是:%s"%type(gg))
	print("\n")

ff = inspect.Parameter.KEYWORD_ONLY
print("inspect.Parameter.KEYWORD_ONLY的值是:%s" % ff)
print("inspect.Parameter.KEYWORD_ONLY的类型是:%s" % type(ff))