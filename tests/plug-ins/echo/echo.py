# -*- coding: utf-8 -*-


def pre_receive(target, old_ref, new_ref):
    print('[ECHO] pre-receive')


def update(target, old_ref, new_ref):
    print('[ECHO] update')
