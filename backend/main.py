from secrets import token_urlsafe
import os
import asyncio

import aio_pika
import tornado.web
import tornado.options
import tornado.concurrent
import tornado.ioloop
import tornado.escape


AMQP_HOST = os.environ.get('AMQP_HOST')
AMQP_PORT = os.environ.get('AMQP_PORT')
AMQP_USER = os.environ.get('AMQP_USER')
AMQP_PASSWORD = os.environ.get('AMQP_PASSWORD')


async def pika_produce_message(json_data):
    await print(json_data)
    queue_name = "form_data"
    # create connection
    amqp_connection = await connect_robust(
                                host=AMQP_HOST,
                                port=AMQP_PORT,
                                login=AMQP_USER,
                                password=AMQP_PASSWORD)

    async with amqp_connection:
        channel = await amqp_connection.channel()
        queue = await channel.declare_queue(queue_name, auto_delete=True)

        await channel.default_exchange.publish(
            aio_pika.Message(body=json_data),
            routing_key=queue_name,
        )


async def pika_consume_message():
    amqp_connection = await connect_robust(
                                host=AMQP_HOST,
                                port=AMQP_PORT,
                                login=AMQP_USER,
                                password=AMQP_PASSWORD)

    queue_name = "form_data"

    async with amqp_connection:
        # Creating channel
        channel = await amqp_connection.channel()

        # Will take no more than 10 messages in advance
        await channel.set_qos(prefetch_count=10)

        # Declaring queue
        queue = await channel.declare_queue(queue_name, auto_delete=True)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    print(message.body)

                    if queue.name in message.body.decode():
                        break

class ReadMessageHandler(tornado.web.RequestHandler):
    async def get(self):
        self.write(pika_consume_message())

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
        await print('data from form:')
        await print(data)
        json_data = tornado.escape.json_encode(data)
        await pika_produce_message(json_data)

        self.redirect('/success')


async def make_app():

    settings = {
        "cookie_secret": token_urlsafe(),
        "form_url": "/",
        "xsrf_cookies": True,
    }
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/success", ReadMessageHandler),
    ], **settings)


async def main():
    app = await make_app()
    app.listen(8888)
    print(f'Server is listening localhost port - 8888')
    await asyncio.Future()


if __name__ == '__main__':
    asyncio.run(main())
