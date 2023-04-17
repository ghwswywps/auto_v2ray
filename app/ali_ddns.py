import time
import hmac
import hashlib
import base64
import urllib.parse
import http.client
import uuid
import yaml

with open('config.yml') as f:
    config = yaml.safe_load(f)

# 定义 Vultr API 的基本 URL 和 API 密钥
access_key_id = config['ali_ddns']['access_key_id']
access_key_secret = config['ali_ddns']['access_key_secret']
domain_name = config['ali_ddns']['domain_name']
record_id = config['ali_ddns']['record_id']

signature_nonce = str(uuid.uuid4())

# 构造 API 请求参数


def change_domain_record(ip):
    params = {
    "Action": "UpdateDomainRecord",
    "DomainName": domain_name,
    "RecordId": record_id,
    "RR": "vultr",
    "Type": "A",
    "Value": ip,
    }

    # 设置 API 请求参数的公共部分
    params["Version"] = "2015-01-09"
    params["Format"] = "JSON"
    params["AccessKeyId"] = access_key_id
    params["SignatureMethod"] = "HMAC-SHA1"
    params["Timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    params["SignatureVersion"] = "1.0"
    params["SignatureNonce"] = signature_nonce
    # 构造待签名字符串
    canonicalized_query_string = "&".join([f"{k}={urllib.parse.quote_plus(str(params[k]))}" for k in sorted(params)])
    string_to_sign = f"GET&%2F&{urllib.parse.quote_plus(canonicalized_query_string)}"

    # 计算签名
    hmac_key = bytes(f"{access_key_secret}&", encoding="utf-8")
    signature = base64.b64encode(hmac.new(hmac_key, bytes(string_to_sign, encoding="utf-8"), hashlib.sha1).digest()).decode()

    # 将签名加入 API 请求参数
    params["Signature"] = signature

    # 发送 API 请求
    conn = http.client.HTTPSConnection("alidns.aliyuncs.com")
    conn.request("GET", f"/?{canonicalized_query_string}&Signature={urllib.parse.quote_plus(signature)}")
    response = conn.getresponse()
    response_text = response.read().decode()
    conn.close()

    # 解析响应内容
    result = response_text.strip().split("\n")[-1]
    if result == "true":
        print("Update record success.")
    else:
        print("Update record failed.")


    # change_domain_record('66.135.8.158')
    # return