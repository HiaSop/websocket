import socketio
import time
import threading
import json
from flask_socketio import SocketIO, send, emit, disconnect
import random
import base64
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

latest_electricity_usage = None  # 全局变量，存用电量
random_number = None

# 生成设备ID（如果未注册，需先通过服务端API创建）
DEVICE_ID = "1"  # 示例：替换为实际设备ID
SERVER_URL = "https://localhost:5000"

# 创建客户端实例
client_sio = socketio.Client(ssl_verify=False) #自签名证书，开发环境不验证

@client_sio.event
def connect():
    """连接成功回调"""
    print('[成功] 已连接到服务器')

@client_sio.event
def message(data):
    print(f'收到服务端消息: {data}')

@client_sio.event
def status(data):
    """接收服务端状态通知（如心跳响应）"""
    print(f'[状态] {data}')

@client_sio.event
def error(data):
    """接收错误消息"""
    print(f'[错误] {data}')
    client_sio.disconnect()

@client_sio.event
def disconnect():
    """断开连接回调"""
    print('[警告] 连接已断开')

def send_heartbeat():
    """定时发送心跳包（每30秒一次）"""
    while True:
        time.sleep(30)
        try:
            client_sio.emit('heartbeat')
        except:
            break

def start_socket():
    try:
        # 连接时传递 device_id 和 password
        client_sio.connect(
            f'https://localhost:5000?device_id={DEVICE_ID}',
            transports=['websocket'],
        )

        # 启动心跳线程
        heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
        heartbeat_thread.start()

        # 用户输入循环
        while True:
            msg = input("输入消息（或输入 'exit' 退出）: ")
            if msg.lower() == 'exit':
                client_sio.disconnect()
                break
            client_sio.send(msg)

    except socketio.exceptions.ConnectionError as e:
        print(f'[错误] 连接失败: {e}')
    except KeyboardInterrupt:
        client_sio.disconnect()

def emit_user_decision(device_id, decision, electricity_usage):
    global latest_electricity_usage
    payload = {
        "device_id": device_id,
        "decision": decision,
    }
    if electricity_usage is not None:
        latest_electricity_usage = float(electricity_usage)
    client_sio.emit("user_decision", payload)

# 加载自己的私钥
def load_private_key():
    path = f"device_{DEVICE_ID}_private.pem"
    with open(path, "rb") as key_file:
        return serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )

# 加载目标设备的公钥（字符串 PEM）
def load_public_key(cert_pem_str):
    # 解析 X.509 证书
    cert = x509.load_pem_x509_certificate(cert_pem_str.encode(), default_backend())
    # 提取公钥
    return cert.public_key()


# 用公钥加密字符串（比如 "235.7"）
def encrypt_number(value: float, target_cert: str) -> str:
    public_key = load_public_key(target_cert)
    plaintext = str(value)
    encrypted = public_key.encrypt(
        plaintext.encode("utf-8"),
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    )
    return base64.b64encode(encrypted).decode("utf-8")

# 用私钥解密密文字符串，返回 float
def decrypt_number(encrypted_b64: str, private_key) -> float:
    encrypted = base64.b64decode(encrypted_b64)
    decrypted_bytes = private_key.decrypt(
        encrypted,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    )
    return float(decrypted_bytes.decode("utf-8"))

DEVICE_PRIVATE_KEY = load_private_key()

@client_sio.event
def chain_step(data):
    global latest_electricity_usage
    """统一处理链式计算步骤（用电量加法）"""
    prev_result = data.get("prev_result")  # 前一设备传来的加密结果（电量）
    target_cert = data.get("target_cert")  # 下一设备的公钥证书（PEM 字符串）

    if latest_electricity_usage is None:
        print("[链式任务] ⚠️ 当前未记录用电量，无法处理")
        return

    print(f'[链式任务] 收到链式任务，目标证书片段: {target_cert[:30]}...')

    if prev_result is None:
        # 第一个设备：用电量 + 小随机扰动
        global random_number
        random_number = random.uniform(0.1, 1.0)
        my_usage = latest_electricity_usage + random_number
        print(f'[链式任务] 第一个设备，用电量(含随机扰动): {my_usage:.2f}')
        encrypted_result = encrypt_number(my_usage, target_cert)
    else:
        try:
            prev_value = decrypt_number(prev_result, DEVICE_PRIVATE_KEY)
            print(f'[链式任务] 解密得到之前总电量: {prev_value:.2f}')
        except Exception as e:
            print(f'[链式任务] ❌ 解密失败: {e}')
            return

        total = prev_value + latest_electricity_usage
        print(f'[链式任务] 当前总电量 = {prev_value:.2f} + {latest_electricity_usage:.2f} = {total:.2f}')
        encrypted_result = encrypt_number(total, target_cert)

    # 发回服务器
    client_sio.emit("chain_response", {
        "device_id": DEVICE_ID,
        "result": encrypted_result
    })
    print(f'[链式任务] ✅ 电量加密并发出')

# 加载服务器公钥（从 PEM 格式证书中）
def load_server_public_key(path="server.pem"):
    with open(path, "rb") as cert_file:
        cert = x509.load_pem_x509_certificate(cert_file.read(), default_backend())
        return cert.public_key()

SERVER_PUBLIC_KEY = load_server_public_key()

@client_sio.event
def chain_complete(data):
    global random_number
    print(random_number)
    """接收链条最终结果（服务器返回到第一个设备）"""
    final_input = data.get("final_input")
    print(f'[链式任务] 收到最终结果（Base64 编码）: {final_input}')

    try:
        # 解密收到的最终结果（用设备私钥）
        final_value = decrypt_number(final_input, DEVICE_PRIVATE_KEY) - random_number
        print(f'[链式任务] 解密后的最终用电量: {final_value:.2f}')

        # 用服务器公钥重新加密
        plaintext = str(final_value)
        re_encrypted = SERVER_PUBLIC_KEY.encrypt(
            plaintext.encode("utf-8"),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        processed = base64.b64encode(re_encrypted).decode("utf-8")

        # 发回服务器
        client_sio.emit("chain_response", {
            "device_id": DEVICE_ID,
            "final_result": processed
        })
        print(f'[链式任务] 最终处理完成，已用服务器公钥加密并返回')

    except Exception as e:
        print(f'[链式任务] ❌ 最终处理失败: {e}')

