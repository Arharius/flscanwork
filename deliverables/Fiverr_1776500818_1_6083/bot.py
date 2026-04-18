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

bot_configuration = BotConfiguration(
    name='ShopBot',
    avatar='http://example.com/avatar.jpg',
    auth_token=os.getenv('VIBER_AUTH_TOKEN')
)
viber = Api(bot_configuration)

@app.route('/', methods=['POST'])
def incoming():
    if not viber.verify_signature(request.get_data(), request.headers.get('X-Viber-Content-Signature')):
        return 'Invalid signature', 403
    
    viber_request = viber.parse_request(request.get_data())
    
    if isinstance(viber_request, ViberConversationStartedRequest):
        return handle_conversation_started(viber_request)
    elif isinstance(viber_request, ViberMessageRequest):
        return handle_message(viber_request)
    elif isinstance(viber_request, ViberSubscribedRequest):
        return handle_subscribed(viber_request)
    
    return jsonify({'status': 'ok'})

def handle_conversation_started(request):
    welcome_message = TextMessage(
        text="Добро пожаловать в наш магазин! Отправьте 'каталог' для просмотра товаров."
    )
    viber.send_messages(request.user.id, [welcome_message])
    return jsonify({'status': 'conversation_started'})

def handle_message(request):
    user_message = request.message.text.lower()
    user_id = request.sender.id
    
    if user_message == 'каталог':
        response = "Каталог товаров:\n1. Товар А - 1000 руб\n2. Товар Б - 1500 руб\nОтправьте номер товара для заказа."
    elif user_message in ['1', '2']:
        response = f"Товар {user_message} добавлен в корзину. Отправьте 'оформить' для создания заказа."
    elif user_message == 'оформить':
        response = "Заказ оформлен! Номер заказа: #12345. Статус доставки будет отправлен вам позже."
    else:
        response = "Не понимаю команду. Доступные команды: 'каталог', '1', '2', 'оформить'"
    
    viber.send_messages(user_id, [TextMessage(text=response)])
    return jsonify({'status': 'message_processed'})

def handle_subscribed(request):
    user_id = request.user.id
    viber.send_messages(user_id, [TextMessage(text="Спасибо за подписку!")])
    return jsonify({'status': 'subscribed'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)