# -*- coding: utf-8 -* -
import socket

def is_port_open(ip,port):
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        s.connect((ip,int(port)))
        s.shutdown(2)
        return True
    except:
        return False

def collect_env_info():
    from torch.utils.collect_env import get_pretty_env_info
    env_str = get_pretty_env_info()
    return env_str

