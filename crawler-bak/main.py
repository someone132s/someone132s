import os
import requests
import json
from bs4 import BeautifulSoup
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime
from pysm4 import encrypt_ecb
from dotenv import load_dotenv
import tempfile
import webbrowser
import base64

class MedicalDataCrawler:
    def __init__(self):
        load_dotenv()
        self.base_url = "http://example.com/medical-data"  # 需要替换为实际数据源
        self.engine = create_engine("sqlite:///./medical.db")
        self.session = requests.Session()
        
        # 登录配置
        self.username = os.getenv('USERNAME')
        self.password = os.getenv('PASSWORD')
        self.sm4_key = os.getenv('SM4_KEY')
        self.verifycode_url = os.getenv('VERIFYCODE_URL')
        self.login_url = os.getenv('LOGIN_URL')

    def encrypt_password(self, password):
        """使用SM4加密密码，并返回16进制的密文"""
        try:
            # 确保密钥是32字符的16进制字符串
            if not self.sm4_key or len(self.sm4_key) != 32:
                raise ValueError("SM4密钥必须是32字符的16进制字符串")
            
            # 将16进制密钥转换为16字节，再转换为latin1字符串
            key_bytes = bytes.fromhex(self.sm4_key)
            if len(key_bytes) != 16:
                raise ValueError("转换后的SM4密钥必须为16字节")
            key_str = key_bytes.decode('latin1')
            
            # 确保密码是字符串
            if not isinstance(password, str):
                raise ValueError("密码必须是字符串")
            
            # 调用库函数加密，库要求明文为字符串，密钥为latin1编码的字符串
            encrypted_base64 = encrypt_ecb(password, key_str)
            
            # 将base64字符串转换为bytes，再转换为16进制字符串输出
            cipher_bytes = base64.b64decode(encrypted_base64)
            cipher_hex = cipher_bytes.hex()
            return cipher_hex
            
        except Exception as e:
            raise ValueError(f"密码加密失败: {str(e)}")

    def download_verifycode(self):
        """下载验证码图片到本地目录"""
        os.makedirs('verification_code', exist_ok=True)
        response = self.session.get(self.verifycode_url)
        if response.status_code == 200:
            # 保存为PNG文件
            with open('verification_code/code.png', 'wb') as f:
                f.write(response.content)
            print("验证码已保存到 verification_code/code.png")
            return True
        print("验证码下载失败")
        return False

    def login(self, max_retries=3):
        """执行登录流程，支持重试"""
        for attempt in range(max_retries):
            if not self.download_verifycode():
                continue
                
            verifycode = input("请输入验证码: ")
            
            try:
                encrypted_pwd = self.encrypt_password(self.password)
                
                # 构造表单数据，参考成功请求示例
                login_data = {
                    "scheme": "login3",
                    "userName": self.username,
                    "passWord": encrypted_pwd,  # 16进制的密文
                    "verifycode": verifycode,
                    "city": "未知",              # 成功请求示例中使用 "未知"
                    "ip": "10.248.200.14",       # 成功请求示例中的ip
                    "equipmentType": "PKD130",   # 成功请求示例中的设备型号
                    "needverifycode": 1
                }
                
                print("即将提交的表单数据:")
                print(json.dumps(login_data, indent=2, ensure_ascii=False))
                
                confirm = input("确认提交? (输入yes继续): ")
                if confirm.lower() != 'yes':
                    print("取消登录")
                    return False
                
                # 使用表单形式提交数据，而非json格式
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded"
                }
                response = self.session.post(self.login_url, data=login_data, headers=headers)
                
                if response.status_code == 200:
                    try:
                        resp_json = response.json()
                    except Exception:
                        resp_json = {}
                    if resp_json.get('code') == 200:
                        print("登录成功")
                        return True
                    else:
                        print(f"登录失败: {response.text}")
                else:
                    print(f"HTTP错误: {response.status_code}")
                
                print(f"剩余重试次数: {max_retries - attempt - 1}")
                
            except Exception as e:
                print(f"登录过程中发生错误: {str(e)}")
                print(f"剩余重试次数: {max_retries - attempt - 1}")
                
        print("登录失败，已达到最大重试次数")
        return False

    def fetch_data(self):
        try:
            response = self.session.get(self.base_url)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"数据获取失败: {e}")
            return None

    def parse_data(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        # 此处添加实际的解析逻辑，解析成列表字典格式
        data = []
        return data

    def save_to_db(self, data):
        df = pd.DataFrame(data)
        df.to_sql('medical_records', self.engine, if_exists='append', index=False)
        print(f"成功保存 {len(data)} 条记录到数据库")

    def run(self):
        if self.login():
            html = self.fetch_data()
            if html:
                data = self.parse_data(html)
                if data:
                    self.save_to_db(data)

if __name__ == "__main__":
    crawler = MedicalDataCrawler()
    crawler.run()
