import logging

import asyncpg

log = logging.getLogger('aiogram')


async def create_conn(host: str, user: str, password: str,
                      database: str, create_table: bool = False) -> asyncpg.connection.Connection:
    conn = await asyncpg.connect(user=user, password=password,
                                 database=database, host=host)

    log.info(f'Соединение с базой данных {database} успешно установлено.')

    if create_table:
        await conn.execute('''CREATE TABLE warn (
                id    SERIAL PRIMARY KEY,
                chat_id    BIGINT,
                user_id    BIGINT,
                warn_count smallint)''')

        log.info(f'Таблицы успешно созданы в базе данных {database}.')
    return conn


async def gen_prepared_query(conn: asyncpg.connection.Connection) -> dict:
    prepared_query = {
        'warn_insert': await conn.prepare('INSERT INTO warn(chat_id, user_id, warn_count) VALUES($1, $2, 1)'''),
        'warn_update': await conn.prepare('UPDATE warn SET warn_count=warn_count+1 WHERE chat_id=$1 AND user_id=$2'),
        'warn_select': await conn.prepare('SELECT chat_id, user_id, warn_count FROM warn WHERE chat_id=$1 AND user_id=$2'),
        'get_warn_count': await conn.prepare('SELECT warn_count FROM warn WHERE chat_id=$1 AND user_id=$2'),
        'warn_delete': await conn.prepare('UPDATE warn SET warn_count=warn_count-1 WHERE chat_id=$1 AND user_id=$2'),
        'warns_delete': await conn.prepare('DELETE FROM warn WHERE chat_id=$1 AND user_id=$2')
    }
    return prepared_query
