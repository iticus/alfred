"""
Created on Dec 22, 2017

@author: ionut
"""

import getpass
import tornado

import alfred
import utils


@tornado.gen.coroutine
def create_admin_user(ioloop):
    """
    Create IOLoop and run create_admin_user
    :param ioloop: existing ioloop instance
    """
    name = input("Name: ")
    username = input("Username: ")
    password = getpass.getpass(prompt="Password: ")
    app = alfred.make_app(None, ioloop)
    password = utils.make_pwhash(app.config.PW_ALGO, password,
                                 app.config.PW_ITERATIONS)
    data = (name, username, password, 1)
    query = """INSERT INTO users(name,username,password,level)
    VALUES(%s,%s,%s,%s) RETURNING id"""
    result = yield app.database.raw_query(query, data)
    if result:
        print("admin account created, don't forget your password")
    else:
        print("admin account NOT created, review above messages")


def main():
    """Create IOLoop and run create_admin_user"""
    ioloop = tornado.ioloop.IOLoop.instance()
    ioloop.run_sync(lambda: create_admin_user(ioloop))


if __name__ == "__main__":
    main()
