# -*- coding: utf-8 -*-

import logging

from qiniu import Auth, put_data


# 需要填写你的 Access Key 和 Secret Key  需要改
access_key = 'EBKfY_X7pDrvM3TAoVFlWQFqRb29j48TCCxec0xF'
secret_key = 'trgmtdMlc4mTx7EwWrpsJkRw67FTSvgyLnY5Ig9E'

# 要上传的空间 需要改
bucket_name = 'minicat'



def storage(data):
    """七牛云存储上传文件接口"""
    if not data:
        return None
    try:
        # 构建鉴权对象
        q = Auth(access_key, secret_key)

        # 生成上传 Token，可以指定过期时间等
        token = q.upload_token(bucket_name)

        # 上传文件
        ret, info = put_data(token, None, data)

    except Exception as e:
        logging.error(e)
        raise e

    if info and info.status_code != 200:
        raise Exception("上传文件到七牛失败")

    # 返回七牛中保存的图片名，这个图片名也是访问七牛获取图片的路径
    return ret["key"]


if __name__ == '__main__':
    file_name = raw_input("输入上传的文件")
    with open(file_name, "rb") as f:
        storage(f.read())

