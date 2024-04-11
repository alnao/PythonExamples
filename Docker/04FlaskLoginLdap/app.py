from functools import wraps
from flask import Flask, request, redirect, url_for, render_template, abort
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from ldap3 import Server, Connection, SUBTREE, SIMPLE

##see 
#	https://flask-login.readthedocs.io/en/latest/
#	https://gist.github.com/lanbugs/40f94d6a7b849dcd0803179e0a7bb137


# LDAP Settings
AD_DOMAIN = "example.local"
LDAP_USER = "adbindlnx" 
SEARCH_BASE = "OU=Users,OU=EXAMPLE,DC=example,DC=local"
LDAP_PASS = "xxxxxx"
LDAP_SERVER = "ldap://server.example.local" # "389"

# Init Flask
app = Flask(__name__)
app.secret_key = "ThisSecretIsVeryWeakDoItBetter"

# Init LoginManager
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


class User(UserMixin):
    """
    The user model
    """
    def __init__(self, username):
        self.id = username
        self.groups = []


def authenticate_ldap(username, password):
    """
    Check authentication of user against AD with LDAP
    :param username: Username
    :param password: Password
    :return: True is authentication is successful, else False
    """
    server = Server(LDAP_SERVER, use_ssl=True)

    try:
        with Connection(server,
                        user=f'{username}',  #user=f'{AD_DOMAIN}\\{username}',
                        password=password,
                        authentication=SIMPLE,
                        check_names=True,
                        raise_exceptions=True) as conn:
            if conn.bind():
#                print("Authentication successful")
                return True
    except Exception as e:
        print(f"LDAP authentication failed: {e}")
    return False


def get_user_groups(username):
    """
    Connect to LDAP and query for all groups
    :param username: Username
    :return: List of group names
    """
    print("get_user_groups ")
    server = Server(LDAP_SERVER, use_ssl=True)
#    print("get_user_groups server")
    try:
        with Connection(server,
                        user=LDAP_USER,
                        password=LDAP_PASS,
                        auto_bind=True) as conn:
#            print("get_user_groups connection ok " + username)
#            search_filter = f'(sAMAccountName={username})'
            search_filter = f'(userPrincipalName={username})'
#            search_filter = "(objectClass=*)"
#            print("get_user_groups filter ok" + SEARCH_BASE )
            conn.search(search_base=SEARCH_BASE,  
                        search_filter=search_filter,
                        attributes=['memberOf'],
                        search_scope=SUBTREE
                        )
#            print("get_user_groups search ok")
#            print(conn.response_to_json())
            if conn.entries:
                user_entry = conn.entries[0]
                group_dns = user_entry.memberOf
#                print(user_entry)
#                print(group_dns)
                group_names = [group.split(',')[0].split('=')[1] for group in group_dns]
                return group_names
    except Exception as e:
        print(f"LDAP get_user_groups: {e}")
    return []


@login_manager.user_loader
def load_user(user_id):
    """
    The user_loader of flask-login, this will load Usermodel and the groups from AD
    :param user_id: Username
    :return: user object
    """
    try:
        user = User(user_id)
        user.groups = get_user_groups(user_id)
        return user
    except Exception as e:
        print(f"load_user error: {e}")
        return None    


def group_required(groups):
    """
    Decorator to check group membership
    :param groups: list of groups which are allowed to see the site
    """
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            for g in groups:
#                print ( g )
#                print ( current_user.groups )
                if current_user.is_authenticated and g in current_user.groups:
                    return func(*args, **kwargs)
            abort(403)
        return decorated_function
    return decorator


@app.route('/')
def entry_point():
    return redirect(url_for('login'))
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page
    """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if authenticate_ldap(username, password):
            user = User(username)
            login_user(user)
            return redirect(url_for('user_panel'))
        else:
            return 'Auth error <a href="login">login</a>'
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """
    Logout page
    """
    logout_user()
    return redirect(url_for('login'))


@app.route('/admin')
@login_required
@group_required(["administrator_group"])
def admin_panel():
    """
    Protected admin panel, only users of group p_admin are allowed to see the page 
    """
    return 'Admin Panel <a href="user">user</a> - <a href="logout">logout</a>'


@app.route('/user')
@login_required
@group_required(["administrator_group", "all_users"])
def user_panel():
    """
    Protected user panel, only users of group p_user and p_admin are allowed to see the page 
    """
    return 'User Panel <a href="admin">Admin</a> - <a href="logout">logout</a>'


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=8001, debug=True)