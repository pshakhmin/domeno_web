import json

from flask import Flask, render_template, request, jsonify
import random

app = Flask(__name__)
users = {}

import pika
import uuid


class ParserRpcClient(object):

    def __init__(self):
        credentials = pika.PlainCredentials('domeno', 'DoMeNo')

        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost', credentials=credentials))

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True)

        self.response = None
        self.corr_id = None

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, req):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange='',
            routing_key='rpc_queue',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=str(req))
        self.connection.process_data_events(time_limit=None)
        return self.response


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chatbot", methods=["POST"])
def chatbot():
    data = request.get_json()
    message = str(data["message"])
    user = data["uuid"]
    print(data, users)
    if user not in users:
        users[user] = {'step': 2, 'domain': ''}

    if users[user]['step'] == 2:
        users[user]['domain'] = message
        users[user]['step'] = 3
        return jsonify({"message": "Вы используете сайт для продажи товаров (оказания услуг)?", 'step': 3})

    if users[user]['step'] == 3:
        if message.lower() == 'нет':
            users[user]['step'] = 4
            return jsonify({
                "message": "Некоммерческое использование товарного знака в домене является законным, "
                           "однако не исключает возможных претензий со стороны правообладателя. "
                           "Консультация со специалистом поможет их избежать, обращайтесь к "
                           "___*гиперссылка на юр. сервис*<br>Хотите продолжить проверку?",
                "step": 4})
        if message.lower() == 'да':
            users[user]['step'] = 5
            return jsonify({
                "message": "Выберите категорию(-ии) товаров или услуг из списка",
                "step": 5
            })

    if users[user]['step'] == 4:
        if message.lower() == 'нет':
            users[user]['step'] = 2
            return jsonify({
                "message": "ну как хотите..",
                "step": 2
            })
        if message.lower() == 'да':
            users[user]['step'] = 5
            return jsonify({
                "message": "Выберите категорию товаров или услуг из списка",
                "step": 5
            })

    if users[user]['step'] == 5:
        users[user]['step'] = 6
        users[user]['category'] = message
        return jsonify({"message": "Выберите подкатегорию товаров или услуг из списка",
                        "step": 6,
                        "category": users[user].get('category')})

    if users[user]['step'] == 6:
        parser_rpc = ParserRpcClient()
        response = json.loads(parser_rpc.call(json.dumps({"query": users[user]['domain'], "mktu": [message]})))
        print(response)
        if len(response) == 0:
            return jsonify({
                "message": "Товарных знаков с таким словом нет. Обезопасьте себя от рисков (запрета использования "
                           "домена или обращения взысканий), зарегистрируйте свой товарный знак. Обратитесь за "
                           "регистрацией к специалистам https://www.hse.ru/ma/dlaw/",
                "step": 7})
        else:
            return jsonify({
                "message": f"Использование домена может нарушать права правообладателя \"{response[0]['owner']}\"."
                           f"Словесное обозначение: {response[0]['words_part']}. Измените домен. "
                           "|Воспользуйтесь сервисом подбора подходящего домена https://www.reg.ru/domain/new/"
                           "|Остались вопросы? Проконсультируйтесь со специалистом https://www.hse.ru/ma/dlaw/",
                "step": 7})
    if users[user]['step'] == 7:
        if message.lower() == 'проверить еще':
            users[user]['step'] = 2
            return jsonify({
                "message": "Для проверки введите домен до точки (без .ru, .com, .org). Пример: вместо cola.cola.ru, "
                           "введите cola.cola",
                "step": 2
            })


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
