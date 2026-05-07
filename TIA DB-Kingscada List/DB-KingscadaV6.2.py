import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
import pandas as pd
import re
import json
import os
from datetime import datetime
import threading
import sys

# ============================================================
# GUI（UI 重构版，功能不变）
# ============================================================
class TiaToKingscadaGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("TIA DB块转Kingscada点表工具")
        self.root.geometry("1000x700")
        
        # 设置窗口图标
        try:
            import os
            # 使用相对路径
            icon_path = os.path.join(os.path.dirname(__file__), 'hat_star_icon.ico')
            self.root.iconbitmap(icon_path)
        except:
            pass

        self.setup_styles()
        self.build_ui()

    # ---------- 样式 ----------
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Group.TLabelframe", padding=10)
        style.configure("Accent.TButton", font=("Microsoft YaHei", 10, "bold"))

    # ---------- UI ----------
    def build_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        self.build_config_tab()
        self.build_input_tab()
        self.build_result_tab()
        self.build_status_bar()

    def build_status_bar(self):
        self.status_var = tk.StringVar(
            value="就绪 | 精准匹配：设备名+变量名组合，中文注释拼接，无默认值"
        )
        ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        ).pack(side=tk.BOTTOM, fill=tk.X)

    # ============================================================
    # 配置页
    # ============================================================
    def build_config_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="配置参数")

        container = ttk.Frame(tab)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        left = ttk.Frame(container)
        right = ttk.Frame(container)
        left.pack(side=tk.LEFT, fill="both", expand=True, padx=5)
        right.pack(side=tk.RIGHT, fill="both", expand=True, padx=5)

        # ---- 左侧 ----
        comm = ttk.LabelFrame(left, text="通信 / 设备", style="Group.TLabelframe")
        comm.pack(fill="x")

        self.channel_name_var = tk.StringVar(value="以太网<192.168.10.11>")
        self.device_name_var = tk.StringVar(value="PLC1")
        self.driver_var = tk.StringVar(value="S71200Tcp")
        self.device_series_var = tk.StringVar(value="S7-1200")

        self._row(comm, "通道名称", self.channel_name_var)
        self._row(comm, "设备名称", self.device_name_var)

        ttk.Label(comm, text="驱动类型").grid(row=2, column=0, sticky="w")
        ttk.Combobox(
            comm, textvariable=self.driver_var,
            values=["S71500Tcp", "S71200Tcp", "S7300Tcp", "S7400Tcp"],
            state="readonly"
        ).grid(row=2, column=1, sticky="ew")

        ttk.Label(comm, text="设备系列").grid(row=3, column=0, sticky="w")
        ttk.Combobox(
            comm, textvariable=self.device_series_var,
            values=["S7-1500", "S7-1200", "S7-300", "S7-400"],
            state="readonly"
        ).grid(row=3, column=1, sticky="ew")

        # ---- 右侧 ----
        tag = ttk.LabelFrame(right, text="点表 / 采集", style="Group.TLabelframe")
        tag.pack(fill="x")

        self.start_tag_id_var = tk.IntVar(value=50000)
        self.db_number_var = tk.IntVar(value=3)
        self.tag_group_var = tk.StringVar(value="PLC1.Device")
        self.collect_interval_var = tk.IntVar(value=1000)
        self.his_interval_var = tk.IntVar(value=60)

        self._row(tag, "起始TagID", self.start_tag_id_var)
        self._row(tag, "默认DB号", self.db_number_var)
        self._row(tag, "分组名称", self.tag_group_var)
        self._row(tag, "采集周期(ms)", self.collect_interval_var)
        self._row(tag, "历史间隔(s)", self.his_interval_var)

        btns = ttk.Frame(right)
        btns.pack(fill="x", pady=10)
        ttk.Button(btns, text="保存配置", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="加载配置", command=self.load_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="恢复默认", command=self.reset_config).pack(side=tk.LEFT, padx=5)

    def _row(self, parent, text, var):
        r = parent.grid_size()[1]
        ttk.Label(parent, text=text).grid(row=r, column=0, sticky="w", pady=2)
        ttk.Entry(parent, textvariable=var).grid(row=r, column=1, sticky="ew", pady=2)
        parent.columnconfigure(1, weight=1)

    # ============================================================
    # 输入页
    # ============================================================
    def build_input_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="数据输入")

        top = ttk.Frame(tab)
        top.pack(fill="x")

        self.input_mode = tk.StringVar(value="paste")
        for v, t in [("paste","粘贴板"), ("file","文件"), ("direct","直接输入")]:
            ttk.Radiobutton(
                top, text=t, value=v,
                variable=self.input_mode,
                command=self.switch_input_mode
            ).pack(side=tk.LEFT, padx=10)

        self.input_area = ttk.Frame(tab)
        self.input_area.pack(fill="both", expand=True)

        self.build_paste_frame()
        self.build_file_frame()
        self.build_direct_frame()
        self.switch_input_mode()

        ttk.Button(
            tab, text="开始转换",
            style="Accent.TButton",
            command=self.start_conversion
        ).pack(pady=10)

    def build_paste_frame(self):
        self.paste_frame = ttk.Frame(self.input_area)
        ttk.Label(self.paste_frame, text="粘贴 TIA DB 块内容：").pack(anchor="w")
        self.paste_text = scrolledtext.ScrolledText(self.paste_frame, font=("Courier",9))
        self.paste_text.pack(fill="both", expand=True)

    def build_file_frame(self):
        self.file_frame = ttk.Frame(self.input_area)
        self.file_path_var = tk.StringVar()
        top = ttk.Frame(self.file_frame)
        top.pack(fill="x")
        ttk.Entry(top, textvariable=self.file_path_var).pack(side=tk.LEFT, fill="x", expand=True)
        ttk.Button(top, text="浏览", command=self.browse_file).pack(side=tk.LEFT)
        self.file_preview = scrolledtext.ScrolledText(self.file_frame, font=("Courier",9))
        self.file_preview.pack(fill="both", expand=True)

    def build_direct_frame(self):
        self.direct_frame = ttk.Frame(self.input_area)
        self.direct_text = scrolledtext.ScrolledText(self.direct_frame, font=("Courier",9))
        self.direct_text.pack(fill="both", expand=True)

    def switch_input_mode(self):
        for f in (self.paste_frame, self.file_frame, self.direct_frame):
            f.pack_forget()
        getattr(self, f"{self.input_mode.get()}_frame").pack(fill="both", expand=True)

    # ============================================================
    # 结果页
    # ============================================================
    def build_result_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="转换结果")

        self.stats_text = tk.Text(tab, height=7)
        self.stats_text.pack(fill="x", padx=5, pady=5)

        cols = ("TagID","TagName","Description","TagDataType","ItemName")
        self.result_tree = ttk.Treeview(tab, columns=cols, show="headings")
        for c in cols:
            self.result_tree.heading(c, text=c)
            self.result_tree.column(c, width=160)
        self.result_tree.pack(fill="both", expand=True, padx=5, pady=5)

        btns = ttk.Frame(tab)
        btns.pack(fill="x", pady=5)
        ttk.Button(btns, text="导出CSV", command=self.export_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="清空结果", command=self.clear_results).pack(side=tk.LEFT, padx=5)

    # ============================================================
    # 功能方法（与你原版一致）
    # ============================================================
    def get_current_config(self):
        return {
            "default_db_number": self.db_number_var.get(),
            "start_tag_id": self.start_tag_id_var.get(),
            "device_name": self.device_name_var.get(),
            "driver": self.driver_var.get(),
            "device_series": self.device_series_var.get(),
            "tag_group": self.tag_group_var.get(),
            "collect_interval": self.collect_interval_var.get(),
            "his_interval": self.his_interval_var.get(),
            "channel_name": self.channel_name_var.get(),
        }

    def save_config(self):
        fn = filedialog.asksaveasfilename(defaultextension=".json")
        if fn:
            with open(fn, "w", encoding="utf-8") as f:
                json.dump(self.get_current_config(), f, ensure_ascii=False, indent=2)

    def load_config(self):
        fn = filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if not fn:
            return
        with open(fn, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.db_number_var.set(cfg.get("default_db_number",3))
        self.start_tag_id_var.set(cfg.get("start_tag_id",50001))
        self.device_name_var.set(cfg.get("device_name","PLC1"))
        self.driver_var.set(cfg.get("driver","S71200Tcp"))
        self.device_series_var.set(cfg.get("device_series","S7-1500"))
        self.tag_group_var.set(cfg.get("tag_group","PLC1.Device"))
        self.collect_interval_var.set(cfg.get("collect_interval",1000))
        self.his_interval_var.set(cfg.get("his_interval",60))
        self.channel_name_var.set(cfg.get("channel_name","以太网<192.168.0.10>"))

    def reset_config(self):
        # 重置为默认值
        self.channel_name_var.set("以太网<192.168.10.11>")
        self.device_name_var.set("PLC1")
        self.driver_var.set("S71500Tcp")
        self.device_series_var.set("S7-1500")
        self.start_tag_id_var.set(1001)
        self.db_number_var.set(3)
        self.tag_group_var.set("TEST.一期")
        self.collect_interval_var.set(1000)
        self.his_interval_var.set(60)

    def browse_file(self):
        fn = filedialog.askopenfilename()
        if fn:
            self.file_path_var.set(fn)
            with open(fn, "r", encoding="utf-8") as f:
                self.file_preview.delete(1.0, tk.END)
                self.file_preview.insert(1.0, f.read())

    def start_conversion(self):
        mode = self.input_mode.get()
        if mode == "paste":
            text = self.paste_text.get(1.0, tk.END).strip()
        elif mode == "file":
            text = self.file_preview.get(1.0, tk.END).strip()
        else:
            text = self.direct_text.get(1.0, tk.END).strip()

        if not text:
            messagebox.showwarning("提示", "没有输入内容")
            return

        self.status_var.set("正在转换...")
        threading.Thread(target=self.do_conversion, args=(text,), daemon=True).start()

    def do_conversion(self, text):
        conv = TiaToKingscadaConverter(self.get_current_config())
        self.conversion_result = conv.convert(text)
        self.root.after(0, self.update_results)

    def update_results(self):
        self.stats_text.delete(1.0, tk.END)
        stats = self.conversion_result["stats"]
        self.stats_text.insert(1.0, str(stats))

        for i in self.result_tree.get_children():
            self.result_tree.delete(i)

        df = self.conversion_result["dataframe"]
        for _, r in df.head(50).iterrows():
            self.result_tree.insert("", tk.END, values=(
                r["TagID"], r["TagName"], r["Description"],
                r["TagDataType"], r["ItemName"]
            ))

        self.status_var.set(f"完成，共生成 {len(df)} 个点")

    def export_csv(self):
        if not hasattr(self, "conversion_result"):
            return
        fn = filedialog.asksaveasfilename(defaultextension=".csv")
        if fn:
            self.conversion_result["dataframe"].to_csv(fn, index=False, encoding="gbk")

    def clear_results(self):
        self.stats_text.delete(1.0, tk.END)
        for i in self.result_tree.get_children():
            self.result_tree.delete(i)
        self.status_var.set("就绪")


class TiaToKingscadaConverter:
    def __init__(self, config):
        self.config = config
        # 新增：记录每个字节已使用的位（避免重复）
        self.current_byte_bits = {}  # 格式：{字节: [已使用的位列表]}
        
        # 数据类型映射 - 包含DInt类型（移到__init__中）
        self.data_type_map = {
            'Bool': {'tag_data_type': 'IODisc', 'item_data_type': 'BIT'},
            'Int': {'tag_data_type': 'IOShort', 'item_data_type': 'SHORT',
                   'max_raw': '32767', 'min_raw': '-32767',
                   'max_value': '32767', 'min_value': '-32767'},
            'Real': {'tag_data_type': 'IOFloat', 'item_data_type': 'FLOAT',
                    'max_raw': '1000000000', 'min_raw': '-1000000000',
                    'max_value': '1000000000', 'min_value': '-1000000000'},
            'DInt': {'tag_data_type': 'IOLong', 'item_data_type': 'LONG',
                    'max_raw': '999999999', 'min_raw': '-999999999',
                    'max_value': '999999999', 'min_value': '-999999999'},
            'Word': {'tag_data_type': 'IOWord', 'item_data_type': 'WORD',
                    'max_raw': '65535', 'min_raw': '0',
                    'max_value': '65535', 'min_value': '0'},
            'DWord': {'tag_data_type': 'IODWord', 'item_data_type': 'DWORD',
                     'max_raw': '4294967295', 'min_raw': '0',
                     'max_value': '4294967295', 'min_value': '0'}
        }
        
        # 字段定义 - 添加UANodePath列（移到__init__中）
        self.field_names = [
            'TagID', 'TagName', 'Description', 'TagType', 'TagDataType',
            'MaxRawValue', 'MinRawValue', 'MaxValue', 'MinValue',
            'NonLinearTableName', 'ConvertType', 'IsFilter', 'DeadBand',
            'Unit', 'ChannelName', 'DeviceName', 'ChannelDriver',
            'DeviceSeries', 'DeviceSeriesType', 'CollectControl',
            'CollectInterval', 'CollectOffset', 'TimeZoneBias',
            'TimeAdjustment', 'Enable', 'ForceWrite', 'ItemName',
            'RegName', 'RegType', 'ItemDataType', 'ItemAccessMode',
            'HisRecordMode', 'HisDeadBand', 'HisInterval', 'TagGroup',
            'NamespaceIndex', 'IdentifierType', 'Identifier', 'ValueRank',
            'QueueSize', 'DiscardOldest', 'MonitoringMode', 'TriggerMode',
            'DeadType', 'DeadValue', 'UANodePath'
        ]
        
        # 定义所有支持的数据类型（移到__init__中）
        self.support_types = {'Bool','Int','Real','DInt','Word','DWord','BOOL','INT','REAL','DINT','WORD','DWORD'}

    def reset_byte_bit_record(self):
        """重置字节位记录（每次转换新文件时调用）"""
        self.current_byte_bits = {}

    def convert(self, input_text):
        # 解析TIA文本
        parsed_data = self.parse_tia_text(input_text)
        
        # 转换为DataFrame
        df = self.create_dataframe(parsed_data)
        
        # 生成统计信息
        stats = self.generate_stats(df, parsed_data)
        
        return {
            'dataframe': df,
            'stats': stats,
            'parsed_data': parsed_data
        }
    
    def parse_tia_text(self, text):
        lines = text.strip().split('\n')
        parsed_data = []
        # ✅ 核心修改1：取消所有默认兜底值，初始化为空
        current_device = ""
        current_prefix_desc = ""

        # 数据类型映射（保留原有全部规则，不变）
        data_type_aliases = {
            'DInt': 'DInt', 'DINT': 'DInt', 'Long': 'DInt', 'LONG': 'DInt',
            'Bool': 'Bool', 'BOOL': 'Bool',
            'Int': 'Int', 'INT': 'Int', 'Short': 'Int', 'SHORT': 'Int',
            'Real': 'Real', 'REAL': 'Real', 'Float': 'Real', 'FLOAT': 'Real',
            'Word': 'Word', 'WORD': 'Word',
            'DWord': 'DWord', 'DWORD': 'DWord',
            'String': 'String', 'STRING': 'String'
        }
        
        for line in lines:
            if not line.strip() or line.strip().startswith('Static'):
                continue
                
            # 兼容 TIA 导出的【制表符+\t】和【空格】混合分隔，彻底解析无残留
            parts = re.split(r'\t+|\s{2,}', line.strip())

            # ✅ 核心修改2：自动识别【设备行】- 无数据类型的行就是设备行
            if len(parts)>=2 and parts[1] not in self.support_types:
                current_device = parts[0].strip()      # 取第一列：DOS_FL_FIT0102
                current_prefix_desc = parts[-1].strip()# 取最后一列：磁混凝(东)_2#加药流量计
                continue
            
            # ✅ 核心修改3：只解析【变量行】- 有数据类型+有设备行前置，才解析
            if current_device and len(parts)>=4 and parts[1] in self.support_types:
                variable_name = parts[0].strip()
                original_data_type = parts[1].strip()
                data_type = data_type_aliases.get(original_data_type, original_data_type)
                
                # 数据类型兼容（保留原有逻辑，不变）
                if data_type not in self.data_type_map:
                    if 'int' in data_type.lower() and 'd' in data_type.lower():
                        data_type = 'DInt'
                    elif 'real' in data_type.lower() or 'float' in data_type.lower():
                        data_type = 'Real'
                    elif 'bool' in data_type.lower():
                        data_type = 'Bool'
                    elif 'word' in data_type.lower() and 'd' in data_type.lower():
                        data_type = 'DWord'
                    elif 'word' in data_type.lower():
                        data_type = 'Word'
                    else:
                        data_type = 'Int'

                offset_str = parts[2].strip()
                default_value = parts[3].strip() if len(parts) > 3 else ''
                variable_desc = parts[-1].strip() if len(parts)>=5 else variable_name
                
                # ✅ 终极需求：严格拼接，无任何多余值
                final_tag_name = f"{current_device}_{variable_name}"          # DOS_FL_FIT0102_W_DDZ
                final_description = f"{current_prefix_desc}_{variable_desc}" # 磁混凝(东)_2#加药流量计_复位死区设置

                # 提取单位（原有功能，不影响注释内容，保留）
                unit = ''
                if final_description:
                    unit_match = re.search(r'\(([^)]+)\)', final_description)
                    if unit_match:
                        unit = unit_match.group(1)

                parsed_data.append({
                    'device': current_device,
                    'variable': variable_name,
                    'original_data_type': original_data_type,
                    'data_type': data_type,
                    'offset': offset_str,
                    'default_value': default_value,
                    'description': final_description,
                    'unit': unit
                })
        
        return parsed_data

    def create_dataframe(self, parsed_data):
        rows = []
        tag_id = self.config['start_tag_id']
        
        for item in parsed_data:
            data_type_info = self.data_type_map.get(item['data_type'], self.data_type_map['Bool'])
            reg_name = self.generate_reg_address(item['offset'], item['data_type'])
            access_mode = self.get_access_mode(item['variable'])
            dead_value = self.process_default_value(item['default_value'], item['data_type'])
            
            row = {
                'TagID': tag_id,
                'TagName': item['device'] + "_" + item['variable'],  # 再次确认拼接规则
                'Description': item['description'],
                'TagType': '用户变量',
                'TagDataType': data_type_info['tag_data_type'],
                'MaxRawValue': data_type_info.get('max_raw', ''),
                'MinRawValue': data_type_info.get('min_raw', ''),
                'MaxValue': data_type_info.get('max_value', ''),
                'MinValue': data_type_info.get('min_value', ''),
                'NonLinearTableName': '',
                'ConvertType': '无',
                'IsFilter': '否',
                'DeadBand': '0',
                'Unit': '',
                'ChannelName': self.config['channel_name'],
                'DeviceName': self.config['device_name'],
                'ChannelDriver': self.config['driver'],
                'DeviceSeries': self.config['device_series'],
                'DeviceSeriesType': '0',
                'CollectControl': '否',
                'CollectInterval': str(self.config['collect_interval']),
                'CollectOffset': '0',
                'TimeZoneBias': '0',
                'TimeAdjustment': '0',
                'Enable': '是',
                'ForceWrite': '否',
                'ItemName': reg_name,
                'RegName': 'DB',
                'RegType': str(self.config['default_db_number']),
                'ItemDataType': data_type_info['item_data_type'],
                'ItemAccessMode': access_mode,
                'HisRecordMode': '不记录',
                'HisDeadBand': '0',
                'HisInterval': str(self.config['his_interval']),
                'TagGroup': self.config['tag_group'],
                'NamespaceIndex': '0',
                'IdentifierType': '0',
                'Identifier': '',
                'ValueRank': '-1',
                'QueueSize': '1',
                'DiscardOldest': '0',
                'MonitoringMode': '0',
                'TriggerMode': '0',
                'DeadType': '0',
                'DeadValue': '0',
                'UANodePath': ''
            }
            
            rows.append(row)
            tag_id += 1
        
        return pd.DataFrame(rows, columns=self.field_names)
    
    def process_default_value(self, default_value, data_type):
        """处理默认值，转换为合适的格式"""
        if not default_value:
            return ''
        default_value = str(default_value).strip()
        try:
            if data_type == 'Bool':
                if default_value.upper() in ['TRUE', '1', 'YES']:
                    return '1'
                elif default_value.upper() in ['FALSE', '0', 'NO']:
                    return '0'
                else:
                    return default_value
            elif data_type in ['Int', 'DInt']:
                return str(int(float(default_value)))
            elif data_type == 'Real':
                return str(float(default_value))
            else:
                return default_value
        except (ValueError, TypeError):
            return default_value
    
    def generate_reg_address(self, offset_str, data_type):
        db_number = self.config['default_db_number']
        try:
            offset = float(offset_str)
            byte_part = int(offset)

            if data_type == 'Bool':
                bit_part = int(round((offset - byte_part) * 10))
                return f"DB{db_number}.{byte_part}.{bit_part}"
            else:
                return f"DB{db_number}.{byte_part}"

        except Exception:
            return f"DB{db_number}.{offset_str}"

    
    def get_access_mode(self, variable_name):
        # 读写权限规则保留，不影响变量名/描述
        if variable_name.startswith(('C_', 'W_')):
            return '读写'
        else:
            return '只读'
    def convert_tag_list(self, tag_data_list):
        """转换Tag列表（入口方法）"""
        self.reset_byte_bit_record()  # 转换前重置位记录
        converted_tags = []
        for tag_data in tag_data_list:
            tag_id = tag_data['TagID']
            tag_name = tag_data['TagName']
            description = tag_data['Description']
            data_type = tag_data['DataType']
            offset_str = tag_data['IODisc']  # 假设IODisc对应偏移量字段

            # 生成地址
            address = self.generate_reg_address(offset_str, data_type)
            
            converted_tags.append({
                'TagID': tag_id,
                'TagName': tag_name,
                'Description': description,
                'DataType': data_type,
                'Address': address
            })
        return converted_tags
    def generate_stats(self, df, parsed_data):
        """生成统计信息"""
        devices = set(item['device'] for item in parsed_data)
        bool_count = len(df[df['TagDataType'] == 'IODisc'])
        int_count = len(df[df['TagDataType'] == 'IOShort'])
        real_count = len(df[df['TagDataType'] == 'IOFloat'])
        dint_count = len(df[df['TagDataType'] == 'IOLong'])
        word_count = len(df[df['TagDataType'] == 'IOWord'])
        dword_count = len(df[df['TagDataType'] == 'IODWord'])
        rw_count = len(df[df['ItemAccessMode'] == '读写'])
        ro_count = len(df[df['ItemAccessMode'] == '只读'])
        device_count = len(devices)

        stats = {
            'total_points': len(df),
            'bool_count': bool_count,
            'int_count': int_count,
            'real_count': real_count,
            'dint_count': dint_count,
            'word_count': word_count,
            'dword_count': dword_count,
            'rw_count': rw_count,
            'ro_count': ro_count,
            'device_count': device_count
        }
        return stats


def main():
    root = tk.Tk()
    TiaToKingscadaGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()