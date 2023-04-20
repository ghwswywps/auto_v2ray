
from flask import session, request
from threading import Lock
from flask_socketio import emit, join_room, leave_room, \
    close_room
from threading import Thread
from app import socketio
from .socket_log import log_queue, with_logging
from .ssh_remote_utils import get_ssh, cmd
from .ali_ddns import change_domain_record
import re, requests, time, json, requests, yaml

with open('config.yml') as f:
    config = yaml.safe_load(f)

# 定义 Vultr API 的基本 URL 和 API 密钥
BASE_URL = config['vultr']['base_url']
API_KEY = config['vultr']['api_key']
USER_ID = config['vultr']['user_id']

headers = None
ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
thread_lock = Lock()
channel_map = {}
ssh_map = {}
thread = None

data = {
            "region": "ewr",
            "plan": "vc2-1c-0.5gb",
            "os_id": 477,
            "hostname": "vultr.guest",
            "label": "guest"
        }



def remove_ansi_codes(text):
    return ansi_escape.sub('', text)

@socketio.event
@with_logging
def get_instance(msg, logger = None):
    def get_instance_async():
        response = requests.get(f"{BASE_URL}/instances", headers=headers)
        instances = response.json()["instances"]
        logger.log("result:" + json.dumps(instances))
    Thread(target=get_instance_async).start()
    
@socketio.event
def connect_me(msg):
    if 'key' not in session:
        return 'Unauthorized access'
    global headers 
    if not headers:
        headers = {
            "Authorization": f"Bearer {session['key'] }",
        }
    print('connect_me:' + msg + 'in room:' + request.sid)
    join_room(request.sid)
        
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)
    emit('my_response', 'Connected, sid:' + request.sid, room=request.sid)
    
@socketio.event
def disconnect():
    channel = channel_map.get(request.sid)
    if channel:
        channel.close()
        channel_map.pop(request.sid)
    ssh = ssh_map.get(request.sid)
    if ssh:
        ssh.close()
        ssh_map.pop(request.sid)
        
    leave_room(request.sid)  # 离开房间
    close_room(request.sid)  # 关闭房间
    print('Client disconnected，room_id:' + request.sid)
    
def background_thread():
    while True:
        loop_run()
    
            
def loop_run():
    try:
        socketio.sleep(0.2)
        while not log_queue.empty():
            message, room_id = log_queue.get()
            socketio.emit('my_response', message, room=room_id)
        rooms_to_delete = set()
        for room_id, channel in channel_map.items():
            if channel.recv_ready():
                output = channel.recv(1024).decode()
                for line in re.sub(r'\x1b\[\?2004\w', '', output).split('\n'):
                    socketio.emit('my_response', remove_ansi_codes(line), room=room_id)
            elif channel.closed:
                rooms_to_delete.add(room_id)
        for room_id in rooms_to_delete:
            del channel_map[room_id]
    except Exception as e:
        socketio.emit('my_response', str(e), room=room_id)

@socketio.event 
@with_logging
def connect_ssh(msg, logger = None):
    if ssh_map.get(request.sid):
        logger.log('there is already a connection established!')
        return
    
    response = requests.get(f"{BASE_URL}/instances", headers=headers)
    instances = response.json()["instances"]
    if(len(instances) > 0):
        logger.log('find instance,try loging in')
        ip = instances[0]['main_ip']
        ssh = get_ssh(ip, session['password'], logger, max_retries = 1)
        ssh_map[request.sid] = ssh
        channel_map[request.sid] =  ssh.invoke_shell()
        
@socketio.event
@with_logging
def delete_instance(msg, logger = None):
    response = requests.get(f"{BASE_URL}/instances", headers=headers)
    instances = response.json()["instances"]
    # 删除所有 instances
    for instance in instances:
        requests.delete(f"{BASE_URL}/instances/{instance['id']}", headers=headers)
    logger.log("invoke delete_instance ok")
    return 'ok'

@socketio.event
@with_logging
def infect_me(msg, logger = None):
    channel = channel_map.get(request.sid)
    if not channel:
        logger.log('plz connect_ssh first!')
    else:
        channel.send("pip install flask flask-cors flask-socketio paramiko && git clone https://github.com/ghwswywps/auto_v2ray.git && cd auto_v2ray && python3 run.py" + "\n")
    return 'ok'

@socketio.event
@with_logging
def install_v2ray(msg, logger = None):
    key = session['key']
    channel = channel_map.get(request.sid)
    if not channel:
        logger.log('here is no connection yet!')
        return
    
    def install_v2ray():
        logger.log('开始安装并配置v2ray服务端')
        channel.send('echo -e "1\n2\n10924\n\n\n\n\n" | bash <(curl -s -L https://git.io/v2ray.sh)\n')
        if key == API_KEY:
            channel.send('''sed -i 's/"id": "[^"]\{36\}"/"id": "''' + USER_ID + '''"/' /etc/v2ray/config.json\n''')
        logger.log('配置完成，重启v2ray服务端')   
        channel.send('v2ray restart\n')

        logger.log('show info:')
        channel.send('v2ray url\n')
        if key == API_KEY:
            response = requests.get(f"{BASE_URL}/instances", headers=headers)
            host = response.json()["instances"][0]['main_ip']
            change_domain_record(host)
        logger.log('安装完成')
    Thread(target=install_v2ray).start()

@socketio.event
@with_logging
def install_warp(msg, logger = None):
    channel = channel_map.get(request.sid)
    if not channel:
        logger.log('plz connect_ssh first!')
    else:
        channel.send('python3 auto_v2ray/warps_utils.py' + '\n')
     

@socketio.event
@with_logging
def create_instance(msg, logger = None):
    password = session['password']
    channel = channel_map.get(request.sid)
    if channel:
        channel.close()
        channel_map.pop(request.sid)
    ssh = ssh_map.get(request.sid)
    if ssh:
        ssh.close()
        ssh_map.pop(request.sid)
    
    def create_instance_async(sid):
        logger.log('查询并删除已有容器')
        response = requests.get(f"{BASE_URL}/instances", headers=headers)
        instances = response.json()["instances"]
        # 删除所有 instances
        for instance in instances:
            requests.delete(f"{BASE_URL}/instances/{instance['id']}", headers=headers)
        # logger.log("删除完成")
        # 创建一个新的 instance
        
        logger.log('删除容器完成')
        response = requests.post(f"{BASE_URL}/instances", headers=headers, json=data)
        passwd = response.json()["instance"]['default_password']
        logger.log("初始化容器中,此过程大约需要30秒...")
        time.sleep(30)
        response = requests.get(f"{BASE_URL}/instances", headers=headers)
        host = response.json()["instances"][0]['main_ip']
        logger.log(f"初始化容器成功，初始密码：{passwd}，地址：{host}")
        logger.log('开始尝试登录SSH，此过程大约需要20秒')
        ssh = get_ssh(host, passwd, logger)
        logger.log('登录成功，开始修改默认密码')
        cmd(ssh,'echo -e "' + password + '\n' + password + '" | passwd')
        time.sleep(2)
        logger.log('修改成功,新密码：' + password)
        ssh = get_ssh(host, password, logger, max_retries = 1)
        ssh_map[sid] = ssh
        channel_map[sid] =  ssh.invoke_shell()
        channel = channel_map[sid]
        logger.log('开始初始化网络，关闭防火墙')
        time.sleep(1)
        channel.send('ufw disable\n')
        logger.log('防火墙已关闭，服务启动完成')
        
    Thread(target=create_instance_async, args=(request.sid,)).start()
    return 'ok'

    
@socketio.event
@with_logging
def terminal(msg, logger = None):
    channel = channel_map.get(request.sid)
    if not channel:
        logger.log('here is no connection yet!')
    else:
        channel.send(msg + "\n")
    return 'ok';
