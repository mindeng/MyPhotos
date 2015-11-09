#! /usr/bin/env python

from hashlib import md5
from Crypto.Cipher import AES
from Crypto import Random
import struct

# MUST be multipled by 16
_BUF_SIZE = 1024 * 16

def derive_key_and_iv(password, salt, key_length, iv_length):
    d = d_i = ''
    while len(d) < key_length + iv_length:
        d_i = md5(d_i + password + salt).digest()
        d += d_i
    return d[:key_length], d[key_length:key_length+iv_length]

def encrypt_file(in_file, out_file, password, key_length=32):
    bs = AES.block_size

    # generate random salt
    salt = Random.new().read(bs)
    # save salt
    out_file.write(salt)
    # save key len
    out_file.write(struct.pack('!B', key_length))

    # derive key, iv
    key, iv = derive_key_and_iv(password, salt, key_length, bs)

    finished = False
    cipher = AES.new(key, AES.MODE_CBC, iv)
    while not finished:
        chunk = in_file.read(_BUF_SIZE)
        if len(chunk) == 0 or len(chunk) % bs != 0:
            padding_length = (bs - len(chunk) % bs) or bs
            chunk += padding_length * chr(padding_length)
            finished = True
        out_file.write(cipher.encrypt(chunk))

def decrypt_file(in_file, out_file, password):
    bs = AES.block_size

    # read salt
    salt = in_file.read(bs)
    # read key len
    key_length = struct.unpack('!B', in_file.read(struct.calcsize('B')))[0]
    if key_length % 16 != 0:
        return False

    # derive key, iv
    key, iv = derive_key_and_iv(password, salt, key_length, bs)

    cipher = AES.new(key, AES.MODE_CBC, iv)
    next_chunk = ''
    finished = False
    while not finished:
        chunk, next_chunk = next_chunk, cipher.decrypt(in_file.read(_BUF_SIZE))
        if len(next_chunk) == 0:
            padding_length = ord(chunk[-1])
            chunk = chunk[:-padding_length]
            finished = True
        out_file.write(chunk)

    return True

import StringIO
import base64
def encrypt_str(s, password, key_length=32):
    fin = StringIO.StringIO(s)
    fout = StringIO.StringIO()
    encrypt_file(fin, fout, password, key_length)
    return base64.b64encode(fout.getvalue())
def decrypt_str(s, password):
    s = base64.b64decode(s)
    fin = StringIO.StringIO(s)
    fout = StringIO.StringIO()
    ret = decrypt_file(fin, fout, password)
    if ret:
        return fout.getvalue()
    else:
        return None

def password_input(prompt='Password: '):
    import getpass
    password = None
    while not password:
        password = getpass.getpass(prompt)
    return password

def user_input_password(double_check=True):
    if not double_check:
        return password_input()
    while True:
        p1 = password_input()
        p2 = password_input('Retype password: ')
        if p1 != p2:
            print 'Passwords do not match'
        else:
            return p1


if __name__ == '__main__':
    import argparse, os

    parser = argparse.ArgumentParser(description='AES encrypt tool.')
    parser.add_argument('src')
    parser.add_argument('-o', '--output', dest='dst')
    parser.add_argument('-p', '--password', dest='password')
    parser.add_argument('--key-len', type=int, default=32)
    parser.add_argument('-d', '--decrypt', dest='decrypt_flag', action='store_const', const=True, help='decrypt')

    args = parser.parse_args()
    print args

    src = args.src
    dst = args.dst
    password = args.password
    key_length = args.key_len
    decrypt_flag = args.decrypt_flag

    if dst:
        if not os.path.isfile(src):
            print 'File not exists: %s' % src
            exit(1)

        if os.path.isfile(dst):
            choice = raw_input('File %s exists, overwrite? (y/n) ' % dst)
            if choice != 'y':
                exit(1)

    if not password:
        password = user_input_password(not decrypt_flag)

    def do_file():
        with open(src, 'rb') as in_file, open(dst, 'wb') as out_file:
            if decrypt_flag:
                ret = decrypt_file(in_file, out_file, password)
                if not ret:
                    print 'Decrpt failed!'
            else:
                encrypt_file(in_file, out_file, password, key_length)

    if src and dst:
        do_file()
    else:
        if decrypt_flag:
            print decrypt_str(args.src, password)
        else:
            print encrypt_str(args.src, password, key_length)
