# -*- coding:utf-8 -*-
from . import api  # 导入蓝图对象
from flask import jsonify, make_response, request, session, g  # session时使用
# 导入状态码
from ihome.utils.response_code import RET
# 导入redis实例
from ihome import redis_client
# 导入常量文件
from ihome import constants
# 导入flask内置的对象
from flask import current_app, session
# 导入模型类
from ihome.models import *
# 导入数据库db
from ihome import db
# 导入登陆验证装饰器
from ihome.utils.commons import login_required
# 导入七牛云
from ihome.utils.image_storage import storage
# 导入正则模块
import re


@api.route('/sessions', methods=['POST'])
def my_login():
    """登陆接口"""
    # 获取json格式data
    json_dict = request.get_json()
    if not json_dict:
        return jsonify(errno=RET.PARAMERR, errmsg="参数jsondict不存在")
    mobile = json_dict.get('mobile')
    password = json_dict.get('password')
    if not all([mobile, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不完整")
    if not re.match(r'1[3-9]\d{9}', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg="手机号格式错误")

    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询用户信息异常")
    if not user or not user.check_password(password):
        return jsonify(errno=RET.SESSIONERR, errmsg="用户名或密码错误")

    # 用户名密码正确缓存用户信息
    session['user_id'] = user.id
    session['name'] = user.name
    session['mobile'] = mobile
    # return jsonify(errno=RET.OK, errmsg="ok", data={'user_id': user.id})
    return jsonify(errno=RET.OK, errmsg="ok", data=dict(user_id=user.id))


@api.route("/user", methods=["GET"])
@login_required
def get_user_profile():
    """获取用户信息"""
    # 从redis中获取user_id 是从loginrequired获取过了无需重复获取
    user_id = g.user_id
    # 根据user_id查询数据库
    try:
        user = User.query.filter_by(id=user_id).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="获取用户信息查询异常")
    if not user:
        return jsonify(errno=RET.NODATA, errmsg="无效操作")
    # 返回正确结果
    return jsonify(errno=RET.OK, errmsg="ok", data=user.to_dict())


@api.route('/user/name', methods=['PUT'])
@login_required
def change_user_profile():
    # 获取参数request.get_json()
    user_id = g.user_id
    user_data = request.get_json()
    # 检查参数
    if not user_data:
        return jsonify(errno=RET.PARAMERR, errmsg="参数缺失")
    # 获取详细json的name
    name = user_data.get("name")
    if not name:
        return jsonify(errno=RET.PARAMERR, errmsg="json字典为空")
    # 修改name属性 ,查询数据库
    try:
        User.query.filter_by(id=user_id).update({'name': name})
        # 手动提交数据
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        # 回滚
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存修改用户信息失败")
    # *************************** 更新session用户数据*************************************************
    session['name'] = name
    # 返回修改响应结果
    return jsonify(errno=RET.OK, errmsg="保存修改用户信息ok!", data={"name": name})


@api.route('/user/avatar', methods=['POST'])
@login_required
def set_user_avatar():
    """用户头像上传"""
    # 获取用户身份,获取用户id
    user_id = g.user_id  # g对象
    # 获取图片文件
    avatar = request.files.get('avatar')
    # 检查参数
    if not avatar:
        return jsonify(errno=RET.PARAMERR, errmsg="用户未上传图片")
    # 读取图片2进制数据
    avatar_data = avatar.read()
    # 使用七牛云上传用户头像
    try:
        image_name = storage(avatar_data)
        print(u"七牛返回的图片名称:%s" % image_name)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="七牛上传失败!!")
    # 保存图片名称到mysql方便拼接地址
    try:
        User.query.filter_by(id=user_id).update({"avatar_url": image_name})
        # 需要手动提交数据
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存用户头像到mysql失败!!")
    # 拼接七牛图片的url路径
    full_image_url = constants.QINIU_DOMIN_PREFIX + image_name
    # 返回七牛图片结果
    return jsonify(errno=RET.OK, errmsg="ok!!", data={"avatar_url": full_image_url})


@api.route('/user/auth', methods=['POST'])
@login_required
def set_user_auth():
    """设置用户实名信息"""
    # 1 获取用户身份id
    user_id = g.user_id
    # 2.获取post请求参数
    user_data = request.get_json()
    # 3.校验参数
    if not user_data:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    real_name = user_data.get('real_name')
    id_card = user_data.get('id_card')
    if not all([real_name, id_card]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数缺失")
    # 4.查询数据库
    try:
        """判断实名认证只插入一次数据库"""
        User.query.filter_by(id=user_id, real_name=None, id_card=None).update(
            {"real_name": real_name, "id_card": id_card}
        )
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存用户实名信息失败")
    return jsonify(errno=RET.OK, errmsg="OK!!!")


@api.route("/user/auth", methods=["GET"])
@login_required
def get_user_auth():
    """获取用户实名认证信息"""
    # 获取用户user_id 查询用户实名信息
    user_id = g.user_id
    try:
        user = User.query.get(user_id)
        # User.query.filter_by(id=user_id).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询用户实名信息失败!!")
    # 判断校验查询结果
    if not user:
        return jsonify(errno=RET.NODATA, errmsg="无效操作")
    # 返回查询结果
    return jsonify(errno=RET.OK, errmsg="查询用户实名信息ok", data=user.auth_to_dict())
