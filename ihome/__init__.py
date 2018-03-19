# -*- coding:utf-8 -*-
from flask import Flask
from config import Config, config
from flask_sqlalchemy import SQLAlchemy
# 导入flask 扩展包
from flask_session import Session
# 不止Session模块用到redis我们自己也要用redis
import redis
# 导入自定义转换器,注册
from utils.commons import RegexConverter
# 导入验证csrf包的东西
from flask_wtf import CSRFProtect

# 日志相关导入包
import logging
from logging.handlers import RotatingFileHandler

db = SQLAlchemy()  # db = SQLAlchemy(app)  SQLAlchemy实例
# 不止Session模块用到redis我们自己也要用redis
redis_client = redis.StrictRedis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, db=Config.DB)

csrf = CSRFProtect()

logging.basicConfig(level=logging.DEBUG)
# 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024 * 100, backupCount=10)
# 创建日志记录的格式                 日志等级    输入日志信息的文件名 行数    日志信息
formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
# 为刚创建的日志记录器设置日志记录格式
file_log_handler.setFormatter(formatter)
# 为全局的日志工具对象（应用程序实例app使用的）添加日后记录器
logging.getLogger().addHandler(file_log_handler)


def create_app(config_name):
    app = Flask(__name__)
    # app.config.from_object(Config) # 不够灵活配置
    app.config.from_object(config[config_name])
    # 添加转换器到程序实例上
    app.url_map.converters['regex'] = RegexConverter
    db.init_app(app)
    csrf.init_app(app)  # 让csrf检验在Flask起作用
    Session(app)  # 让Session在flask起作用
    # 为app 添加api蓝图应用
    from api import api
    app.register_blueprint(api, url_prefix="/api/v1.0")  # url_prefix="/api/v1.0"

    # 导入蓝图对象 因为注册使用蓝图对象
    from .web_page import html
    app.register_blueprint(html)  # 使蓝图对象在flask app中起作用

    return app


"""就是初始化app关联操作"""
