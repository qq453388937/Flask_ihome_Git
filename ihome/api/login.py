# -*- coding:utf-8 -*-

# 需要用到api 直接从__init__里面导过来无需重复创建api对象
from flask.json import jsonify

from . import api


@api.route('/login')
def login():
    my_dict = {
        'name': 'aaa',
        'age': 18,
    }
    # jsonify 命名参数和传字典都会转换为json对象
    return jsonify(my_dict)
    # return '123'
