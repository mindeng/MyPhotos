import sys

def log(s):
    print s
    sys.stdout.flush()

def decode_text(text):
    ret = None
    try:
        try:
            if type(text) == type(''):
                ret = text.decode('utf-8')
        except UnicodeDecodeError, e:
            ret = text.decode('gb18030')
    except UnicodeDecodeError, e:
        log('Failed to decode %s' % text)
        log(e)
    return ret
