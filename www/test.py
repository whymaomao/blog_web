import ORM 
import asyncio
import os
from models import User, Blog, Comment

#创建异步事件的句柄


async def test():
	await ORM.create_pool(loop = loop,user='www-data',password='www-data',db='awesome')

	#u = User(name='Test',email= 'test@example.com',passwd='1234567890',image='about:blank')
	#await u.save()
	r = await User.findAll()
	print (r)
	r = await User.find('0')
	print(r)
	r = await User.findAll(name='Test')
	print (r)

loop = asyncio.get_event_loop()
loop.run_until_complete(test())
loop.run_forever()

