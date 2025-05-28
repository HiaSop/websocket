from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template
from threading import Thread
from socket_client import start_socket

app = Flask(__name__)

# @app.route('/')
# def index():
#     if 'user_id' in session:
#         user = User.query.get(session['user_id'])
#         return render_template('index.html', username=user.username)
#     else:
#         return redirect(url_for('login'))
#
# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#
#         user = User.query.filter_by(username=username).first()
#         if user and check_password_hash(user.password, password):
#             session['user_id'] = user.id
#             flash('登录成功！', 'success')
#             return redirect(url_for('index'))
#         else:
#             flash('用户名或密码错误', 'danger')
#
#     return render_template('login.html')
#
# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         confirm_password = request.form['confirm_password']
#         csr_file = request.files.get('csr_file')
#
#         if password != confirm_password:
#             flash('两次密码输入不一致', 'danger')
#             return render_template('register.html')
#
#         existing_user = User.query.filter_by(username=username).first()
#         if existing_user:
#             flash('用户名已存在', 'danger')
#             return render_template('register.html')
#
#         hashed_password = generate_password_hash(password)
#
#         csr_data = None
#         if csr_file:
#             csr_data = csr_file.read()
#
#         new_user = User(username=username, password=hashed_password, csr_file=csr_data)
#         db.session.add(new_user)
#         db.session.commit()
#
#         flash('注册成功，请登录', 'success')
#         return redirect(url_for('login'))
#
#     return render_template('register.html')
#
# @app.route('/logout')
# def logout():
#     session.pop('user_id', None)
#     flash('已注销登录', 'info')
#     return redirect(url_for('login'))

if __name__ == '__main__':
    Thread(target=start_socket).start()
    app.run(host='0.0.0.0', port=5001, ssl_context=('server.crt', 'server.key'))
