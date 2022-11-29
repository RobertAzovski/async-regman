from secrets import token_urlsafe

import aio_pika
import tornado.web
import tornado.options
import tornado.concurrent
import tornado.ioloop
import tornado.escape


async def pika_produce_message(json_data):
    await print(json_data)
    connection = await aio_pika.connect_robust(
        f"amqp://{AMQP_USER}:{AMQP_PASSWORD}@127.0.0.1/",
    )

    async with connection:
        routing_key = "form_data"
        channel = await connection.channel()

        await channel.default_exchange.publish(
            aio_pika.Message(body=json_data),
            routing_key=routing_key,
        )


async def pika_consume_message():
    logging.basicConfig(level=logging.DEBUG)
    connection = await aio_pika.connect_robust(
        f"amqp://{AMQP_USER}:{AMQP_PASSWORD}@127.0.0.1/",
    )

    queue_name = "form_data"

    async with connection:
        # Creating channel
        channel = await connection.channel()

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


class MainHandler(tornado.web.RequestHandler):
    async def get(self):
        self.render('frontend/templates/index.html')

    async def post(self):
        data = {
            'firstname': self.get_argument('firstname'),
            'surname': self.get_argument('surname'),
            'middlename': self.get_argument('middlename'),
            'phone_number': self.get_argument('phone_number'),
            'text_message': self.get_argument('text_message'),
        }

        json_data = tornado.escape.json_encode(data)
        await pika_produce_message(json_data)

        self.redirect('/')


settings = {
    "cookie_secret": token_urlsafe(),
    "form_url": "/",
    "xsrf_cookies": True,
}
application = tornado.web.Application([
    (r"/", MainHandler),
], **settings)


if __name__ == '__main__':
    app = application
    app.listen(PORTMQ)
    print(f'Server is listening localhost port - {PORTMQ}')
    tornado.ioloop.IOLoop.current().start()
