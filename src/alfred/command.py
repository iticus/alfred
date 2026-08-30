"""Created on Dec 22, 2017.

Copyright (C) 2026, Ionut Ticus (iticus), <ticus.ionut@gmail.com>
"""

import asyncio
import getpass

from alfred import appkeys, utils
from alfred.main import make_app


async def create_admin_user() -> None:
    """Create admin user."""
    app = make_app()
    await app[appkeys.database].connect()
    loop = asyncio.get_event_loop()
    name = await loop.run_in_executor(None, input, "name: ")
    username = await loop.run_in_executor(None, input, "Username: ")
    password = getpass.getpass(prompt="Password: ")
    password = utils.make_pw_hash(password)
    query = """INSERT INTO users(name,username,password,level) VALUES($1,$2,$3,$4) RETURNING id"""
    result = await app[appkeys.database].pool.fetch(query, name, username, password, 1)
    if result:
        print("admin account created, don't forget your password")  # noqa: T201
    else:
        print("admin account NOT created, review above messages")  # noqa: T201


async def main() -> None:
    """Create IOLoop and run create_admin_user."""
    await create_admin_user()


if __name__ == "__main__":
    asyncio.run(main())
