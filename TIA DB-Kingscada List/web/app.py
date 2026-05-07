from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
import pandas as pd
import re
import json
import os
import sys
from datetime import datetime
import tempfile

# 添加父目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入核心转换功能
from src.core.converter import TiaToKingscadaConverter

app = Flask(__name__)

# 配置密钥，用于会话管理
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')

# 配置模板目录 - 使用绝对路径
app.root_path = os.path.dirname(os.path.abspath(__file__))
app.template_folder = os.path.join(app.root_path, 'templates')
print(f"App root path: {app.root_path}")
print(f"Template folder: {app.template_folder}")

# 用户数据文件路径
USERS_FILE = os.path.join(app.root_path, 'data', 'users.json')

# 临时文件存储
TEMP_DIR = tempfile.gettempdir()
current_result = None

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def check_login():
    return 'username' in session

@app.route('/')
def index():
    if not check_login():
        return redirect(url_for('login'))
    
    current_date = datetime.now().strftime("%Y年%m月%d日")
    # 打印模板文件路径，用于调试
    template_path = os.path.join(app.template_folder, 'index.html')
    print(f"Template path: {template_path}")
    print(f"Template exists: {os.path.exists(template_path)}")
    return render_template('index.html', current_date=current_date)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        users = load_users()
        for user in users:
            if user['username'] == username and user['password'] == password:
                session['username'] = username
                return jsonify({'success': True})
        
        return jsonify({'success': False, 'message': '用户名或密码错误'})
    
    if check_login():
        return redirect(url_for('index'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload_file():
    if not check_login():
        return jsonify({'success': False, 'error': '请先登录'})
        
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'})
    
    if file:
        # 读取文件内容
        content = file.read().decode('utf-8')
        return jsonify({'success': True, 'content': content})

@app.route('/convert', methods=['POST'])
def convert():
    if not check_login():
        return jsonify({'success': False, 'error': '请先登录'})
        
    global current_result
    
    # 获取文件内容
    file_content = request.form.get('file_content')
    if not file_content:
        return jsonify({'success': False, 'error': 'No file content'})
    
    # 获取配置参数
    conversion_config = {
        "default_db_number": int(request.form.get('db_number', 3)),
        "start_tag_id": int(request.form.get('start_tag_id', 50000)),
        "device_name": request.form.get('device_name', 'PLC1'),
        "driver": request.form.get('driver', 'S71200Tcp'),
        "device_series": request.form.get('device_series', 'S7-1200'),
        "tag_group": request.form.get('tag_group', 'PLC1.Device'),
        "collect_interval": int(request.form.get('collect_interval', 1000)),
        "his_interval": int(request.form.get('his_interval', 60)),
        "channel_name": request.form.get('channel_name', '以太网<192.168.10.11>'),
    }
    
    try:
        # 执行转换
        conv = TiaToKingscadaConverter(conversion_config)
        result = conv.convert(file_content)
        
        # 保存结果
        current_result = result
        
        # 准备返回数据
        data = []
        for _, row in result['dataframe'].iterrows():
            data.append({
                'TagID': row['TagID'],
                'TagName': row['TagName'],
                'Description': row['Description'],
                'TagDataType': row['TagDataType'],
                'ItemName': row['ItemName']
            })
        
        # 打印统计信息，用于调试
        print("转换结果统计:", result['stats'])
        print("数据框长度:", len(result['dataframe']))
        print("返回数据长度:", len(data))
        
        return jsonify({
            'success': True,
            'stats': result['stats'],
            'data': data
        })
    except Exception as e:
        print("转换错误:", str(e))
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download')
def download():
    if not check_login():
        return jsonify({'success': False, 'error': '请先登录'})
        
    global current_result
    
    if not current_result:
        return jsonify({'success': False, 'error': 'No conversion result'})
    
    # 创建临时CSV文件
    temp_file = os.path.join(TEMP_DIR, f"conversion_result_{datetime.now().timestamp()}.csv")
    current_result['dataframe'].to_csv(temp_file, index=False, encoding='gbk')
    
    # 发送文件
    return send_file(temp_file, as_attachment=True, download_name='conversion_result.csv')



if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)
