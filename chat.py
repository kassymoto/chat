# coding:utf-8
import json
import csv
import os
import re
from datetime import *
from bottle import *

#static以下のファイルアクセス用のルーティング
@route('/static/<file_path:path>')
def static(file_path):
    return static_file(file_path, root="./static")

#images以下のファイルアクセス用のルーティング
@route('/images/<file_path:path>')
def static(file_path):
    return static_file(file_path, root="./images")

#一番最初はここにルーティングする
@route("/")
def index():
    return template("index",message="")

#index.htmlでsign inした時のルーティング
@route("/enter", method=["POST"])
#入力されたログイン情報を確認してログイン処理をする
def enter():
    #postされたユーザーネームの取得
    username = request.POST.get("username")
    print("POST username is ", username)
    #postされたパスワードの取得
    password = request.POST.get("password")
    print("{0}'s password is {1}".format(username,password))

    #現在登録されているユーザ名とパスワードをCSVから取得
    user_pass = get_user_pass()

    #取得したユーザ名、パスワードを登録されている情報と照らし合わせる
    for i in user_pass:
        #ユーザ名、パスワードが正しかったとき
        if i['username']==username and i['password']==password:
            #cookieにユーザ名を登録する。
            response.set_cookie("username", username)
            #ログイン情報が正しいのでchat_roomにアクセス
            return redirect("/chat_room")
    #入力された情報が正しくないのでエラーメッセージとともにindex.htmlへ
    return template("index",message="ユーザ名かパスワードが間違っています。")

#index.htmlでsign upした時のルーティング
@route("/registration", method=["POST"])
#入力されたユーザ名、パスワードを新規ログイン情報としてCSVに登録する。
def registration():
    try:
        #postされたユーザ名を取得する
        username = request.POST.get("username")
        #postされたパスワードを取得する
        password = request.POST.get("password")

        #現在登録されているユーザ名とパスワードをCSVから取得。
        user_pass = get_user_pass()

        #すでに同じユーザー名が登録されていないか調べる
        for i in user_pass:
            #postされたユーザ名がすでに登録されていた場合
            if i['username']==username:
                #エラーメッセージを設定し、index.htmlへ
                return template("index",message="入力されたユーザ名は既に登録されています。")
        #ユーザ名に重複がなかったので、ユーザ名とパスワードを新規ログイン情報としてCSVに登録
        save_user_pass(username, password)

    #マルチバイトはcookieに登録できないのでエラーになってしまう。→改善の余地あり
    except UnicodeEncodeError:
        #エラーメッセージを設定し、index.htmlへ
        return template("index",message="ユーザ名・パスワードは半角アルファベット及び数字のみ使用可となります。")

    #無事にすべての処理が終わったら、登録完了を伝え、index.htmlへ
    return template("index",message="新規登録完了しました。Sign inしてください。")

#ログインに成功したらchat_roomへアクセスする。
@route("/chat_room")
#chat_room.htmlへアクセスする際の処理
def chat_room():
    #cookieからユーザーネームを取得
    username = request.get_cookie("username")

    #cookieにユーザ情報がない場合は入室画面へ戻す
    if not username:
        return redirect("/")

    #csvからこれまでのチャットデータを取得
    talk_list = get_talk()

    #取得した情報を渡してchat_roomにアクセス
    return template("chat_room", username=username, talk_list=talk_list)


#chat_roomで発言した時のルーティング
@route("/talk", method=["POST"])
#発言を登録する。
def talk():
    #発言をpostから取得 日本語も使えるのでunicodeで取得しないと文字化けする
    chat_data = request.POST.getunicode("chat")

    #発言者をcookieから取得
    username = request.get_cookie("username")

    #発言時間取得
    talk_time = datetime.now()

    #発言をCSVに保存
    save_talk(talk_time, username, chat_data)

    #chat_roomにリダイレクトする
    return redirect("/chat_room")

#APIとして発言を管理する 非同期通信の実装に際して必要
@route("/api/talk", method=["GET", "POST"])
def talk_api():

    #GETの場合は発言一覧を返す
    if request.method == "GET":
        #CSVからトークデータを取得する
        talk_list = get_talk()
        #json形式で返す
        return json.dumps(talk_list)

    #POSTの場合は発言を保存する
    elif request.method == "POST":
        #発言をPOSTから取得　日本語なのでgetunicode
        chat_data = request.POST.getunicode("chat")
        #発言者をcookieから取得
        username = request.get_cookie("username")
        #発言時間取得
        talk_time = datetime.now()
        #発言をCSVに保存
        save_talk(talk_time, username, chat_data)
        #jsonに変換して保存
        return json.dumps({
            "status": "success"
        })


#最後に発言した人を調べる。→部分更新するかどうかの判断材料
@route("/api/last_talk")
def get_last_talk():
    #トークデータの一覧を取得する
    talk_list = get_talk()
    #トークデータの一番最後の情報をjson形式で返す
    return json.dumps(talk_list[-1])#pythonでよく使うリスト最後を取る方法


#発言時間、発言者、発言内容をCSVに保存する関数
def save_talk(talk_time, username, chat_data):
    #CSVを開く
    with open('./chat_data.csv', 'a') as f:
        #CSVに書き込みを行う
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow([talk_time, username, chat_data])

#ユーザ名、パスワードをCSVに保存する関数　→暗号化等行っていないので改善の余地あり
def save_user_pass(username, password):
    #CSVを開く
    with open('./user_pass.csv', 'a') as f:
        #CSVに書き込みを行う
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow([username, password])

#csvからチャットデータを取得する関数
def get_talk():

    talk_list = []
    #履歴ファイルがない場合は空ファイルを作成する
    if not os.path.exists("./chat_data.csv"):
        open("./chat_data.csv", "w").close()
    #CSVファイルを開く
    with open('./chat_data.csv', 'r') as f:
        #ファイルから一行読み込み
        reader = csv.reader(f)
        #rowは配列として各列のセルの情報を格納してあるので、各々をリストに辞書型としてアペンドする
        for row in reader:
            talk_list.append({
                "talk_time": row[0],
                "username": row[1],
                "chat_data": row[2],
            })
    #読み込んだしたチャットデータを返す
    return talk_list


#csvからユーザ名、パスワードを取得する関数
def get_user_pass():

    user_pass = []
    #履歴ファイルがない場合は空ファイルを作成する
    if not os.path.exists("./user_pass.csv"):
        open("./user_pass.csv", "w").close()
    #CSVファイルを開く
    with open('./user_pass.csv', 'r') as f:
        #ファイルから一行読み込み
        reader = csv.reader(f)
        #rowは配列として各列のセルの情報を格納してあるので、各々をリストに辞書型としてアペンドする
        for row in reader:
            user_pass.append({
                "username": row[0],
                "password": row[1],
            })
    #読み込んだユーザ名、パスワードを返す
    return user_pass

# サーバの起動
run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
