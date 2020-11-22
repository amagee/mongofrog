import asyncio
import curses
from typing import List, Optional, Callable

from blessed import Terminal
import motor.motor_asyncio
import urwid


client = None
state = {
    'database': None,
    'collection': None,
}
urwid_loop = None


def main():
    global loop, client, urwid_loop
    client = motor.motor_asyncio.AsyncIOMotorClient(host="localhost")
    loop = asyncio.get_event_loop()
    urwid_loop = urwid.MainLoop(
        urwid.SolidFill(), # Placeholder
        palette=[('reversed', 'standout', '')],
        event_loop=urwid.AsyncioEventLoop(loop=loop),
        unhandled_input=lambda k: asyncio.create_task(handle_input(k)),
    )
    loop.create_task(render())
    urwid_loop.run()


def menu(title: str, choices: List[str], onclick: Optional[Callable]):
    body = [urwid.Text(title), urwid.Divider()]
    for c in choices:
        button = urwid.Button(c)
        if onclick is not None:
            urwid.connect_signal(button, 'click', lambda b, d: asyncio.create_task(onclick(d)), c)
        body.append(urwid.AttrMap(button, None, focus_map='reversed'))
    return urwid.ListBox(urwid.SimpleFocusListWalker(body))


async def select_database(database):
    state['database'] = database
    await render()


async def select_collection(collection):
    state['collection'] = collection
    await render()


async def render():
    if state['collection'] is not None:
        items = await client[state['database']].get_collection(state['collection']).find().to_list(100)
        urwid_loop.widget = menu(
            f"{state['database']} -> {state['collection']}",
            [str(item) for item in items], None
        )
    elif state['database'] is not None:
        collections = await client[state['database']].list_collections()
        urwid_loop.widget = menu(
            state['database'],
            [c['name'] for c in collections], select_collection
        )
    else:
        cursor = await client.list_databases()
        databases = await cursor.to_list(length=999)
        urwid_loop.widget = menu('Databases', [d['name'] for d in databases], select_database)


def exit_program():
    raise urwid.ExitMainLoop()


async def handle_input(key):
    if key == 'backspace':
        if state['collection'] is not None:
            state['collection'] = None
        elif state['database'] is not None:
            state['database'] = None
        await render()
    elif key in ('esc', 'q'):
        exit_program()


if __name__ == "__main__":
    main()
