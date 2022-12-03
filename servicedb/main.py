import os
import asyncio

import databases
import aio_pika
import aiohttp
import sqlalchemy
from fastapi import FastAPI
from pydantic import BaseModel


DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_NAME = os.environ.get('DB_NAME')
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
# SQLAlchemy specific code, as with any other app
# DATABASE_URL = "sqlite:///./test.db"

database = databases.Database(DATABASE_URL)

metadata = sqlalchemy.MetaData()

appeals = sqlalchemy.Table(
    "appeals",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("firstname", sqlalchemy.String),
    sqlalchemy.Column("surname", sqlalchemy.String),
    sqlalchemy.Column("middlename", sqlalchemy.String),
    sqlalchemy.Column("phone_number", sqlalchemy.Integer),
    sqlalchemy.Column("text_message", sqlalchemy.String),
)


engine = sqlalchemy.create_engine(
    DATABASE_URL,
)
metadata.create_all(engine)

class Appeal(BaseModel):
    firstname: str
    surname: str
    middlename: str
    phone_number: int
    text_message: str


app = FastAPI()


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.post("/appeal/", response_model=Appeal)
async def create_note(appeal: Appeal):
    query = appeals.insert().values(
        firstname=appeal.firstname,
        surname=appeal.surname,
        middlename=appeal.middlename,
        phone_number=appeal.phone_number,
        text_message=appeal.text_message)
    last_record_id = await database.execute(query)
    return {**appeal.dict(), "id": last_record_id}

async def pika_consume(amqp_connection) -> None:

    queue_name = "form_data"

    async with amqp_connection.channel() as channel:
        # Will take no more than 10 messages in advance
        await channel.set_qos(prefetch_count=10)

        # Declaring queue
        queue = await channel.declare_queue(queue_name)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    async with aiohttp.ClientSession() as session:
                        await session.post('/appeal/', data=message.body)


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