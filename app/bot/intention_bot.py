import json
import urllib.request
import urllib.parse
from app.models import db, Term 
from html.parser import HTMLParser
from google import search, get_page
from bs4 import BeautifulSoup
from datetime import datetime
from app.secrets import PAGE_TOKEN
from app.bot.constants import *
from app.bot.reply_generator import ReplyGenerator

class IntentionBot:
    def __init__(self):
        self.reply_gen = ReplyGenerator()

    def handle_message(self, msg, sender, state, msgbody):
        raise Exception("Not Implemented!")

    def bot_sendAPI(self, data):
        token = PAGE_TOKEN
        url = "https://graph.facebook.com/v2.8/me/messages?access_token=" + token
        try:
            req = urllib.request.Request(url, data, {'Content-Type': 'application/json'})
            f = urllib.request.urlopen(req)
            response = f.read()
            print(response)
            f.close()
        except Exception as e:
            print(e)

    def bot_sender_action(self, recipient_id, action):
        data = json.dumps({
            "recipient": {
                "id": str(recipient_id)
            },
            "sender_action": action
            }).encode('utf8')
        self.bot_sendAPI(data)

    def bot_send_message(self, recipient_id, msg):
        data = json.dumps({
            "recipient": {
                "id": str(recipient_id)
            },
            "message": msg
            }).encode('utf8')
        self.bot_sendAPI(data)



import enchant
import mafan
class En2ZhTwIntentionBot(IntentionBot):
    def __init__(self):
        super().__init__()
    
    def ask_google_en_to_zh(self, s):
        q = s + " wikipedia 中文"
        result = search(q, lang="zh", pause=1.0)
        cnt = 0
        for x in result:
            cnt += 1
            if cnt >= 10:
                break
            if 'wikipedia' in x:
                x = urllib.parse.unquote(x)
                x = x.split('/')[-1]
                if mafan.text.is_traditional(x):
                    return x
                if mafan.text.is_simplified(x):
                    url = "http://zh.wikipedia.org/zh-tw/" + urllib.parse.quote_plus(x)
                    print(url)
                    try:
                        w = get_page(url)
                    except:
                        continue
                    soup = BeautifulSoup(w, 'lxml')
                    x = soup.title.string
                    x = x.strip().split(' ')[0]
                    if '維基百科' not in x:
                        return x
        return None


    def en_to_zh(self, s):
        s = s.lower().strip()
        q = Term.query.filter_by(english=s).order_by(Term.hit_counts.desc()).first()

        if q is None:
            translated = self.ask_google_en_to_zh(s)
            return translated
        print("search DB: %s <=> %s [%d]" % (q.english, q.chinese, q.hit_counts))
        return q.chinese

    def handle_message(self, msg, sender, state, msgbody):
        """ 處理英翻中的超辛苦流程，state 的變化應該要寫成筆記之類的... """

        payload = None
        if 'quick_reply' in msgbody and 'payload' in msgbody['quick_reply']:
            payload = msgbody['quick_reply']['payload']

        # 首先判斷是否為取消
        if payload == TMT_CANCEL:
            state.set_status('new')
            return

        # 判斷是否為「我要校正」的選項
        if payload == TMT_FIX_TRANSLATION:
            state.set_status(STATE_WAIT_FOR_FIX_CHINESE)
            # TODO: Get Similars as quick replies
            self.bot_send_message(sender, { "text": "請輸入 \"%s\" 對應的正確中文～" % state.get_q() })
            return

        # 如果是確認更新資料庫
        if payload == TMT_CONFIRM_TRANSLATION:
            q = Term.query.filter_by(english=state.get_english(), chinese=state.get_chinese()).first()
            if q is None:
                q = Term(english=state.get_english(), chinese=state.get_chinese(), hit_counts=1)
                db.session.add(q)
            else:
                q.hit_counts += 1
            print("update DB: %s <=> %s [%d]" % (q.english, q.chinese, q.hit_counts))
            db.session.commit()
            self.bot_send_message(sender, self.reply_gen.sticker('thank you'))
            return

        # 如果是更新 FIX
        if state.get_status() == STATE_WAIT_FOR_FIX_CHINESE:
            if 'text' in msgbody:
                state.set_status(STATE_En2ZhTw_IS_CALLED)
                msgtext = msgbody['text'].strip()
                state.set_chinese(msgtext)
                self.bot_send_message(sender, self.reply_gen.translated_string("「" + msgtext + "」這樣對嗎？"))
            else:
                state.set_status('new')
                self.bot_send_message(sender, { "text": "已取消 ：）" })
            return


        # 如果是一般詢問
        if 'text' in msgbody:
            msgtext = msgbody['text']

            state.set_status(STATE_En2ZhTw_IS_CALLED)
            state.set_q(msgtext)

            # 找出翻譯內容
            tr = self.en_to_zh(msgtext)
            if tr is None:
                self.bot_send_message(sender, { "text": "搜尋近似詞中，請耐心等候..." })
                self.bot_sender_action(sender, "typing_on")
                d = enchant.Dict("en_US")
                suggested = d.suggest(msgtext.strip().lower())
                for term in suggested:
                    tr = self.en_to_zh(term)
                    if tr is not None:
                        break
            if tr is None:
                tr = "翻譯失敗"
            
            state.set_english(msgtext.strip().lower())
            state.set_chinese(tr)
            self.bot_send_message(sender, self.reply_gen.translated_string(tr))
            return

        # TODO: 其他情形 -> 圖片? 按讚?
        self.bot_send_message(sender, { "text": "很抱歉，這個功能林北還做不出來 ^_<" })
        return


class GreetingIntentionBot(IntentionBot):
    def __init__(self):
        super().__init__()

    def handle_message(self, msg, sender, state, msgbody):
        pass


