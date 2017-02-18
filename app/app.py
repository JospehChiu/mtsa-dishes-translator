# -*- coding: utf-8 -*-

from flask import Flask, request, render_template, session, url_for
from celery import Celery
from app.app_celery import make_celery
import json
import urllib.request
app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'very-very-super-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aafood.db'

app.config['CELERY_BROKER_URL']='redis://localhost:6379/14'
app.config['CELERY_RESULT_BACKEND']='redis://localhost:6379/14'
celery = make_celery(app)

from flask_redis import FlaskRedis
app.config['REDIS_URL'] = 'redis://localhost:6379/15'
redis_store = FlaskRedis(app)


@app.route('/')
def index():
    return "OK"


@app.route("/callback", methods=['GET'])
def hello():
    """ webhook 一開始的認證使用 """
    challenge = request.args.get('hub.challenge', '')
    secret = request.args.get('hub.verify_token', '')
    print(challenge)
    print(secret)
    return challenge


from app.bot import Bot
bot = Bot(app)


@celery.task
def celery_handle_message(msg, sender, msgbody):
    """ 背景作業：處理每一個傳進來的訊息 """
    with app.app_context():
        # 先已讀
        bot.intention_bot.bot_sender_action(sender, "mark_seen")

        # 然後處理
        bot.handle_message(msg, sender, msgbody)

@app.route("/callback", methods=['POST'])
def messenge_updates():
    """ 實際 webhook 會呼叫的地方，理論上必須儘快回覆 HTTP 200 """
    data = request.data
    data = json.loads(str(data, 'utf-8'))
    entries = data['entry']
    for entry in entries:
        if 'messaging' in entry:
            messages = entry['messaging']
            for msg in messages:
                if 'message' in msg and 'is_echo' in msg['message']:
                    continue
                if 'sender' in msg and 'message' in msg:
                    sender = msg['sender']['id']
                    msgbody = msg['message']
                    print("%s send a message: %s" %(sender, msgbody))
                    # 這邊使用 Async Task:
                    #   先送到 Redis 去存起來, 然後交給 celery 完成任務
                    #celery_handle_message.delay(msg, sender, msgbody)
                    celery_handle_message(msg,sender,msgbody)

    return "OK"
    
