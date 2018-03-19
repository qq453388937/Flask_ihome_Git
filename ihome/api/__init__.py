# -*- coding:utf-8 -*-
# 导入蓝图对象
from flask import Blueprint

# 这个蓝图对象是为了处理我们的动态请求而web_page里面的蓝图对象是为了处理静态请求
api = Blueprint('api', __name__)

# 防止循环引用下放 交错导入
# 关联第三个文件 这个可以无限下放只要注册了就可以
"""注意再次拆分出去的文件需要把文件再次导入到创建蓝图实例文件中的地方便于追加注册"""

from . import login
from . import register
from . import passport




@api.after_request  # 请求钩子不止app可以用,蓝图也可以用
def after_request(response):
    if response.headers.get('Content-Type').startswith('text'):
        response.headers['Content-Type'] = 'application/json'
    return response
