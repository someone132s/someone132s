#!/usr/bin/env python3
from pysm4 import encrypt_ecb, encrypt_cbc
from binascii import unhexlify
import base64

def sm4_encrypt():
    """交互式SM4加密测试"""
    print("SM4加密测试工具")
    print("="*30)
    
    try:
        # 获取用户输入
        plaintext = input("请输入要加密的明文: ").strip()
        key_hex = input("请输入16进制密钥(32字符): ").strip()
        mode = input("加密模式(ecb/cbc, 默认ecb): ").strip().lower() or "ecb"
        
        # 验证输入
        if not plaintext:
            raise ValueError("明文不能为空")
        if len(key_hex) != 32:
            raise ValueError("密钥必须是32字符的16进制字符串")
        if mode not in ("ecb", "cbc"):
            raise ValueError("加密模式必须是ecb或cbc")
            
        # 转换密钥: 从16进制转换为bytes后，再转换为latin1字符串
        try:
            key_bytes = unhexlify(key_hex)
            if len(key_bytes) != 16:
                raise ValueError("密钥长度必须为16字节(32字符16进制)")
            key_str = key_bytes.decode('latin1')
        except Exception as e:
            raise ValueError(f"密钥转换错误: {str(e)}")
        
        # 执行加密
        try:
            if mode == "ecb":
                ciphertext = encrypt_ecb(plaintext, key_str)
            else:
                iv_hex = input("请输入16进制IV(32字符): ").strip()
                iv_bytes = unhexlify(iv_hex)
                if len(iv_bytes) != 16:
                    raise ValueError("IV必须是32字符的16进制字符串")
                iv_str = iv_bytes.decode('latin1')
                ciphertext = encrypt_cbc(plaintext, key_str, iv_str)
        except Exception as e:
            raise ValueError(f"加密失败: {str(e)}. 请确认密钥和输入数据格式正确")
        
        # 将base64字符串转换为16进制字符串
        try:
            cipher_bytes = base64.b64decode(ciphertext)
            cipher_hex = cipher_bytes.hex()
        except Exception as e:
            raise ValueError(f"转换密文为16进制失败: {str(e)}")
        
        # 输出结果
        print("\n加密结果:")
        print(f"模式: SM4-{mode.upper()}")
        print(f"密钥: {key_hex}")
        if mode == "cbc":
            print(f"IV: {iv_hex}")
        print(f"明文: {plaintext}")
        print(f"密文(hex): {cipher_hex}")
        
    except Exception as e:
        print(f"\n错误: {str(e)}")
        print("用法示例:")
        print("明文: hello123 (直接输入字符串)")
        print("密钥: 32字符16进制字符串，如: 0123456789abcdef0123456789abcdef")
        print("模式: ecb 或 cbc")
        print("注意:")
        print("- 密钥会先从16进制转换为16字节，再转换为latin1字符串")
        print("- 加密后的结果会从base64转换为16进制")
        print("- 确保pysm4库已正确安装")
        print("- 如果使用Docker, 请确认容器内已安装pysm4")

if __name__ == "__main__":
    sm4_encrypt()
