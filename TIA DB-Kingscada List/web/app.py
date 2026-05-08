from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
import pandas as pd
import re
import json
import os
import sys
from datetime import datetime
import tempfile
from openpyxl.styles import Font
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
app.static_folder = os.path.join(app.root_path, 'static')
print(f"App root path: {app.root_path}")
print(f"Template folder: {app.template_folder}")
print(f"Static folder: {app.static_folder}")

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
    current_user = session.get('username', '')
    # 打印模板文件路径，用于调试
    template_path = os.path.join(app.template_folder, 'index.html')
    print(f"Template path: {template_path}")
    print(f"Template exists: {os.path.exists(template_path)}")
    return render_template('index.html', current_date=current_date, current_user=current_user)

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

@app.route('/ico/<path:filename>')
def serve_ico(filename):
    return send_file(os.path.join(app.root_path, 'ico', filename))

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
        
        # 准备返回数据（只返回前端显示需要的列）
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
        print("数据框列数:", len(result['dataframe'].columns))
        print("数据框列名:", result['dataframe'].columns.tolist())
        
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
    
    # 获取格式参数
    export_format = request.args.get('format', 'csv').lower()
    filename = request.args.get('filename', 'conversion_result')
    
    try:
        if export_format == 'excel' or export_format == 'xlsx':
            # Excel格式（单Sheet）- 导出完整列
            temp_file = os.path.join(TEMP_DIR, f"{filename}_{datetime.now().timestamp()}.xlsx")
            current_result['dataframe'].to_excel(temp_file, index=False, engine='openpyxl')
            return send_file(temp_file, as_attachment=True, download_name=f'{filename}.xlsx')
        elif export_format == 'excel-multi':
            # Excel格式（多Sheet）- 按数据类型分Sheet
            conv = TiaToKingscadaConverter({
                'default_db_number': 3,
                'start_tag_id': 50000,
                'device_name': 'PLC1',
                'driver': 'S71200Tcp',
                'device_series': 'S7-1200',
                'tag_group': 'PLC1.Device',
                'collect_interval': 1000,
                'his_interval': 60,
                'channel_name': '以太网<192.168.10.11>'
            })
            sheets = conv.create_multi_sheet_dataframes(current_result['dataframe'])
            temp_file = os.path.join(TEMP_DIR, f"{filename}_{datetime.now().timestamp()}.xlsx")
            with pd.ExcelWriter(temp_file, engine='openpyxl') as writer:
                for sheet_name, df in sheets.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    # 获取工作表对象，将第一行字体设为非粗体
                    worksheet = writer.sheets[sheet_name]
                    for cell in worksheet[1]:   # 第一行所有单元格
                        cell.font = Font(bold=False)
                    for row in worksheet.iter_rows(min_row=1, max_row=1):
                        for cell in row:
                            cell.border = Border()  # 等同于无边框
            return send_file(temp_file, as_attachment=True, download_name=f'{filename}.xlsx')
        elif export_format == 'json':
            # JSON格式 - 导出完整数据
            temp_file = os.path.join(TEMP_DIR, f"{filename}_{datetime.now().timestamp()}.json")
            result_data = current_result['dataframe'].to_dict('records')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            return send_file(temp_file, as_attachment=True, download_name=f'{filename}.json')
        else:
            # 默认CSV格式 - 导出完整列
            temp_file = os.path.join(TEMP_DIR, f"{filename}_{datetime.now().timestamp()}.csv")
            current_result['dataframe'].to_csv(temp_file, index=False, encoding='gbk')
            return send_file(temp_file, as_attachment=True, download_name=f'{filename}.csv')
    except Exception as e:
        print("下载错误:", str(e))
        return jsonify({'success': False, 'error': str(e)})



if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)
