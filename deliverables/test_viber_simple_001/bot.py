#!/usr/bin/env python3
import os
from flask import Flask, request, jsonify
from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.messages.text_message import TextMessage
from viberbot.api.viber_requests import ViberConversationStartedRequest
from viberbot.api.viber_requests import ViberMessageRequest
from viberbot.api.viber_requests import ViberSubscribedRequest
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

auth_token = os.getenv('VIBER_AUTH_TOKEN')
if not auth_token:
    raise ValueError("VIBER_AUTH_TOKEN not set in environment")

bot_configuration = BotConfiguration(
    name='EchoBot',
    avatar='',
    auth_token=auth_token
)
viber = Api(bot_configuration)

@app.route('/', methods=['POST'])
def incoming():
    if not viber.verify_signature(request.get_data(), request.headers.get('X-Viber-Content-Signature')):
        return 'Invalid signature', 403

    viber_request = viber.parse_request(request.get_data())
    if isinstance(viber_request, ViberConversationStartedRequest):
        response_message = TextMessage(text="Hello! I'm an echo bot. Send me any message and I'll repeat it.")
        viber.send_messages(viber_request.user.id, [response_message])
    elif isinstance(viber_request, ViberMessageRequest):
        echo_message = TextMessage(text=viber_request.message.text)
        viber.send_messages(viber_request.sender.id, [echo_message])
    elif isinstance(viber_request, ViberSubscribedRequest):
        viber.send_messages(viber_request.user.id, [TextMessage(text="Thanks for subscribing!")])
    return jsonify({})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)