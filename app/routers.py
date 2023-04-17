from flask import Blueprint, render_template, request, session, redirect, url_for

from functools import wraps

bp = Blueprint('routers', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'key' not in session:
            return redirect(url_for('routers.login')) 
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        key = request.form['key']
        session['key'] = key
        session['password'] = password
        global headers 
        headers = {
                "Authorization": f"Bearer {key}",
            }
        return redirect(url_for('routers.index'))
    return render_template('login.html')

@bp.route('/logout')
def logout():
    session.pop('key', None)
    session.pop('password', None)
    return redirect(url_for('routers.login'))

@bp.route('/')
@login_required
def index():
    return render_template('index.html')