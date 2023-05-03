import re
import json5



config_file_path = "/etc/v2ray/config.json"  


with open(config_file_path, 'r') as f:
    config_data = json5.load(f)
    
    if any(item['tag'] == 'chat_gpt' for item in config_data["outbounds"]):
        print("已存在")
    else:
        # 插入新的outbound
        new_outbound = {
            "tag": "chat_gpt",
            "protocol": "socks",
            "settings": {
                "servers": [
                    {
                        "address": "127.0.0.1",
                        "port": 40000,
                        "users": []
                    }
                ]
            }
        }
        config_data["outbounds"].append(new_outbound)

        # 修改rules
        new_rule = {
            "type": "field",
            "outboundTag": "chat_gpt",
            "domain": [
                "openai.com",
                "bing.com"
            ],
            "enabled": True
        }
        config_data["routing"]["rules"].append(new_rule)
        
# 将修改后的配置写回文件
with open(config_file_path, 'w') as f:
    pattern = re.compile(r',(\s*[\]}])')
    # 直接将Python对象写入文件
    f.write(pattern.sub(r'\1', json5.dumps(config_data, indent=4, quote_keys=True)))




