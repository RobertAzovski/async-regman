import asyncio
import os
import json

import aio_pika
import asyncio
import asyncpg

TABLE_NAME = 'appeals'


async def pika_consume(amqp_connection, db_connection) -> None:

    queue_name = "form_data"

    async with amqp_connection.channel() as channel:
        # Will take no more than 10 messages in advance
        await channel.set_qos(prefetch_count=10)

        # Declaring queue
        queue = await channel.declare_queue(queue_name)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    data = json.loads(message.body)
                    data = json.loads(data) # for some reason json decode as string on first call
                    await db_connection.execute('''
                        INSERT INTO appeals VALUES (DEFAULT, $1, $2, $3, $4, $5);
                        ''', *data.values())


async def ensure_db_table(db_connection) -> None:
    await db_connection.execute('''
            CREATE TABLE IF NOT EXISTS appeals (
                id SERIAL NOT NULL PRIMARY KEY,
                firstname text,
                surname text,
                middlename text,
                phone_number text,
                text_message text);
            ''')

async def main():
    amqp_host = os.environ.get('AMQP_HOST')
    amqp_port = os.environ.get('AMQP_PORT')
    amqp_user = os.environ.get('AMQP_USER')
    amqp_password = os.environ.get('AMQP_PASSWORD')

    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT')
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    db_name = os.environ.get('DB_NAME')

    try:
        amqp_connection = await aio_pika.connect_robust(
                                    host=amqp_host,
                                    port=amqp_port,
                                    login=amqp_user,
                                    password=amqp_password)
        db_connection = await asyncpg.connect(host=db_host,
                                port=db_port,
                                user=db_user,
                                password=db_password,
                                database=db_name)
        await ensure_db_table(db_connection)
        await pika_consume(amqp_connection, db_connection)
    finally:
        await amqp_connection.close()
        await db_connection.close()

if __name__ == "__main__":
    asyncio.run(main())