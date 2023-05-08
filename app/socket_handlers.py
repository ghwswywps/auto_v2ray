
from flask import session, request
from threading import Lock
from flask_socketio import emit, join_room, leave_room, \
    close_room
from threading import Thread
from app import socketio
from .socket_log import get_socket_log,log_queue, with_logging
from .ssh_remote_utils import get_ssh, cmd, cmd_with_log
from .ali_ddns import change_domain_record
import re, requests, time, json, yaml, hashlib

with open('config.yml') as f:
    config = yaml.safe_load(f)
    


# 定义 Vultr API 的基本 URL 和 API 密钥
BASE_URL = config['vultr']['base_url']
API_KEY = config['vultr']['api_key']
USER_ID = config['vultr']['user_id']

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
    # def get_instance_async():
    response = requests.get(f"{BASE_URL}/instances", headers=session['headers'])
    instances = response.json()["instances"]
    logger.log("result:" + json.dumps(instances))

@socketio.event
@with_logging
def get_instance_password(msg, logger = None):
    response = requests.get(f"{BASE_URL}/instances", headers=session['headers'])
    instances = response.json()["instances"]
    if(len(instances) > 0):
        logger.log('find instance,try loging in')
        iid = instances[0]['id']
        response = requests.get(f"{BASE_URL}/instances/{iid}/password", headers=session['headers'])
        logger.log("result:" + json.dumps(response))
    
@socketio.event
def connect_me(msg):
    if 'key' not in session:
        return 'Unauthorized access'
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
            socketio.emit('my_response', re.sub(r'\x1b\[\?2004\w', '', message), room=room_id)
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
    
    response = requests.get(f"{BASE_URL}/instances", headers=session['headers'])
    instances = response.json()["instances"]
    if(len(instances) > 0):
        logger.log('find instance,try loging in')
        ip = instances[0]['main_ip']
        iid = instances[0]['id']
        ssh = get_ssh(ip, get_password(session['key'], iid), logger, max_retries = 1)
        ssh_map[request.sid] = ssh
        channel_map[request.sid] =  ssh.invoke_shell()
        
@socketio.event
@with_logging
def delete_instance(msg, logger = None):
    response = requests.get(f"{BASE_URL}/instances", headers=session['headers'])
    instances = response.json()["instances"]
    # 删除所有 instances
    for instance in instances:
        requests.delete(f"{BASE_URL}/instances/{instance['id']}", headers=session['headers'])
    logger.log("invoke delete_instance ok")
    return 'ok'

@socketio.event
@with_logging
def infect_me(msg, logger = None):
    channel = channel_map.get(request.sid)
    if not channel:
        logger.log('plz connect_ssh first!')
    else:
        channel.send("pip install flask flask-cors flask-socketio paramiko json5 && git clone https://github.com/ghwswywps/auto_v2ray.git" + "\n")
    return 'ok'

 
@socketio.event
@with_logging
def openmldb_chatgpt(msg, logger = None):
    channel = channel_map.get(request.sid)
    if not channel:
        logger.log('here is no connection yet!')
    else:
        channel.send('openmldb-chatgpt\n')
    return 'ok'


@socketio.event
@with_logging
def install_v2ray(msg, logger = None):
    channel = channel_map.get(request.sid)
    if not channel:
        logger.log('here is no connection yet!')
        return
    
    logger.log('开始安装并配置v2ray服务端')
    channel.send('echo -e "1\n2\n10924\n\n\n\n\n" | bash <(curl -s -L https://git.io/v2ray.sh)&& v2ray restart\n')

@socketio.event
@with_logging
def install_warp(msg, logger = None):
    ssh = ssh_map.get(request.sid)
    if not ssh:
        logger.log('plz connect_ssh first!')
    else:
        def install_warp_async():
            cmd_with_log(ssh, logger, 'curl https://pkg.cloudflareclient.com/pubkey.gpg | sudo gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg')
            cmd_with_log(ssh, logger, 'echo "deb [arch=amd64 signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflare-client.list')
            cmd_with_log(ssh, logger, 'sudo apt update')
            cmd_with_log(ssh, logger, 'sudo apt install cloudflare-warp -y')
            cmd_with_log(ssh, logger, 'echo -e "y" |warp-cli register')
            cmd_with_log(ssh, logger, 'warp-cli set-mode proxy')
            cmd_with_log(ssh, logger, 'warp-cli connect')
            cmd_with_log(ssh, logger, 'python3 auto_v2ray/warps_utils.py && v2ray restart')
            logger.log('warp install success!')

        Thread(target=install_warp_async).start()    
        
     

@socketio.event
@with_logging
def create_instance(msg, logger = None):
    sid = request.sid
    channel = channel_map.get(sid)
    if channel:
        channel.close()
        channel_map.pop(sid)
    ssh = ssh_map.get(sid)
    if ssh:
        ssh.close()
        ssh_map.pop(sid)
        
    key = session['key']
    local_headers = session['headers']
    def create_instance_async(sid):
        logger.log('查询并删除已有容器') 
        response = requests.get(f"{BASE_URL}/instances", headers=local_headers)
        instances = response.json()["instances"]
        for instance in instances:
            requests.delete(f"{BASE_URL}/instances/{instance['id']}", headers=local_headers)
        logger.log('有个傻卵嫌这个工具不好用，给他做了一键版的，出现任何问题请刷新页面重来一遍....')
        time.sleep(10)
        logger.log('删除容器完成')
        response = requests.post(f"{BASE_URL}/instances", headers=local_headers, json=data)
        passwd = response.json()["instance"]['default_password']
        logger.log("初始化容器中,此过程大约需要50秒...")
        time.sleep(50)
        response = requests.get(f"{BASE_URL}/instances", headers=local_headers)
        host = response.json()["instances"][0]['main_ip']
        iid = response.json()["instances"][0]['id']
        logger.log(f"初始化容器成功，初始密码：{passwd}，地址：{host}")
        logger.log('开始尝试登录SSH，此过程大约需要30秒')
        ssh = get_ssh(host, passwd, logger)
        ssh_map[sid] = ssh
        
        cmd(ssh,'echo -e "' + get_password(key, iid) + '\n' + get_password(key, iid) + '" | passwd')
        time.sleep(2)
        logger.log('修改成功,新密码：' + get_password(key, iid))
        ssh = get_ssh(host, get_password(key, iid), logger, max_retries = 1)
        logger.log('开始初始化网络，关闭防火墙')
        time.sleep(1)
        cmd_with_log(ssh, logger, 'ufw disable\n')
        logger.log('防火墙已关闭，服务启动完成')
        logger.log('开始安装并配置v2ray服务端')
        cmd_with_log(ssh, logger, 'echo -e "1\n2\n10924\n\n\n\n\n" | bash <(curl -s -L https://git.io/v2ray.sh)')
        cmd_with_log(ssh, logger, "pip install flask flask-cors flask-socketio paramiko json5 && git clone https://github.com/ghwswywps/auto_v2ray.git")
        cmd_with_log(ssh, logger, 'curl https://pkg.cloudflareclient.com/pubkey.gpg | sudo gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg')
        cmd_with_log(ssh, logger, 'echo "deb [arch=amd64 signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflare-client.list')
        cmd_with_log(ssh, logger, 'sudo apt update')
        cmd_with_log(ssh, logger, 'sudo apt install cloudflare-warp -y')
        cmd_with_log(ssh, logger, 'echo -e "y" |warp-cli register')
        cmd_with_log(ssh, logger, 'warp-cli set-mode proxy')
        cmd_with_log(ssh, logger, 'warp-cli connect')
        cmd_with_log(ssh, logger, 'python3 auto_v2ray/warps_utils.py && v2ray restart && v2ray url')
        logger.log('全部安装完成，以用上方的url信息配置v2ray客户端!')
    
    Thread(target=create_instance_async, args=(request.sid,)).start()    
        
    return 'ok'

    
@socketio.event
def terminal(msg):
    logger = get_socket_log()
    channel = channel_map.get(request.sid)
    if not channel:
        logger.log('here is no connection yet!')
    else:
        channel.send(msg + "\n")
    return 'ok';


def get_password(str1, str2):
    # 将两个字符串和时间戳拼接成一个新字符串
    new_str = str1 + str2
    # 使用SHA256哈希函数对新字符串进行哈希运算
    hash_obj = hashlib.sha256(new_str.encode())
    # 生成密码，可以选择截取哈希值的一部分作为密码
    password = hash_obj.hexdigest()[:12]
    return password

