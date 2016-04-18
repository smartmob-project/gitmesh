# -*- coding: utf-8 -*-


def pre_receive(updates):
    for ref, (old, new) in updates.items():
        print('[ECHO] pre-receive %s | %s ==> %s' % (ref, old, new))


def update(ref, old, new):
    print('[ECHO] update %s | %s ==> %s' % (ref, old, new))


def post_receive(updates):
    for ref, (old, new) in updates.items():
        print('[ECHO] post-receive %s | %s ==> %s' % (ref, old, new))


async def post_update(refs):
    for ref in refs:
        print('[ECHO] post-update %s' % (ref,))
