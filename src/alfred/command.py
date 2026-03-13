"""
Created on Dec 22, 2017

@author: ionut
"""

import asyncio
import getpass

from alfred import appkeys
from alfred import utils
from alfred.main import make_app


async def create_admin_user():
    """
    Create admin user.
    """
    app = make_app()
    await app[appkeys.database].connect()
    name = input("Name: ")
    username = input("Username: ")
    password = getpass.getpass(prompt="Password: ")
    password = utils.make_pw_hash(password)
    query = """INSERT INTO users(name,username,password,level) VALUES($1,$2,$3,$4) RETURNING id"""
    result = await app[appkeys.database].pool.fetch(query, name, username, password, 1)
    if result:
        print("admin account created, don't forget your password")
    else:
        print("admin account NOT created, review above messages")


async def main():
    """Create IOLoop and run create_admin_user"""
    await create_admin_user()


if __name__ == "__main__":
    asyncio.run(main())
