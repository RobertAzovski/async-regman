import asyncio
import os

import aio_pika
from fastapi import FastAPI
from pydantic import BaseModel


async def pika_consume(amqp_connection) -> None:

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
                    print(message.body, flush=True)


async def main():
    amqp_host = os.environ.get('AMQP_HOST')
    amqp_port = os.environ.get('AMQP_PORT')
    amqp_user = os.environ.get('AMQP_USER')
    amqp_password = os.environ.get('AMQP_PASSWORD')

    amqp_connection = await aio_pika.connect_robust(
                                host=amqp_host,
                                port=amqp_port,
                                login=amqp_user,
                                password=amqp_password)

    await pika_consume(amqp_connection)


if __name__ == "__main__":
    asyncio.run(main())