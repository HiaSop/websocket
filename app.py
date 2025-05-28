from flask import Flask, render_template, request, jsonify, render_template_string
from flask_socketio import SocketIO, send, emit, disconnect
from models import db, Device
from config import Config
from datetime import datetime, timedelta

app = Flask(__name__)
# 允许所有跨域
app.config.from_object(Config)
db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")

with app.app_context():
    db.create_all()

# -----------------------------------------------------------------------------------------------
# WebSocket 事件处理
# -----------------------------------------------------------------------------------------------

# 客户端连接时触发
@socketio.on('connect')
def handle_connect():
    """设备连接时验证并更新状态"""
    device_id = request.args.get('device_id')

    # 检查 device_id 是否存在
    if not device_id:
        print("")
        emit('error', '缺少 device_id 参数')
        disconnect()
        return
    device = db.session.get(Device, device_id)
    if not device:
        print("Device not found")
        disconnect()
        return

    # 更新设备状态
    device.is_active = True
    device.websocket_id = request.sid
    device.last_heartbeat = datetime.now()
    db.session.commit()

    emit('status', {'is_active': True, 'device_id': device_id})

@socketio.on('disconnect')
def handle_disconnect():
    """设备断开时更新状态"""
    device = Device.query.filter_by(websocket_id=request.sid).first()
    if device:
        device.is_active = False
        device.websocket_id = None
        db.session.commit()

@socketio.on('heartbeat')
def handle_heartbeat():
    """处理心跳包"""
    device = Device.query.filter_by(websocket_id=request.sid).first()
    if device:
        device.last_heartbeat = datetime.now()
        db.session.commit()

if __name__ == '__main__':
    print("✅ 启动服务器：https://localhost:5000")
    socketio.run(app, port=5000, ssl_context=('server.crt', 'server.key'), debug=True)
