# pwd module for Windows
# Escaping ':' in pwd is via '\:'
# WARNING md5 is used for crypting!

import collections
import warnings
import os
import md5
from pybase.utils import system

# every my environment params will use this prefix
ENV_PREFIX = "PYBASE_"

HEAD_COMMENT = \
"""# Users database (standard Unix format)
# example:1234:1000:1000:Example user:/:demo0\
"""
User = collections.namedtuple("User", "name, passwd, uid, gid, gecos, dir, shell")

class UniqError(Exception):
    """Occurs when non-unique users are detected"""
    def __init__(self, nonuniq, msg=""):
        self._nonuniq = nonuniq # list of nonuniq usernames (uid, name)
        if msg: msg = msg+"\n"
        Exception.__init__(self, "%sUsers unique constraints violation: %s"%(msg, str(nonuniq)))

class AuthError(Exception):
    """Authentification error: incorrect username, password"""
    pass

def encode_escapes(s):
    """Converts escapes in string to internal (safe) form"""
    return s.replace(r"\:", "ESC_58")

def decode_escapes(s):
    """Decode internal (safe) escapes form"""
    s = s.strip()
    s = s.replace("ESC_58", ':')
    return s

def escape(s):
    """All escaped symbols will be escaped"""
    return s.replace(':', r"\:")

def parse_user_line(line):
    """Parse one line from pwd file and returns User object:
    >>> u = parse_user_line(r'root:1234:0:0:Root user\: Admin:/:c\:/xxx/demo0')
    >>> u.name
    'root'
    >>> u.passwd
    '1234'
    >>> u.gecos
    'Root user: Admin'
    >>> u.shell
    'c:/xxx/demo0'
    """
    if not line:
        return None
    line = encode_escapes(line)
    tpl = [decode_escapes(s) for s in line.split(':')]
    return User._make(tpl)

def user_to_line(user):
    """User() to line:
    >>> u = parse_user_line(r'root:1234:0:0:Root user\: Admin:/:c\:/xxx/demo0')
    >>> u.shell
    'c:/xxx/demo0'
    >>> user_to_line(u) == r'root:1234:0:0:Root user\: Admin:/:c\:/xxx/demo0'
    True
    """
    return ":".join(escape(v) for v in user._asdict().values())

def _nonuniq_users(users):
    """Test list of User for unique, if not then returns list of not unique usernames,
    else []"""
    names = collections.defaultdict(int)
    uids = collections.defaultdict(int)
    for user in users:
        names[user.name] += 1
        uids[user.uid] += 1

    errs = []
    for user in users:
        if names[user.name] > 1 or uids[user.uid] > 1:
            errs.append(user.name)
    return errs

def parse_pwd_file(fileobj):
    """Parse pwd file and returns dict {login:User()}. Instead of filename is possible
    to be any other file-like object. UniqError as warning is possible!
    """
    ret = collections.OrderedDict()
    for line in fileobj:
        line = line.strip()
        if not line.startswith("#"):
            user = parse_user_line(line)
            if user and user.name:
                ret[user.name] = user
    nonuniq = _nonuniq_users(ret.values())
    if nonuniq:
        warnings.warn(unicode(UniqError(nonuniq)))
    return ret

def create_dummy_pwd_file(filename):
    """Create dummy pwd file"""
    with open(filename, "wt") as f:
        f.write(HEAD_COMMENT+"\n")

def crypt_passwd(password):
    """crypt password"""
    if not password:
        return ""
    elif password=="*":
        return "*"
    else:
        m = md5.new(password)
        return m.hexdigest()

def save_pwd_file(filename, users):
    """Save list of User (or dict) to pwd file. UniqError is possible!"""
    if isinstance(users, dict):
        users = users.values()

    nonuniq = _nonuniq_users(users)
    if nonuniq:
        raise UniqError(nonuniq)

    with open(filename, "wt") as f:
        f.write(HEAD_COMMENT+"\n")
        for user in users:
            s = user_to_line(user)
            f.write(s)
            f.write("\n")

def auth(username, password, users):
    """Authenticate by password. users is the list of User or dict returned
    by parse_pwd_file()"""
    if isinstance(users, dict):
        user = users.get(username, None)
    else:
        user = [u for u in users if u.name==username]
        if user: user = user[0]

    if not user:
        # no such user
        return None

    # special passwords
    if not user.passwd:
        # empty password, so not password required
        return user
    elif user.passwd=="*":
        # banned user, any password is incorrect
        return None

    chp = crypt_passwd(password)
    if chp != user.passwd:
        # incorrect password
        return None

    return user

def inituser_env(user, env=None):
    """Initialize environment for user. Also
    to environment will be added env dict"""
    # XXX not sure that's needed: os.environ does not changes
    # XXX in both cases
    _env = dict(os.environ)
    _env.update(env or {})
    home = (ENV_PREFIX + "HOME", user.dir)
    name = (ENV_PREFIX + "USER", user.name)
    shell = (ENV_PREFIX + "SHELL", user.shell)
    _env.update((home, name, shell))
    return _env

def login(username, password, users, env=None):
    """Login user: check password, prepare environment and
    start 'shell'. env is additional dict to update()
    environment dict
    """
    user = auth(username, password, users)
    if user:
        env = inituser_env(user, env=env)
        system(user.shell, env, user.dir)
    else:
        raise AuthError

if __name__ == "__main__":
    import doctest
    doctest.testmod()
    #users = parse_pwd_file(open("../../../../../etc/passwd", "rt"))
    #login("root", "111", users)
