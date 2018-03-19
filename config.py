# -*- coding:utf-8 -*-
from werkzeug.routing import BaseConverter
import redis


class Config:
    """基本配置参数"""
    SECRET_KEY = "TQ6uZxn+SLqiLgVimX838/VplIsLbEP5jV7vvZ+Ohqw="
    SQLALCHEMY_DATABASE_URI = 'mysql://root:123@localhost/flask_ihome'  # flask_ihome数据库
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_COMMIT_ON_TEARDOWN = False

    # 创建redis实例用到的参数
    REDIS_HOST = "127.0.0.1"
    REDIS_PORT = 6379
    DB = 0

    # 下面的3个参数是from flask_session import Session类中需要的
    SESSION_TYPE = 'redis'  # 保存session数据的地方
    SESSION_USE_SIGNER = True  # 为session id进行签名
    SESSION_REDIS = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=DB)  # 保存session数据的redis配置
    PERMANENT_SESSION_LIFETIME = 86400  # session数据的有效期秒 一天


class DevelopmentConfig(Config):
    """开发模式的配置参数"""
    DEBUG = True  # 调试模式


class ProductionConfig(Config):
    """生产环境的配置参数"""
    pass  # 默认Debug=false


config = {
    'development': DevelopmentConfig,  # 开发模式
    'prodution': ProductionConfig,  # 生产/线上模式
}

"""就是配置信息"""
