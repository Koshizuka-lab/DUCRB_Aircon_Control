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

# 空調制御の対象外の部屋
EXCLUDE_ROOMS_AIRCONDITIONER = [
    # サーバールーム
    "B1SVR",
    "B1SMR",
    # 他研究室から要望のあった調整対象外の部屋
    "B203",
    "A103"
]

# 換気扇制御の対象外の部屋
EXCLUDE_ROOMS_VENTILATION = [
    # サーバールーム
    "B1SVR",
    "B1SMR",
    # GALLERY_ROOM: B1~B2Fのギャラリー室
    "B106",
    "B205",
    # 他研究室から要望のあった調整対象外の部屋
    "B203",
    "A103"
]

# エアコン制御
def searchActiveRoom(bLight:bool):
    url = BASE_URL + "airconditioner/ALL/"
    req = requests.get(url, auth=(ID, PW))

    activeRoom = []
    controlResult = ""

    # 稼働中の部屋情報のみ抽出
    for data in req.json():
        if (data['on_off'] == 1):
            # APIレスポンスのnameから先頭３文字目から抽出("A-"を省くため) + UnicodeのNull文字を除去
            name = re.sub('\u0000', '', data['name'][3:])
            # 部屋ごとの機数番号("-1", "-2", "-3")を除去
            name = re.sub('-1|-2|-3', "", name)
            # 廊下の機数番号(1, 2, 3)を除去
            name = re.sub('WAY1|WAY2|WAY3', "WAY", name)

            # 対象外の部屋の場合何もしない
            if(name not in EXCLUDE_ROOMS_AIRCONDITIONER):
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

    # 操作対象が0件だった場合の出力文字追加処理
    if (len(activeRoom) == 0):
        controlResult += "操作対象はありませんでした。\n"
    else:
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
    postSlack(str(datetime.datetime.today().strftime("%Y/%m/%d %H:%M:%S")) + ": 稼働中エアコン停止処理結果\n" + controlResult)

# 換気扇制御
def serachAcitiveVentilationRoom(bLight:bool):
    url = BASE_URL + "ventilationunit/ALL/"
    req = requests.get(url, auth=(ID, PW))
    
    activeRoom = []
    controlResult = ""

    for data in req.json():
        if (data['on_off'] == 1):
            name = re.sub('\u0000', '', data['name'][3:])
            
            # 対象外の部屋の場合何もしない
            if(name not in EXCLUDE_ROOMS_VENTILATION):
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

    # 操作対象が0件だった場合の出力文字追加処理
    if (len(activeRoom) == 0):
        controlResult += "操作対象はありませんでした。\n"
    else:
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
    postSlack(str(datetime.datetime.today().strftime("%Y/%m/%d %H:%M:%S")) + ": 稼働中換気扇停止処理結果\n" + controlResult)


# 照明が付いている部屋の配列を返す
def searchActiveLightRoom(activeRoom):
    url = BASE_URL + "light/"
    activeLightRoom = []
    
    for room in activeRoom:
        # 部屋以外(廊下, エレベータホール, サーバルーム, 電気室, 共有機材室)がfind(-1以外)されると　continue実行
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

# 結果をslackへ投稿
def postSlack(message:str):
    slack = slackweb.Slack(url=SLACK_URL)
    slack.notify(text=message)
    
if __name__ == '__main__':
    # args: 実行時引数
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
