# -*- coding:utf-8 -*-
from ihome import create_app, db  # 导包的时候会执行__init__.py里面的代码所以会有create_app
from flask import session

from flask_script import Manager
# 导入数据库迁移所用的类，命令类
from flask_migrate import Migrate, MigrateCommand
# ************************************************************************************
# 迁移一定要导入该类
from ihome import models

app = create_app('development')

# 迁移第一步
manager = Manager(app)
# 迁移第二步
migrate = Migrate(app, db)  # migrate 对象可以不定义
# 迁移第三部 添加到命令行
manager.add_command('db', MigrateCommand)


@app.route('/index')
def index():
    session['python24'] = '666'
    return 'hello word'


if __name__ == '__main__':
    print(app.url_map)
    # app.run()
    manager.run()

"""123
dawd
不会包括localhost
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' IDENTIFIED BY '123456' WITH GRANT OPTION;

manger就是启动文件
import os,base64
ret = os.urandom(10) 随机生成10个字节的字符串
base64.b64encode(ret)

安装mysqlclient出问题

    centos 7：
        yum install python-devel mariadb-devel -y

    ubuntu：
        sudo apt-get install libmysqlclient-dev

    然后：
        pip install mysqlclient


"""

""" python xxx.py runserver --help
optional arguments:
  -?, --help            show this help message and exit
  -h HOST, --host HOST
  -p PORT, --port PORT
  --threaded
  --processes PROCESSES
  --passthrough-errors
  -d, --debug           enable the Werkzeug debugger (DO NOT use in production
                        code)
  -D, --no-debug        disable the Werkzeug debugger
  -r, --reload          monitor Python files for changes (not 100{'const':
                        True, 'help': 'monitor Python files for changes (not
                        100% safe for production use)', 'option_strings':
                        ['-r', '--reload'], 'dest': 'use_reloader',
                        'required': False, 'nargs': 0, 'choices': None,
                        'default': None, 'prog': '_3session__json.py
                        runserver', 'container': <argparse._ArgumentGroup
                        object at 0x7f33bc8d5d50>, 'type': None, 'metavar':
                        None}afe for production use)
  -R, --no-reload       do not monitor Python files for changes
"""


"""
python _5db_select.py db init 第一次创建一次即可
python _5db_select.py db migrate -m 'init_tables_pxd注释注解' -m 可写可不写  
python _5db_select.py db upgrade
python _5db_select.py db history 查看历史迁移版本号码,根据guid版本号回退
python _5db_select.py db downgrade 4fc5046cb8c6 # 迁移回退直接会修改数据库 不建议回退
"""
