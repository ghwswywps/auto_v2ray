import vultr
import yaml

data = {
    "region": "ewr",
    "plan": "vc2-1c-0.5gb",
    "os_id": 477,
    "hostname": "vultr.guest",
    "label": "guest"
}

# Initialize the Vultr API client with the API key
with open('config.yml') as f:
    config = yaml.safe_load(f)

# 定义 Vultr API 的基本 URL 和 API 密钥
VULTR_API_KEY = config['vultr']['api_key']

def get_client(key):
    return vultr.Vultr(key)




