import paramiko
import time
import socket


def get_ssh(host, passwd, logger, max_retries=15, timeout=10):
    retries = 0
    while retries < max_retries:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host, port=22, username='root', password=passwd, timeout=timeout)
            return ssh
        except (paramiko.ssh_exception.SSHException, socket.error) as e:
            retries += 1
            logger.log(f"SSH connection failed (attempt {retries}/{max_retries}): {e}")
            time.sleep(10)
    raise logger.log(f"Failed to establish SSH connection to {host} after {max_retries} attempts")


def cmd(ssh,cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    return stdout.read().decode()

