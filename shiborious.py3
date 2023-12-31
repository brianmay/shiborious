import web
import string
from random import choice
import datetime
import hashlib
import MySQLdb

from shiborious import settings

urls = (
  '/', 'index'
)


def gen_password(length=16, chars=string.letters + string.digits):
    return ''.join([choice(chars) for i in range(length)])


class index:

    def GET(self):
        # Get Shibboleth attributes
        try:
            email = web.ctx.env['mail']
        except:
            web.header("Content-Type","text/plain; charset=utf-8")
            return "This website requires email. Your IdP is not releasing this attribute to this site. Please talk to your IdP Admin."
        create_date = datetime.datetime.now()
        try:
            full_name = web.ctx.env['displayName']
        except:
            try:
                full_name = web.ctx.env['cn']
            except:
                web.header("Content-Type","text/plain; charset=utf-8")
                return "This website requires either displayName or commonName. Your IdP is not releasing these attribute to this site. Please talk to your IdP Admin."

        if True:
            # Check gitorious database
            conn = MySQLdb.connect (
                host = settings.DB_HOST,
                user = settings.DB_USER,
                passwd = settings.DB_PASSWD,
                db = settings.DB_NAME)
            cursor = conn.cursor()

            # Try to find existing user
            cursor.execute("""SELECT id,login FROM users WHERE email=%s""", (email, ))
            result = cursor.fetchone()
            if result is not None:
                # User found, get details
                id = result[0]
                login = result[1]
            else:
                # User not found, we need to pick a login
                id = None
                login = email.replace('@','').replace('.','')

            result = cursor.fetchone()
            # Paranoia check, if multiple users exist with same email address something has gone terrible wrong. Check
            # for monkeys in the telephone.
            if result is not None:
                web.header("Content-Type","text/plain; charset=utf-8")
                return "Too many gitorious users matched email address!"

            # Create new password for user
            password = gen_password()
            salt = hashlib.sha1("--"+str(create_date)+"--"+login+"--").hexdigest()
            crypted_password = hashlib.sha1("--"+salt+"--"+password+"--").hexdigest()

            # Add user if already exists or update existing user
            if id is None:
                cursor.execute("""SELECT id FROM users WHERE login=%s""", (login,))
                result = cursor.fetchone()
                if result is not None:
                    web.header("Content-Type","text/plain; charset=utf-8")
                    return "Automatically picked login '%s' for new account is already in use" % (login,)

                cursor.execute("""INSERT INTO users (login, email, crypted_password, salt, created_at, updated_at, activated_at, fullname, aasm_state, public_email, wants_email_notifications) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, "terms_accepted", 1, 1)""", (login, email, crypted_password, salt, create_date, create_date, create_date, full_name))
            else:
                cursor.execute("""UPDATE users SET crypted_password=%s, salt=%s, updated_at=%s, fullname=%s WHERE id=%s""", (crypted_password, salt, create_date, full_name, id))

            # Did it work?
            if cursor.rowcount <= 0:
                web.header("Content-Type","text/plain; charset=utf-8")
                return "Cannot add/update userid '%s'"% (id,)

            # Close database connection
            conn.commit()
            cursor.close()
            conn.close()

        # We now have valid login and password for user, redirect to login page
        web.header("Content-Type","text/html; charset=utf-8")
        t = web.template.Template("""$def with (title, body)
<html>
<head>
<title>$title</title>
</head>
<body onload="document.forms[0].submit()">
<noscript>
<p>
<strong>Note:</strong> Since your browser does not support JavaScript,
you must press the Continue button once to proceed.
</p>
</noscript>
<pre>
<h1>Redirecting....</h1>
$body
</pre></body>
</html>
""")


        form_body = """
 <form action="%s" method="post">
        <input id="email" name="email" type="hidden" value="%s"/>
        <input id="password" name="password" type="hidden" value="%s" />
        <input name="commit" type="submit" value="Continue" />
  </form>
                """ % (settings.FORM_URL, email, password)
            
        return t("Shibboleth Login", form_body)
            

application = web.application(urls, globals()).wsgifunc()
#application = web.application(urls, globals())

#if __name__ == "__main__": 
#    application.run()

