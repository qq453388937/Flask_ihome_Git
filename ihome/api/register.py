# -*- coding:utf-8 -*-
from flask import jsonify, make_response, request, session  # session时使用
from . import api  # 导入蓝图对象
# 导入cptcha扩展包
from ihome.utils.captcha.captcha import captcha
# 导入redis实例
from ihome import redis_client
# 导入常量文件
from ihome import constants
# 导入flask内置的对象
from flask import current_app, session
# 导入状态码
from ihome.utils.response_code import RET
# 导入正则
import re
# 导入随机数模块
import random
# 导入模型类
from ihome.models import *
# 导入数据库db
from ihome import db
# 导入登陆验证装饰器
from ihome.utils.commons import login_required


@api.route('/imagecode/<image_code_id>', methods=['GET'])
def generate_image_code(image_code_id):
    # 调用captcha扩展包,生成图片验证码,
    name, text, image = captcha.generate_captcha()
    try:
        redis_client.setex('ImageCode_' + image_code_id, constants.IMAGE_CODE_REDIS_EXPIRES, text)
    except Exception as e:
        # 记录项目日志
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="保存图片导redis失败")
    else:
        response = make_response(image)
        response.headers['Content-Type'] = 'image/jpg'  # 不影响数据展示
        # 返回正确结果,图片数据
        return response


@api.route('/smscode/<mobile>', methods=['GET'])
def send_message(mobile):
    # 获取参数
    image_code = request.args.get('text')
    image_code_id = request.args.get('id')
    # 校验接收参数,校验手机号
    if not all([mobile, image_code, image_code_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不完整")
    # 检查手机号码格式
    if not re.match(r'1[3456789]\d{9}', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg="手机号格式错误")
    # 查询数据,获取redis中验证码
    try:
        real_image_text = redis_client.get('ImageCode_' + image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="redis数据库获取验证码错误")
    if not real_image_text:
        return jsonify(errno=RET.NODATA, errmsg="验证码过期")
    try:
        # 删除redis中验证码,只允许请求一次
        redis_client.delete('ImageCode_' + image_code_id)
    except Exception as e:
        current_app.logger.error(e)
    if real_image_text.lower() != image_code.lower():
        return jsonify(errno=RET.DATAERR, errmsg="图片验证码比较错误")
    # 查询数据库,确认用户未注册
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        return jsonify(errno=RET.DATAERR, errmsg="查询用户未注册异常")
    else:
        if user is not None:
            return jsonify(errno=RET.DATAEXIST, errmsg="手机号已注册")

    # 生成随机数发送短信
    sms_code = "%04d" % random.randint(0, 9999)
    # 保存短信验证码到redis
    try:
        redis_client.setex("SMSCode_" + mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="短信验证码存储redis失败")
    # 发送短信
    from ihome.lib.yuntongxun.SendTemplateSMS import CCP
    ccp = CCP.instance()
    b = ccp.sendTemplateSMS(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES / 60], 1)
    # 返回对应结果
    if not b:
        current_app.logger.error("云通讯发送短信异常")
        return jsonify(errno=RET.THIRDERR, errmsg="云通讯发送短信异常")
    return jsonify(errno=RET.OK, errmsg="ok!!!")


@api.route('/users', methods=['POST'])
def register_user():
    # 获取请求体中的数据request.data + json.loads()
    print(request.data)
    print(request.get_json())
    user_data = request.get_json()
    # 判断获取结果
    if not user_data:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    # 获取详细的参数信息
    mobile = user_data.get("mobile")
    sms_code = user_data.get("sms_code")
    password = user_data.get("password")
    # 检查参数的完整性
    if not all([mobile, sms_code, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数缺失!!")
    # 校验手机号格式
    if not re.match(r"^1[3-9]\d{9}$", mobile):
        return jsonify(errno=RET.PARAMERR, errmsg="手机号正则不通过")
    # 检查手机号是否注册
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="校验手机号是否注册异常")
    else:
        if user:
            return jsonify(errno=RET.DATAERR, errmsg="用户手机号已经注册")

    # 获取redis数据库中的验证码
    try:
        real_sms_code = redis_client.get("SMSCode_" + mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询redis验证码异常")
    # 判断redis中验证码是否过期
    if not real_sms_code:
        return jsonify(errno=RET.NODATA, errmsg="短信验证码过期")
    # 比较
    if real_sms_code != str(sms_code):
        return jsonify(errno=RET.DATAERR, errms="短信验证码错误")
    # 删除短信验证码在redis中的缓存
    try:
        redis_client.delete("SMSCode_" + mobile)
    except Exception as e:
        current_app.logger.error(e)  # 删除失败没关系,可以自动过期,不影响注册流程
    # 插入注册信息保存数据
    user_model = User(mobile=mobile, name=mobile)
    # 加密密码
    user_model.password = password
    try:
        db.session.add(user_model)  # add_all([a,b,c])
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="注册存储失败")
    # 缓存用户数据
    else:
        session['user_id'] = user_model.id
        session['mobile'] = user_model.mobile
        session['name'] = mobile  # 用户登录是user.name,用户有可能修改用户名
        return jsonify(errno=RET.OK, errmsg="注册成功!session存储成功!"
                       , data=user.to_dict())





