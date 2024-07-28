import asyncio
import contextlib
from typing import Callable

import aio_pika
import pika

from src import config


@contextlib.contextmanager
def connect_to_channel(queue: str):
    connection = pika.BlockingConnection(pika.ConnectionParameters(config.RABBIT_MQ_HOST, config.RABBIT_MQ_PORT))
    channel = connection.channel()
    channel.queue_declare(queue=queue, durable=True)

    yield channel

    connection.close()


def consume_messages(queue: str, callback: Callable):
    with connect_to_channel(queue) as channel:
        channel.basic_consume(queue=queue, on_message_callback=callback)
        print('Waiting for messages. To exit press CTRL+C')
        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()


async def consume_messages_async(callback: Callable):
    connection = await aio_pika.connect_robust(
        host=config.RABBIT_MQ_HOST, port=config.RABBIT_MQ_PORT
    )

    channel = await connection.channel()
    await channel.set_qos(prefetch_count=100)

    queue = await channel.declare_queue(config.RABBIT_MQ_QUEUE_NAME, durable=True)

    await queue.consume(callback)

    try:
        await asyncio.Future()
    finally:
        await connection.close()
