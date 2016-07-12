import sys

def log(s):
    print encode_text(s)
    sys.stdout.flush()

def decode_text(text):
    ret = text
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

def encode_text(text):
    if type(text) == type(u''):
        return text.encode('utf-8')
    return text