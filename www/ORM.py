'''
选择MySQL作为网站的后台数据库
 
执行SQL语句进行操作，并将常用的SELECT、INSERT等语句进行函数封装
 
在异步框架的基础上，采用aiomysql作为数据库的异步IO驱动
 
将数据库中表的操作，映射成一个类的操作，也就是数据库表的一行映射成一个对象(ORM)
 
整个ORM也是异步操作
 
预备知识：Python协程和异步IO(yield from的使用)、SQL数据库操作、元类、面向对象知识、Python语法
 
# -*- -----  思路  ----- -*-
    如何定义一个user类，这个类和数据库中的表User构成映射关系，二者应该关联起来，user可以操作表User
     
    通过Field类将user类的属性映射到User表的列中，其中每一列的字段又有自己的一些属性，包括数据类型，列名，主键和默认值
 
'''

import asyncio,logging

import aiomysql

def log(sql,args=()):
	logging.info('SQL: %s' %sql)

#创建一个全局的连接池，每个HTTP请求都从池中获得数据库连接

#**kw是一个dict
async def create_pool(loop,**kw):
	logging.info("create database connection pool...")
	global __pool
 # 理解这里的yield from 是很重要的  
#dict有一个get方法，如果dict中有对应的value值，则返回对应于key的value值，否则返回默认值，例如下面的host，如果dict里面没有  
#'host',则返回后面的默认值，也就是'localhost'  
#这里有一个关于Pool的连接，讲了一些Pool的知识点，挺不错的，<a target="_blank" href="http://aiomysql.readthedocs.io/en/latest/pool.html">点击打开链接</a>，下面这些参数都会讲到，以及destroy__pool里面的  
#wait_closed()  
	__pool = await aiomysql.create_pool(
			host=kw.get('host','localhost'),
			port = kw.get('port',3306),
			user = kw['user'],
			password=kw['password'],
			db=kw['db'],
			charset=kw.get('charset','utf8'),
			autocommit=kw.get('autocommit',True),  #默认自动提交事务，不用手动去提交事务 
			maxsize = kw.get('maxsize',10),
			minsize = kw.get('minsiz',1),
			loop=loop)
	

#封装SQL SELECT语句为select函数

async def select(sql,args,size=None):
	log(sql,args)
	global __pool

	# yield from 将会调用一个子协程，并直接返回调用的结果
	# yield from 从连接中返回一个连接,这个地方已经创建了进程池并和进程池连接了，
	#进程池的创建被封装到了create_pool(loop, **kw)
	#  
	async with __pool.get() as conn:
		#DictCursor is a cursor which returns results as a dict
		async with conn.cursor(aiomysql.DictCursor) as cur:
		#SQL语句的占位符是?，而MySQL的占位符是%s，
		#select()函数在内部自动替换。注意要始终坚持使用带参数的SQL，
		#而不是自己拼接SQL字符串，这样可以防止SQL注入攻击
			await cur.execute(sql.replace('?','%s'),args or ())

			if size:
				#一次性返回size条查询结果，结果是一个list，里面是tuple
				rs = await cur.fetchmany(size)
			else:
				#一次性返回所有的查询结果
				rs = await cur.fetchall()
			
			
		logging.info('rows returned : %s' %len(rs))
			#返回结果是tuple的list
		return rs 


#要执行INSERT,UPDATE,DELETE语句，可以定义一个通用的execute()函数，因为这3种函数
#的执行都需要相同的参数，以及返回一个整数表示影响的行数

async def execute(sql,args,autocommit = True):
	log(sql)
	async with __pool.get() as conn:
		if not autocommit:
			await conn.begin()
		try:
			 # 因为execute类型sql操作返回结果只有行号，不需要dict  
			async with conn.cursor(aiomysql.DictCursor) as cur:
				await cur.execute(sql.replace('?','%s'),args)
				affected = cur.rowcount
			if not autocommit:
				await conn.commit()
		except BaseException as e:
			if not autocommit:
				await conn.rollback()
			raise

		return affected

# 这个函数主要是把查询字段计数 替换成sql识别的?  
# 比如说：insert into  `User` (`password`, `email`, `name`, `id`) values (?,?,?,?)  看到了么 后面这四个问号  
def create_args_string(num):
	L = []
	for n in range(num):
		L.append('?')
	return ','.join(L)

#定义Field类，负责保存（数据库）表的字段名和字段类型
class Field(object):
	#表的字段包含名字、类型、是否为表的主键和默认值
	def __init__(self,name,column_type,primary_key,default):
		self.name = name
		self.column_type = column_type
		self.primary_key = primary_key
		self.default = default

	# 返回 表名字 字段名 和字段类型 
	def __str__(self):
		return '<%s,%s:%s>' %(self.__class__.__name__,self.column_type,self.name)

# 定义数据库中五个存储类型 
class StringField(Field):
	def __init__(self,name=None,primary_key = False, default = None,ddl = 'varchar(100)'):
		super().__init__(name,ddl,primary_key,default)

#boolean值不可能成为主键
class BooleanField(Field):
	def __init__(self, name = None, default = False):
		super().__init__(name,'boolean',False,default)

class IntegerField(Field):
	def __init__(self,name = None,primary_key = False,default = 0):
		super().__init__(name,'bigint',primary_key,default)

class FloatField(Field):
	def __init__(self,name = None,primary_key = False,default = 0.0):
		super().__init__(name,'real',primary_key,default)

class TextField(Field):
	def __init__(self,name = None, default = None):
		super().__init__(name,'text',False,default)


# class Model(dict,metaclass=ModelMetaclass):  
   
# -*-定义Model的元类  
   
# 所有的元类都继承自type  
# ModelMetaclass元类定义了所有Model基类(继承ModelMetaclass)的子类实现的操作  
   
# -*-ModelMetaclass的工作主要是为一个数据库表映射成一个封装的类做准备：  
# ***读取具体子类(user)的映射信息  
# 创造类的时候，排除对Model类的修改  
# 在当前类中查找所有的类属性(attrs)，如果找到Field属性，就将其保存到__mappings__的dict中，
# 同时从类属性中删除Field(防止实例属性遮住类的同名属性)  
# 将数据库表名保存到__table__中  
   
# 完成这些工作就可以在Model中定义各种数据库的操作方法  
# metaclass是类的模板，所以必须从`type`类型派生：		

class ModalMetaclass(type):
    # __new__控制__init__的执行，所以在其执行之前  
    # cls:代表要__init__的类，此参数在实例化时由Python解释器自动提供(例如下文的User和Model)  
    # bases：代表继承父类的集合  
    # attrs：类的方法集合  
    def __new__(cls,name,bases,attrs):
    	 # 排除model 是因为要排除对model类的修改  
    	if name == 'Model':
    	 	return type.__new__(cls,name,bases,attrs)
    	 # 获取table名称 为啥获取table名称 至于在哪里我也是不明白握草  
    	tableName = attrs.get('__table__',None) or name
    	logging.info('found model:%s (table:%s)' % (name,tableName))
    	  # 获取Field所有主键名和Field  
    	mappings = dict()
    	  #field保存的是除主键外的属性名  
    	fields = []
    	primaryKey = None
    	# 这个k是表示字段名  
    	for k,v in attrs.items():
    	 	if isinstance(v,Field):
    	 		logging.info(' found mappings: %s ==> %s' %(k,v))
    	 		mappings[k] = v
    	 		if v.primary_key:
    	 			if primaryKey:
    	 			# 这里很有意思 当第一次主键存在primaryKey被赋值 后来如果再出现主键的话就会引发错误 
    	 				raise StandardError('Duplicate primary key for field: %s' %k)
    	 			primaryKey = k# 也就是说主键只能被设置一次  
    	 		else:
    	 			fields.append(k)	
    	  #如果主键不存在也将会报错，在这个表中没有找到主键，一个表只能有一个主键，而且必须有一个主键  
    	if not primaryKey:
    	 	raise StandardError('Primary Key not found')
    	   # w下面位字段从类属性中删除Field 属性在当前类（比如User）中查找定义的类的所有属性，
    	   #如果找到一个Field属性，就把它保存到一个__mappings__的dict中，
    	   #同时从类属性中删除该Field属性，否则，容易造成运行时错误（实例的属性会遮盖类的同名属性）；    	   
    	for k in mappings.keys():
    	 	attrs.pop(k)
    	# 保存除主键外的属性为''列表形式  
        # 将除主键外的其他属性变成`id`, `name`这种形式
    	escaped_fields = list(map(lambda f: '`%s`' % f, fields))
    	attrs['__mappings__'] = mappings
    	attrs['__table__'] = tableName
    	attrs['__primary_key__'] = primaryKey
    	attrs['__fileds__'] = fields
    	attrs['__select__'] = 'select `%s`,%s from `%s`' %(primaryKey,','.join(escaped_fields),tableName)
    	attrs['__insert__'] = 'insert into `%s` (%s,`%s`) values (%s)'% (tableName,','.join(escaped_fields),primaryKey,create_args_string(len(escaped_fields)+1))
    	attrs['__update__'] = 'update `%s` set %s where `%s`=?' %(tableName,','.join(map(lambda f: '`%s`=?'%(mappings.get(f).name or f),fields)),primaryKey)
    	attrs['__delete__'] = 'delete from `%s` where `%s`=?' %(tableName,primaryKey)
    	return type.__new__(cls,name,bases,attrs)

   
# 定义ORM所有映射的基类：Model  
# Model类的任意子类可以映射一个数据库表  
# Model类可以看作是对所有数据库表操作的基本定义的映射  
   
   
# 基于字典查询形式  
# Model从dict继承，拥有字典的所有功能，同时实现特殊方法__getattr__和__setattr__，能够实现属性操作  
# 实现数据库操作的所有方法，定义为class方法，所有继承自Model都具有数据库操作方法 

class Model(dict,metaclass = ModalMetaclass):
	def __init__(self,**kw):
		super(Model,self).__init__(**kw)

	def __getattr__(self,key):
		try:
			return self[key]
		#如果不知道dict中是否有key的值  
		#如果用 dict[key] 读取会报KeyError异常  
		except KeyError:
			raise AttributeError(r"'Model' object has no attribute '%s'"%key)


	def __setattr__(self,key,value):
		self[key] = value

	def getValue(self,key):
		#getattr(object, name[,default])
		#获取对象object的属性或者方法，如果存在打印出来，如果不存在，打印出默认值，默认值可选。
		#需要注意的是，如果是返回的对象的方法，返回的是方法的内存地址，如果需要运行这个方法，
		#可以在后面添加一对括号。
		return getattr(self,key,None)

	def getValueOrDefault(self,key):
		value = getattr(self,key,None)
		#获取值，如果没有的话就是用默认值
		if value is None:
			field = self.__mappings__[key]
			if field.default is not None:
				#callable(object)

				#检查对象object是否可调用。如果返回True，object仍然可能调用失败；
				#但如果返回False，调用对象ojbect绝对不会成功。
				value = field.default() if callable(field.default) else field.default
				logging.debug('using default value for %s :%s' %(key,str(value)))
				setattr(self,key,value)
		return value

	@classmethod
	   # 类方法有类变量cls传入，从而可以用cls做一些相关的处理。并且有子类继承时，
	   # 调用该类方法时，传入的类变量cls是子类，而非父类。
	async def findAll(cls,where = None,args=None,**kw):
		'find object by where clause'
		sql = [cls.__select__]
		if where:
			sql.append('where')
			sql.append(where)
		if args is None:
			args = []

		orderBy = kw.get('orderBy',None)
		if orderBy:
			sql.append('order By')
			sql.append(orderBy)

		limit = kw.get('limit',None)
		if limit is not None:
			sql.append('limit')
			if isinstance(limit,int):
				sql.append('?')
				args.append(limit)
			elif isinstance(limit,tuple) and len(limit) == 2:
				sql.append('?,?')
				args.extend(limit)
			else:
				#str()函数把数值转换为字符串
				raise ValueError('Invalid limit value: %s'% str(limit))
		#返回的rs是一个元素是tuple的list 
		rs = await select(' '.join(sql),args)
		# **r 是关键字参数，构成了一个cls类的列表，其实就是每一条记录对应的类实例  
		return [cls(**r) for r in rs]

	@classmethod
	async def findNumber(cls,selectField,where=None,args = None):
		'find number by select and where'
		sql =  ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
		if where:
			sql.append('where')
			sql.append(where)
		rs = await select(' '.join(sql),args,1)
		if len(rs) == 0:
			return None
		return rs[0]['_num_']


	async def save(self):
		args = list(map(self.getValueOrDefault,self.__fileds__))
		args.append(self.getValueOrDefault(self.__primary_key__))
		rows = await execute(self.__insert__,args)
		if rows != 1:
			logging.warn('failed to insert record: affected rows: %s' %rows)

	async def update(self):
		args = list(map(self.getValue(self.__fileds__)))
		args.append(self.getValue(self.__primary_key__))
		rows = await execute(self.__update__,args)
		if rows != 1:
			logging.warn('failed to update by primary key: affected rows:%s'%rows)

	async def romove(self):
		args = [self.getValue(self.__primary_key__)]
		rows = await execute(self.__delete__,args)
		if rows != 1:
			logging.warn('failed to remove by primary key: affected rows:%s' %rows)


	@classmethod
	async def find(cls, pk):
		' find object by primary key. '
		rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
		if len(rs) == 0:
			return None
		return cls(**rs[0])


if __name__ == '__main__':
	class User(Model):
		id = IntegerField('id',primary_key = True)
		name = StringField('username')
		email = StringField('email')
		password = StringField('password')

	u = User(id=12345,name='pp',email = 'pp@seu',password = 'password')
	print(u)
	u.save()
	print(u)