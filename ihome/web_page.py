# -*- coding:utf-8 -*-

# 蓝图导包
from flask import Blueprint, current_app, make_response, session
# csrf导包,给所有静态页面设置csrf
from flask_wtf import csrf

# 创建蓝图对象
html = Blueprint('html', __name__)


# 优化原始静态访问地址 否则/static/html/my.html 处理静态请求
@html.route("/<regex('.*'):filename>")
def web_page(filename):
    print(filename)
    if not filename:
        filename = "html/index.html"
    elif filename == 'favicon.ico':
        pass
    else:
        filename = "html/" + filename
    csrf_token = csrf.generate_csrf()
    # 把具体的文件返回给浏览器 make_response,current_app 会自动去找/static下的静态文件
    response = make_response(current_app.send_static_file(filename))
    response.set_cookie('csrf_token', csrf_token)  # 设置cookie
    return response


