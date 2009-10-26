import web
import string
from random import choice
import datetime
import hashlib
import MySQLdb

import settings

urls = (
  '/', 'index'
)


def gen_password(length=16, chars=string.letters + string.digits):
    return ''.join([choice(chars) for i in range(length)])


class index:

    def GET(self):
        f = open(settings.USER_FILE, 'r')
        users = f.readlines()
        f.close()
        try:
            email = web.ctx.env['mail']
        except:
            return "This website requires email. Your IdP is not releasing this attribute to this site. Please Talk to your IdP Admin."
        login = email.replace('@','').replace('.','')
        create_date = datetime.datetime.now()
        try:
            full_name = web.ctx.env['displayName']
        except:
            try:
                full_name = web.ctx.env['cn']
            except:
                return "This website requires either displayName or commonName. Your IdP is not releasing these attribute to this site. Please Talk to your IdP Admin."

        found = False

        for u in users:
            if u.startswith(email):
                found = True
                password = u.split(':')[1].replace('\n','')
                
        if not found:
            password = gen_password()
            
            f = open(settings.USER_FILE, 'a')
            f.write("%s:%s\n" % (email, password))
            f.close()
            
            salt = hashlib.sha1("--"+str(create_date)+"--"+login+"--").hexdigest()
            crypted_password = hashlib.sha1("--"+salt+"--"+password+"--").hexdigest()
       
            SQL = """INSERT INTO users (login, email, crypted_password, salt, created_at, updated_at, activated_at, fullname, aasm_state, public_email, wants_email_notifications) VALUES ("%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "terms_accepted", 1, 1)""" % (login, email, crypted_password, salt, create_date, create_date, create_date, full_name)

            conn = MySQLdb.connect (
                host = settings.DB_HOST,
                user = settings.DB_USER,
                passwd = settings.DB_PASSWD,
                db = settings.DB_NAME)

            cursor = conn.cursor()
            cursor.execute(SQL)
            conn.commit()
            cursor.close()
            conn.close()
        
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
 <form action="https://code.arcs.org.au/gitorious/sessions" method="post">
        <input id="email" name="email" type="hidden" value="%s"/>
        <input id="password" name="password" type="hidden" value="%s" />
        <input name="commit" type="submit" value="Continue" />
  </form>
                """ % (email, password)
            
        return t("Shibboleth Login", form_body)
            

application = web.application(urls, globals()).wsgifunc()
#application = web.application(urls, globals())

#if __name__ == "__main__": 
#    application.run()

