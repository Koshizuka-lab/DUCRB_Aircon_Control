# エアコンおよび換気扇の電源を停止させる(B1サーバ室とB106以外)
import requests
import json
import re
import time
import datetime
import slackweb
import initFile
import sys

# initData読み取り
data = initFile.initData()

# Aircon操作用のbaseUrl
BASE_URL = data['url']

# aircon_control チャンネルを指定
SLACK_URL = data['slack']

ID = data['id'].decode("utf-8")
PW = data['pw'].decode("utf-8")

SUCCESS_CODE = "204"
SERVER_ROOM = "B1SVR"
GALLERY_ROOM = "B106"


def searchActiveRoom(bLight:bool):
    url = BASE_URL + "airconditioner/ALL/"
    req = requests.get(url, auth=(ID, PW))

    activeRoom = []

    # 稼働中の部屋情報のみ抽出
    for data in req.json():
        if (data['on_off'] == 1):
            # APIレスポンスのnameから先頭３文字目から抽出("A-"を省くため) + UnicodeのNull文字を除去
            name = re.sub('\u0000', '', data['name'][3:])
            # 部屋ごとの機数番号("-1", "-2", "-3")を除去
            name = re.sub('-1|-2|-3', "", name)
            # 廊下の機数番号(1, 2, 3)を除去
            name = re.sub('WAY1|WAY2|WAY3', "WAY", name)

            # B1のサーバ室は対象から除外
            if (name != SERVER_ROOM):
                activeRoom.append(name)

    # 部屋情報の重複削除
    activeRoom = sorted(list(set(activeRoom)), key=activeRoom.index)

    # 部屋の照明を考慮するか
    if (bLight):
        # 照明がアクティブな部屋を取得
        activeLightRoom = searchActiveLightRoom(activeRoom)
        
        # エアコンを消す部屋の一覧から、電気がついている部屋を除去(電気がついていない部屋のみエアコンを停止させるため)
        for lightRoom in activeLightRoom:
            activeRoom.remove(lightRoom)

    # 稼働中の部屋に対してAPI操作実行
    for room in activeRoom:
        result = str(controlMethod("airconditioner/", room))
        if (result == SUCCESS_CODE):
            result += "(成功)"
        else:
            result += "(失敗)"
        controlResult += (room + ": " + result + "\n")
        time.sleep(1)
    
    # slackへ結果を投稿
    postSlack(str(datetime.datetime.today()) + ": 稼働中エアコン停止処理結果\n" + controlResult)

def serachAcitiveVentilationRoom(bLight:bool):
    url = BASE_URL + "ventilationunit/ALL/"
    req = requests.get(url, auth=(ID, PW))
    
    activeRoom = []

    for data in req.json():
        if (data['on_off'] == 1):
            name = re.sub('\u0000', '', data['name'][3:])
            
            # サーバ室とB106(ギャラリー室)は調整対象から除外
            if (name != SERVER_ROOM and name != GALLERY_ROOM):
                activeRoom.append(name)
    
    # 部屋情報の重複削除
    activeRoom = sorted(list(set(activeRoom)), key=activeRoom.index)

    # 部屋の照明を考慮するか
    if (bLight):
        # 照明がアクティブな部屋を取得
        activeLightRoom = searchActiveLightRoom(activeRoom)
        
        # エアコンを消す部屋の一覧から、電気がついている部屋を除去(電気がついていない部屋のみエアコンを停止させるため)
        for lightRoom in activeLightRoom:
            activeRoom.remove(lightRoom)

    # 稼働中の部屋に対してAPI操作実行
    for room in activeRoom:
        result = str(controlMethod("ventilationunit/", room))
        if (result == SUCCESS_CODE):
            result += "(成功)"
        else:
            result += "(失敗)"
        controlResult += (room + ": " + result + "\n")
        time.sleep(1)
    
    # slackへ結果を投稿
    postSlack(str(datetime.datetime.today()) + ": 稼働中換気扇停止処理結果\n" + controlResult)


# 照明が付いている部屋の配列を返す
def searchActiveLightRoom(activeRoom):
    url = BASE_URL + "light/"
    activeLightRoom = []
    
    for room in activeRoom:
        # 部屋以外(廊下, エレベータホール, サーバルーム, 電気室)がfind(-1以外)されると　continue実行
        if (room.find("WAY") != -1 or room.find("EVH") != -1 or
            room.find("SVR") != -1 or room.find("EL") != -1 or
            room.find("SMR") != -1):
            continue
        lightUrl = url + room + "/"
        req = requests.get(lightUrl, auth=(ID, PW))

        for data in req.json():
            if (data['data'][0]['instance'] != "0"):
                activeLightRoom.append(room)

    return activeLightRoom

def controlMethod (controlActuator, roomName):
    url = BASE_URL + controlActuator

    headers = {
        "Content-Type": "application/json"}
    putdata = {
        'id': roomName, # RoomName or Aircon ID
        'setting_bit': 0x01,
        'on_off': 0,
        'operation_mode': 0,
        'ventilation_mode': 0,
        'ventilation_amount': 0,
        'set_point': 0,
        'fan_speed': 0,
        'fan_direction': 0,
        'filter_sign_reset': 0
    }
    req = requests.put(url, data=json.dumps(putdata), headers=headers, auth=(ID, PW))
    return req.status_code

def postSlack(message:str):
    # slackへ結果を投稿
    slack = slackweb.Slack(url=SLACK_URL)
    slack.notify(text=message)
    
if __name__ == '__main__':
    args = sys.argv
    if (len(args) == 2):
        if (args[1] == "True"):
            # 照明状況を考慮(照明がついていれば空調操作をしない)
            searchActiveRoom(True)
            serachAcitiveVentilationRoom(True)
        elif (args[1] == "False"):
            # 照明状況を考慮しない(空調がついている場所を停止させる)
            searchActiveRoom(False)
            serachAcitiveVentilationRoom(False)            
        else:
            print("Prameter Error")
    else:
        print("Prameter Error")