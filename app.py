import os
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template
from threading import Thread
from socket_client import start_socket, DEVICE_ID, SERVER_URL

app = Flask(__name__)

app.secret_key = os.getenv('SECRET_KEY', 'local-secret-key')

IS_ACTIVE = False
USER_EMAIL = '<EMAIL>'

@app.route('/')
def index():
    if IS_ACTIVE:
        return redirect(url_for('dashboard'))
    else:
        return render_template('login.html')

@app.route('/send-code', methods=['POST'])
def send_code():
    email = request.form.get('email')
    if not email:
        flash('请输入邮箱', 'danger')
        return redirect(url_for('index'))

    try:
        res = requests.post(f'{SERVER_URL}/send-code', json={'email': email}, verify=False)
        if res.status_code == 200:
            flash('验证码已发送，请查收邮箱', 'success')
        else:
            flash(res.json().get('message', '验证码发送失败'), 'danger')
    except Exception as e:
        flash(f'请求失败: {e}', 'danger')

    return render_template('login.html', email=email)

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    code = request.form.get('code')

    try:
        print(request.form.to_dict())
        res = requests.post(f'{SERVER_URL}/user_login',json={'email': email, 'code': code, 'device_id': DEVICE_ID},verify=False)
        if res.status_code == 200:
            token = res.json().get('token')
            session['token'] = token

            global IS_ACTIVE
            IS_ACTIVE = True
            global USER_EMAIL
            USER_EMAIL = email

            flash('登录成功', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(res.json().get('message', '登录失败'), 'danger')
    except Exception as e:
        flash(f'请求失败: {e}', 'danger')

    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if not IS_ACTIVE:
        return render_template('login.html')
    return f"欢迎登录！User：{USER_EMAIL}"

if __name__ == '__main__':
    Thread(target=start_socket).start()
    app.run(host='0.0.0.0', port=5001)
