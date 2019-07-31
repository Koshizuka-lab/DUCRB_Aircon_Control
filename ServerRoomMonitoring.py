import requests
import json
import re
import time
import datetime
import initFile
import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate

# initData読み取り
data = initFile.initData()

# Aircon操作用のbaseUrl
BASE_URL = data['url']

ID = data['id'].decode("utf-8")
PW = data['pw'].decode("utf-8")


MAIL_ADD = data['mailAdd']
MAIL_PW = data['mailPw'].decode("utf-8")
TO_MAIL_ADD = data['toMailAdd']
CC_MAIL_ADD = data['ccMailAdd']

SUCCESS_CODE = "204"

ROOM = "b1svr"

# 設定情報閾値
ROOMTEMP = 25
SETTEMP = 20
FANSPEED = 2

def fanSpeed(num):
    if(num == 0):
        return "弱風"
    elif (num == 1):
        return "強風"
    elif (num == 2):
        return "急風(最大値)"
    else:
        return "未定義"

def operationMode(num):
    if (num == 1):
        return "送風"
    elif (num == 2):
        return "暖房"
    elif (num == 4):
        return "冷房"
    elif (num == 32):
        return "換気"
    elif (num == 64):
        return "ドライ"
    elif (num == 128):
        return "自動"
    else:
        return "未定義"

def fanDirection(num):
    if (num in {0, 1, 2, 3, 4}):
        return "固定"
    elif (num == 7):
        return "スイング"
    else:
        return "未定義"
    
def fanPower(num):
    if (num == 0):
        return "OFF"
    elif (num == 1):
        return "ON"
    else:
        return "未定義"
    
def apiResultCode(num):
    if (num == SUCCESS_CODE):
        return "成功"
    else:
        return "失敗\n至急管理者に連絡をしてください！\n"

def convertResultMessage(data): 
    message = "空調電源：" + fanPower(int(data["on_off"])) + "\n"
    message += "運転モード：" + operationMode(int(data["operation_mode"])) + "\n"
    message += "室内温度：" + str(data["room_temp"]) + "℃\n"
    message += "設定温度：" + str(data["set_temp"]) + "℃\n"
    message += "風量：" + fanSpeed(int(data["fan_speed"])) + "\n"
    message += "風向：" + fanDirection(int(data["fan_direction"])) + "\n"
    return message

def checkStatus(power, roomTemp, setTemp, fanSpeed):
    if (power == 0):
        return "【警告】"
    elif (roomTemp <= ROOMTEMP and setTemp <= SETTEMP and fanSpeed == FANSPEED):
        return "【正常】"
    else:
        return "【注意】"

def getAirconStatus():
    url = BASE_URL + "airconditioner/" + ROOM + "/"
    return requests.get(url, auth=(ID, PW))

def checkAircon():
    postStatus = ""
    postMessage = "サーバ室空調稼働状況\n" 
    postMessage += "時刻：" + str(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")) + "\n\n"
    
    req = getAirconStatus()
    data = req.json()[0]
    
    if (int(req.status_code) != 200):
        postMessage += "空調APIを実行しましたが、情報を取得できませんでした。\n"
        postMessage += "API管理者に稼働状況を確認をしてください。\n"
        postStatus = "【警告】"
    else:
        postMessage += convertResultMessage(data)
        if (int(data["on_off"]) == 0):
            postMessage += "\n!!サーバ室の空調が停止しているため、空調の再起動処理を実行します。!!\n\n"
            resultCode = int(controlMethod("airconditioner/", ROOM))
            postMessage += "再起動処理結果：" + apiResultCode(resultCode) + "\n"
            time.sleep(3)
            postMessage += "===============================\n"
            postMessage += "再起動処理後 サーバ室空調稼働状況\n"
            postMessage += "時刻：" + str(datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")) + "\n\n"

            req = getAirconStatus()
            data = req.json()[0]
            postMessage += convertResultMessage(data)
            postMessage += "===============================\n"

        postStatus = checkStatus(int(data["on_off"]), int(data["room_temp"]), int(data["set_temp"]), int(data["fan_speed"]))
        
    postMessage += "\n\n===========================\n"
    postMessage += "越塚研究室 APIサーバプログラム\n"
    postMessage += "【警告】の場合は空調がOFF状態、またはAPIの応答がない状態です。\n"
    postMessage += "【注意】の場合は下記のいずれかの状態になっています。\n"
    postMessage += "室内温度が26℃以上、設定温度が21℃以上、風量が急風以外\n"
    postMessage += "===========================\n"
    
#     print(postMessage)
#     print(postStatus)
    sendMail(postMessage, postStatus)

    
def controlMethod (controlActuator, roomName):
    url = BASE_URL + controlActuator

    headers = {
        "Content-Type": "application/json"}
    putdata = {
        'id': roomName, # RoomName or Aircon ID
        'setting_bit': 0xFF,
        'on_off': 1,
        'operation_mode': 4,
        'ventilation_mode': 0,
        'ventilation_amount': 0,
        'set_point': 20.0,
        'fan_speed': 2,
        'fan_direction': 7,
        'filter_sign_reset': 0
    }
    req = requests.put(url, data=json.dumps(putdata), headers=headers, auth=(ID, PW))
    return req.status_code


def sendMail(message, status):
    smtpobj = smtplib.SMTP('smtp.gmail.com', 587)
    smtpobj.ehlo()
    smtpobj.starttls()
    smtpobj.ehlo()
    smtpobj.login(MAIL_ADD, MAIL_PW)
    
    msg = MIMEText(message)
    msg['Subject'] = status + "ダイワユビキタス サーバ室空調稼働状況"
    msg['From'] = MAIL_ADD
    msg['To'] = TO_MAIL_ADD
    msg['cc'] = CC_MAIL_ADD
    msg['Date'] = formatdate()
#     print(msg)

    # 送信先を一つにまとめる(sendmailの仕様)
    MAIL_LIST = TO_MAIL_ADD.split(',')+CC_MAIL_ADD.split(',')

    smtpobj.sendmail(MAIL_ADD, MAIL_LIST, msg.as_string())
    smtpobj.close()
    
if __name__ == '__main__':
    checkAircon()
