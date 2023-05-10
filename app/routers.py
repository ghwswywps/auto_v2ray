from flask import Blueprint, render_template, request, session, redirect, url_for

from functools import wraps

import requests
import yaml

bp = Blueprint('routers', __name__)

with open('config.yml') as f:
    config = yaml.safe_load(f)

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
        key = request.form['key']
        headers = {
            "Authorization": f"Bearer {key}",
        }
        response = requests.get(f"{config['vultr']['base_url']}/instances", headers=headers)
        json_data = response.json()
        if "instances" in json_data:
            session['key'] = key
            session['headers'] = headers
            return redirect(url_for('routers.index'))
        else:
            return "key不合法，请查看权限配置"
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