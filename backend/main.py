from secrets import token_urlsafe
import os
import asyncio
import json

import aio_pika
import tornado.web
import tornado.options
import tornado.concurrent
import tornado.ioloop
import tornado.escape


async def pika_produce_message(json_data, amqp_connection):
    print(json_data, flush=True)
    queue_name = "form_data"

    async with amqp_connection:
        channel = await amqp_connection.channel()
        queue = await channel.declare_queue(queue_name, auto_delete=True)

        json_string = json.dumps(json_data)
        await channel.default_exchange.publish(
            aio_pika.Message(body=json_string.encode()),
            routing_key=queue_name,
        )


class SuccessHandler(tornado.web.RequestHandler):
    async def get(self):
        self.write('Success !!!')


class MainHandler(tornado.web.RequestHandler):
    async def get(self):
        self.render('templates/index.html')

    async def post(self):
        data = {
            'firstname': self.get_argument('firstname'),
            'surname': self.get_argument('surname'),
            'middlename': self.get_argument('middlename'),
            'phone_number': self.get_argument('phone_number'),
            'text_message': self.get_argument('text_message'),
        }
        amqp_connection = self.application.settings["amqp_connection"]
        json_data = tornado.escape.json_encode(data)
        await pika_produce_message(json_data, amqp_connection)

        self.redirect('/success')


async def make_app() -> tornado.web.Application:
    amqp_host = await os.environ.get('AMQP_HOST')
    amqp_port = await os.environ.get('AMQP_PORT')
    amqp_user = await os.environ.get('AMQP_USER')
    amqp_password = await os.environ.get('AMQP_PASSWORD')
    # throw error if amqp details not defined
    if not all([amqp_host, amqp_port, amqp_user, amqp_password]):
        raise NotImplementedError

    amqp_connection = await aio_pika.connect_robust(
                                host=amqp_host,
                                port=amqp_port,
                                login=amqp_user,
                                password=amqp_password)

    channel = await amqp_connection.channel()
    queue = await channel.declare_queue("form_data", auto_delete=True)

    settings = {
        "cookie_secret": token_urlsafe(),
        "form_url": "/",
        "xsrf_cookies": True,
    }
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/success", SuccessHandler),],
        amqp_connection=amqp_connection,
        **settings)


async def main():
    app = await make_app()
    app.listen(8888)
    print(f'Server is listening localhost port - 8888')
    await asyncio.Future()


if __name__ == '__main__':
    asyncio.run(main())
