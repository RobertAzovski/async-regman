import asyncio
import logging

import aio_pika

from fastapi import FastAPI
from pydantic import BaseModel


async def pika_consume() -> None:
    logging.basicConfig(level=logging.DEBUG)
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
            return [async message for message in queue_iter]
            
# async with message.process():
#     print(message.body)
#     return message.body


if __name__ == "__main__":
    asyncio.run(main())