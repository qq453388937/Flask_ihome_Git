# -*- coding:utf-8 -*-
from . import api  # 导入蓝图对象
from flask import jsonify, make_response, request, session, g, current_app  # session时使用
# 导入状态码
from ihome.utils.response_code import RET
# 导入redis实例
from ihome import redis_client
# 导入常量文件
from ihome import constants
# 导入模型类
from ihome.models import *
# 导入数据库db,redis实例
from ihome import db, redis_client
# 导入登陆验证装饰器
from ihome.utils.commons import login_required
# 导入七牛云
from ihome.utils.image_storage import storage
# 导入正则模块
import re
import json


@api.route("/areas", methods=["GET"])
def get_areas_info():
    """获取城区信息
    redis缓存接口
    """
    # 尝试从redis中获取城区信息
    try:
        areas = redis_client.get("areas_info_flask")  # 下面需要滞空的原因是这里的redis_client.get可能会异常使左面的areas不存在
    except Exception as e:
        current_app.logger.error(e)
        areas = None  # 这里滞空的原因是redis_client.get 右边可能会发生异常不会返回给左边,所以area变量不存在
    if areas:
        current_app.logger.info("hit redis area info")
        # redis中已经是key_value字符串了,直接返回
        return '{"errno":' + RET.OK + ',"errmsg":"ok","data":%s}' % areas
    # 判断获取结果,有数据返回,没有数据查询mysql
    try:
        areas = Area.query.all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询错误!!!")
    if not areas:
        return jsonify(errno=RET.NODATA, errmsg="无城区数据")
    # 临时容器,组织数据使用
    areas_list = []  # 列表嵌套字典[{},{},{}] ==> js中数组嵌套对象[{},{},{}]
    for area in areas:
        # 不能把一个对象直接转换称json
        areas_list.append(area.to_dict())  # 基于字典的键值对才能dumps,不能是对象
        # # 本质就是下面解释
        # areas_list.append({
        #     "aid": area.id,
        #     "aname": area.name
        # })
    # 把城区信息转成json字符串存到redis
    area_json = json.dumps(areas_list)  # 本质就是加了引号 json.loads本质就是去除双引号转换为python的类型
    try:
        redis_client.setex("areas_info_flask", constants.AREA_INFO_REDIS_EXPIRES, area_json)
    except Exception as e:
        current_app.logger.error(e)  # 不能够return
    # 返回对应响应结果
    # redis中已经是key_value字符串了,直接返回
    resp = '{"errno":' + RET.OK + ',"errmsg":"ok","data":%s}' % area_json
    return resp


@api.route('/houses', methods=["POST"])
@login_required
def new_house_info():
    """发布房屋信息
    flushall 清除所有redis数据
    """
    # 获取user_id  g对象
    user_id = g.user_id
    # 获取get_json,判断获取结果
    json_dict = request.get_json()
    if not json_dict:
        return jsonify(errno=RET.PARAMERR, errmsg="参数有错误")
    # 获取参数
    title = json_dict.get("title")
    price = json_dict.get("price")
    area_id = json_dict.get("area_id")  # 城区id
    address = json_dict.get("address")  # 详细地址
    room_count = json_dict.get("room_count")  # 房屋数
    unit = json_dict.get("unit")  # 户型
    acreage = json_dict.get("acreage")
    capacity = json_dict.get("capacity")
    beds = json_dict.get("beds")
    deposit = json_dict.get("deposit")
    min_days = json_dict.get("min_days")
    max_days = json_dict.get("max_days")
    # 检查参数的完整性
    if not all(
            [title, price, area_id, address, room_count, unit, acreage, capacity, beds, deposit, min_days, max_days]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    try:
        price = int(float(price) * 100)
        deposit = int(float(deposit) * 100)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="价格处理错误")
    # # 构造模型对象 准备存储房屋基本信息
    house = House()
    house.user_id = user_id
    house.area_id = area_id
    house.title = title
    house.price = price
    house.address = address
    house.room_count = room_count
    house.unit = unit
    house.acreage = acreage
    house.capacity = capacity
    house.beds = beds
    house.deposit = deposit
    house.min_days = min_days
    house.max_days = max_days

    # ##################################### 测试
    # house = House()
    # house.user_id = 3
    # house.area_id = 5
    # house.title = "测试title"
    # house.price = 998
    # house.address = "修正大厦"
    # house.room_count = 12
    # house.unit = "测试"
    # house.acreage = 120
    # house.capacity = 3
    # house.beds = "炕"
    # house.deposit = 1000
    # house.min_days = 1
    # house.max_days = 0
    # facility = [1, 2, 3, 4]
    # ####################################### 测试

    # 判断配套设施是否存在?
    facility = json_dict.get("facility")
    if facility:
        try:
            in_facilities = Facility.query.filter(Facility.id.in_(facility)).all()  # in_
            # 多对多保存,数据存储在第三个表中 ,中间表
            house.facilities = in_facilities
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询in操作失败")
    try:
        db.session.add(house)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="添加房屋失败")
    # 最后返回houseid
    else:
        # commit后 houseid 会自动存到house对象当中
        return jsonify(errno=RET.OK, errmsg="添加房屋ok", data={"house_id": house.id})


@api.route("/houses/<int:house_id>/images", methods=["POST"])
@login_required
def save_house_image(house_id):
    # 获取图片文件参数
    house_image_file = request.files.get("house_image")  # 前端当中的表单名称
    # 检查图片文件的存在
    if not house_image_file:
        return jsonify(errno=RET.PARAMERR, errmsg="未上传图片,请上传文件!")
    # 根据house_id查询房屋是否存在?
    # 保存查询结果,校验
    try:
        house = House.query.get(house_id)
        # house = House.query.filter_by(id=house_id).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询房屋数据异常")
    if not house:
        return jsonify(errno=RET.NODATA, errmsg="房屋不存在无法存储图片")
    # 房屋存在读取图片数据
    house_image_data = house_image_file.read()  # 对比tornado[0]['body']
    # 存储到七牛云
    try:
        image_name = storage(house_image_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="上传图片失败")
    # 构造模型类对象,判断房屋默认图片是否设置
    house_image = HouseImage()
    house_image.house_id = house_id
    house_image.url = image_name  # 保存七牛的名称name
    db.session.add(house_image)  # 添加数据到数据库会话当中
    # 判断房屋主图片是否设置,如果没有设置则设置,有则跳过继续执行
    if not house.index_image_url:
        house.index_image_url = image_name
        # 临时添加房屋的默认图片
        db.session.add(house)
    # 存储导mysql,事务提交一次保存2条(仅仅是默认图片没有存时)
    try:
        db.session.commit()  # 不建议这样操作一次commit
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存房屋图片失败")
    else:
        # 拼接七牛图片的绝对路径
        juedui_image_url = constants.QINIU_DOMIN_PREFIX + image_name
        # 返回正确响应结果
        return jsonify(errno=RET.OK, errmsg="OK!!!!!", data={"url": juedui_image_url})


###########################################
@api.route('/user/houses', methods=['GET'])
@login_required
def get_user_houses():
    """获取用户的房源"""
    # 和获取用户身份
    user_id = g.user_id
    # 查询用户表
    try:
        user = User.query.filter_by(id=user_id).first()
        # 使用反向引用,获取用户的房屋信息
        user_houses = user.houses  # 一对多查询
    except Exception as e:
        current_app.logger.error(e)  # 记录日志信息
        return jsonify(errno=RET.DBERR, errmsg="查询用户或用户房屋出错")
    # 定义一个容器存储用户房屋
    temp_house = []
    # 遍历查询结果,调用模型类封装的查询方法
    if user_houses:
        for item in user_houses:
            # 调用了模型类当中的方法获取字典数据
            temp_house.append(item.to_basic_dict())
    # 返回结果 jsonify自带序列化,把穿进去的命名参数序列化,放入redis缓存的话手动的调用dumps
    return jsonify(errno=RET.OK, errmsg="ok", data={"houses": temp_house})  # 有数据或空列表存储用户房屋


@api.route("/houses/index", methods=["GET"])
def get_house_index():
    """项目首页幻灯片展示"""
    # 尝试读取redis缓存
    try:
        ret = redis_client.get("home_page_data")  # ｇｅｔ出错没有ｒｅｔ局部变量
    except Exception as e:
        current_app.logger.error(e)
        ret = None
        # 继续执行不能中断请求
    if ret:
        current_app.logger.info("hit redis house info ")
        return '{"errno":0,"errmsg":"OK","data":%s}' % ret
    # 判断查询结果是否有数据
    try:  # redis没有数据
        # 预订完成的该房屋的订单数 倒叙排序，订房最多的 5个＃
        houses = House.query.order_by(House.order_count.desc()).limit(
            constants.HOME_PAGE_MAX_HOUSES
        )
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询mysql房屋数据异常")

    # 留下访问reids数据的记录
    if not houses:
        return jsonify(errno=RET.NODATA, errmsg="mysql无房屋数据")
    # 定义容器
    house_list = []  # [{},{},{},{}]
    for house in houses:
        if not house.index_image_url:  # 没有图片的跳过
            continue
        house_list.append(house.to_basic_dict())  # 就是添加字典(对象)进去
    # 查询mysql数据库,默认按成交次数进行排序,分页
    houses_json = json.dumps(house_list)  # '[{},{},{},{}]'
    # redis 存
    try:
        redis_client.setex("home_page_data", constants.HOME_PAGE_DATA_REDIS_EXPIRES,
                           houses_json)
    except Exception as e:
        current_app.logger.error(e)
        # 这里保存redis出错也不能return让用户看到mysql查询出来的数据
        # return jsonify(errno=RET.NODATA, errmsg="无数据")
    # 带确认 必须是双引号
    return '{"errno":0,"errmsg":"OK","data":%s}' % houses_json  # '{"errno":0,"errmsg":"OK","data":'[{},{},{},{}]'}'


@api.route("/houses/<int:house_id>", methods=["GET"])
def get_house_detail(house_id):
    """获取房屋的详细数据"""
    # 获取用户的身份 从redis中获取
    user_id = session.get("user_id", -1)  # 类比login_required
    # -1提供预定入口
    if not house_id:
        return jsonify(errno=RET.PARAMERR, errmsg="参数不存在")
    # 尝试从redis中获取房屋详情数据,存储键为house_info_%s % house_id
    ret = None  # ret为局部变量
    try:
        ret = redis_client.get("house_info_%s" % house_id)
    except Exception as e:
        current_app.logger.error(e)
    # 判断查询结果
    if ret:
        current_app.logger.info("hit redis house detail info ")
        # 前段判断user_id 和house的id是相等的是房东本人,如果是房东本人把预定接口藏起来
        return '{"errno":0,"errmsg":"ok","data":{"user_id":%s,"house":%s}}' % (user_id, ret)
    # redis没有数据
    try:
        house = House.query.get(house_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询房屋mysql数据失败")
    # 判断查询结果
    if not house:
        return jsonify(errno=RET.NODATA, errmsg="mysql没有数据")
    try:
        house_data = house.to_full_dict()  # 因为to_full_dict() 里面查询数据库,所以需要异常处理
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询房屋详情失败")
    # json字符串
    house_json = json.dumps(house_data)
    # 添加到redis
    try:
        redis_client.setex("house_info_%s" % house_id, constants.HOME_PAGE_DATA_REDIS_EXPIRES, house_json)
    except Exception as e:
        current_app.logger.error(e)
    resp = '{"errno":0,"errmsg":"ok","data":{"user_id":%s,"house":%s}}' % (user_id, house_json)
    return resp


@api.route("/houses", methods=["GET"])
def get_houses_list_ai_jia():
    """
    area_id  ===> aid
    start_date_str ===> sd
    end_date_str  ===> ed
    sort_key   ===> sk  默认 "new"
    page ===>       p   默认 1
    皆为非必传
    """
    # 缓存 ===> 磁盘 =====> 缓存
    """
    redis hash
    redis_key="house_%s_%s_%s_%s"
    redis_client.hget(redis_key,page)
    """

    # datetime.datetime.strptime(start_datetime,"%Y-%m-%d")
    # 比较开始日期小于等于结束日期
    # 尝试从redis缓存获取信息,使用hash数据类型,如果有数据直接返回,没有数据查询mysql
    # redis_key = "house_%s_%s_%s_%s" % ()
    # 定义容器存储查询条件的容器
    # 用户选择的开始日期和结束日期比较已预定的订单的开始日期和结束日期,筛选不冲突的房屋
    # 分页 houses_page = houses.paginate(pageIndex,每页数据的条目,false)
    # house_list = houses_page.items 分页后的数据
    # total_page = house_page.pages 分页后的总页数
    # 定义容器,遍历分页后的数据 to_basic_dict()
    # 构造响应数据

    # 获取参数,区域信息,开始日期,结束日期,排序条件(默认new),页数(默认1)
    area_id = request.args.get("aid", "")
    start_date_str = request.args.get("sd", "")
    end_date_str = request.args.get("ed", "")
    sort_key = request.args.get("sk", "new")
    page = request.args.get("p", "1")
    import datetime
    # 对日期参数进行格式化
    try:  # 定义变量存储格式化后的日期
        start_date, end_date = None, None
        # 判断如果存在开始日期
        if start_date_str:
            start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        # 判断如果存在结束日期
        if end_date_str:
            end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        # 对格式化后的日期进行判断,要求用户选择的日期必须至少是哦一天
        if start_date_str and end_date_str:
            assert start_date <= end_date, "日期不合适"
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="日期不合适格式错误!")
    # 对页数进行格式化
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="page不是整数报错!")
    # 尝试读取redis数据库,获取房屋列表信息
    try:
        redis_key = "house_%s_%s_%s_%s" % (area_id, start_date_str, end_date_str, sort_key)
        ret = redis_client.hget(redis_key, page)  # 获取一页数据
    except Exception as e:
        current_app.logger.error(e)
        ret = None
        return jsonify(errno=RET.DATAERR, errmsg="redis报错!")
    if ret:
        current_app.logger.info("hit redis house list info ==============================")
        return ret
    # redis 没有查询mysql

    # 定义容器存储查询的过滤条件
    try:
        params_filter = []
        # 判断城区信息是否存在
        if area_id:
            params_filter.append(House.area_id == area_id)
        # 判断日期是否
        if start_date_str and end_date_str:
            conflict_orders = Order.query.filter(Order.begin_date <= end_date
                                                 , Order.end_date >= start_date).all()
            conflict_houses_id = [order.house_id for order in conflict_orders]
            if conflict_houses_id:
                params_filter.append(House.id.notin_(conflict_houses_id))

        # 如果用户选择开始日期
        elif start_date:
            conflict_orders = Order.query.filter(Order.end_date >= start_date).all()
            conflict_houses_id = [order.house_id for order in conflict_orders]
            if conflict_houses_id:
                params_filter.append(House.id.notin_(conflict_houses_id))
        elif end_date:
            conflict_orders = Order.query.filter(
                Order.begin_date <= end_date
            ).all()
            conflict_houses_id = [order.house_id for order in conflict_orders]
            if conflict_houses_id:
                params_filter.append(House.id.notin_(conflict_houses_id))
        # 排序
        # 成交次数进行排序
        if "booking" == sort_key:
            houses = House.query.filter(*params_filter).order_by(House.order_count.desc())
        elif "price-inc" == sort_key:
            houses = House.query.filter(*params_filter).order_by(House.price.asc())
        elif "price-des" == sort_key:
            houses = House.query.filter(*params_filter).order_by(House.price.desc())
        else:
            houses = House.query.filter(*params_filter).order_by(House.create_time.desc())
        # 分页
        # constants.HOUSE_LIST_PAGE_CAPACITY
        houses_page = houses.paginate(page, 2, False)
        # 获取分页后的房屋数据
        house_list = houses_page.items
        # 获取总页数
        total_page = houses_page.pages
        # 定义容器遍历分页后的房屋数据,调用模型类中的to_basic_dict()
        houses_dict_list = []
        for house in house_list:
            houses_dict_list.append(house.to_basic_dict())

    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询房屋列表数据信息失败!")
    # 构造缓存json数据
    resp = {
            "errno": 0, "errmsg": "ok",
            "data":
                {
                    "houses": houses_dict_list,
                    "totol_page": total_page,
                    "current_page": page
                }
            }
    resp_json = json.dumps(resp)
    # 判断用户请求的页数小于等于分页后的总页数,即用户请求的页数是有数据的

    if page <= total_page:
        redis_key = "houses_%s_%s_%s_%s" % (area_id, start_date_str, end_date_str, sort_key)
        pip = redis_client.pipeline()
        try:
            # 开启hi事务
            pip.multi()
            # 存储数据
            pip.hset(redis_key, page, resp_json)
            # 统一设置过期时间
            pip.expire(redis_key, constants.HOUSE_LIST_REDIS_EXPIRES)  # 7200
            # 执行事务
            pip.execute()
        except Exception as e:
            current_app.logger.error(e)
    import time
    # 返回结果
    return resp_json
