import asyncio
import datetime
import json
import os

import tornado.web
from tornado.httputil import HTTPServerRequest
import aio_pika
from aio_pika import Message, connect_robust

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")

class Base:
    QUEUE: asyncio.Queue

class SubscriberHandler(tornado.web.RequestHandler, Base):
    async def get(self) -> None:
        message = await self.QUEUE.get()
        await self.finish(message.body)

class PublisherHandler(tornado.web.RequestHandler):
    async def get(self, *args, **kwargs) -> None:
        r: HTTPServerRequest = self.request
        now = datetime.datetime.now()
        data = {
            'method' : r.method,
            'address' : r.remote_ip,
            'date' : f'{now}',
        }
        serialized = json.dumps(data)
        print(serialized)
        # dump data back to client for debug
        self.write(data)
        self.set_header('Content-Type', 'application/json')

        # actual amqp publish
        connection = self.application.settings["amqp_connection"]
        channel = await connection.channel()

        try:
            await channel.default_exchange.publish(
                Message(body=serialized.encode()),
                routing_key="test",
            )
        finally:
            await channel.close()

        await self.finish()

async def make_app() -> tornado.web.Application:
    amqp_host = os.environ.get('AMQP_HOST')
    amqp_port = os.environ.get('AMQP_PORT')
    amqp_user = os.environ.get('AMQP_USER')
    amqp_password = os.environ.get('AMQP_PASSWORD')
    if not all([amqp_host, amqp_port, amqp_user, amqp_password]):
        raise NotImplentedError
    amqp_connection = await connect_robust(f'amqp://{amqp_user}:{amqp_password}@{amqp_host}:{amqp_port}')

    channel = await amqp_connection.channel()
    queue = await channel.declare_queue("test", auto_delete=True)
    Base.QUEUE = asyncio.Queue()

    await queue.consume(Base.QUEUE.put, no_ack=True)

    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/api/publish", PublisherHandler),
        (r"/api/subscribe", SubscriberHandler)],
        amqp_connection=amqp_connection)

async def main():
    app = await make_app()
    app.listen(8888)
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())