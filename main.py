from datetime import timedelta
from flask import *
import boto3, requests
import sqlite3, hashlib, os
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, text
import key_config as keys

app = Flask(__name__)
app.secret_key = 'random string'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = set(['jpeg', 'jpg', 'png', 'gif'])

s3 = boto3.client('s3',
                  aws_access_key_id = keys.aws_access_key_id,
                  aws_secret_access_key=keys.aws_secret_access_key,
                  aws_session_token=keys.aws_session_token
                 )

BUCKET_NAME = 'is458'

engine = create_engine('mysql+mysqldb://cme_database:ilovecme@cme-database.cpufpabpntvq.us-east-1.rds.amazonaws.com:3306/cme_database')

def getLoginDetails():
    with engine.connect() as conn:
        # cur = conn.cursor()
        if 'email' not in session:
            loggedIn = False
            firstName = ''
            noOfItems = 0
        else:
            loggedIn = True
            conn.execute("SELECT userId, firstName FROM users WHERE email = ?", (session['email'], ))
            userId, firstName = conn.fetchone()
            conn.execute("SELECT count(productId) FROM kart WHERE userId = ?", (userId, ))
            noOfItems = conn.fetchone()[0]
    conn.close()
    return (loggedIn, firstName, noOfItems)

@app.route("/")
def root():
    loggedIn, firstName, noOfItems = getLoginDetails()
    with engine.connect() as conn:
        categoryData = conn.execute("SELECT * from categories")
        productDataRaw = conn.execute(text("SELECT * from products"))
        productData = []
        for productRaw in productDataRaw:
            details = []
            details.append(productRaw[0])
            details.append(productRaw[1])
            details.append(productRaw[2])
            details.append(productRaw[3])
            if productRaw[4] != None:
                imageURL = s3.generate_presigned_url('get_object',
                                                    Params={'Bucket': BUCKET_NAME,
                                                            'Key': productRaw[4]},
                                                    ExpiresIn=0)
                details.append(imageURL)
            else:
                details.append("https://images.fastcompany.net/image/upload/w_596,c_limit,q_auto:best,f_auto/fc/3034007-inline-i-applelogo.jpg")
            details.append(productRaw[5])
            productData.append(details)

        print(productData[-1])
        return render_template('home.html', productData=productData, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems, categoryData=categoryData)
    
@app.route("/add")
def admin():
    with engine.connect() as conn:
        categories = conn.execute("SELECT categoryId, name FROM categories")
        
    return render_template('add.html', categories=categories)

@app.route("/addItem", methods=["GET", "POST"])
def addItem():
    if request.method == "POST":
        name = request.form['name']
        price = int(request.form['price'])
        description = request.form['description']
        stock = int(request.form['stock'])
        categoryId = int(request.form['category'])

        # #Uploading image procedure
        image = request.files['image']
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)

            # might need to remove this, adds file to the source code
            # image.save(filename)

            # s3.upload_file(
            #     filename, BUCKET_NAME, filename
            # )
            with engine.connect() as conn:
                try:
                    conn.execute(text(f"INSERT INTO cme_database.products(productId, name, price, description, image, stock, categoryId) VALUES (4, '{name}', {price}, '{description}', '{filename}', {stock}, {categoryId})"))
                    msg="added successfully"
                except:
                    msg="error occurred"
            conn.close()
        else:
            msg = "error occurred, invalid file type"       
                
        print(msg)
        return redirect(url_for('root'))

@app.route("/remove")
def remove():
    with engine.connect() as conn:
        data = conn.execute('SELECT productId, name, price, description, image, stock FROM products')
    conn.close()
    return render_template('remove.html', data=data)

@app.route("/removeItem")
def removeItem():
    productId = request.args.get('productId')
    with engine.connect() as conn:
        try:
            conn.execute(f'DELETE FROM cme_database.products WHERE productID = {productId}')
            msg = "Deleted successfully"
        except:
            msg = "Error occurred"
    conn.close()
    print(msg)
    return redirect(url_for('root'))

@app.route("/displayCategory")
def displayCategory():
        loggedIn, firstName, noOfItems = getLoginDetails()
        categoryId = request.args.get("categoryId")
        with engine.connect() as conn:
            data = conn.execute(f"SELECT products.productId, products.name, products.price, products.image, categories.name FROM cme_database.products, cme_database.categories WHERE products.categoryId = categories.categoryId AND categories.categoryId = {categoryId}")
            productData = conn.execute(f"SELECT * from products where categoryId={categoryId}")
        conn.close()
        categoryName = data.all()[0][4]
        print(data.all())
        

        return render_template('displayCategory.html', productData=productData, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems, categoryName=categoryName)

# yet to test
# @app.route("/account/profile")
# def profileHome():
#     if 'email' not in session:
#         return redirect(url_for('root'))
#     loggedIn, firstName, noOfItems = getLoginDetails()
#     return render_template("profileHome.html", loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

# yet to test
@app.route("/account/profile/edit")
# def editProfile():
#     if 'email' not in session:
#         return redirect(url_for('root'))
#     loggedIn, firstName, noOfItems = getLoginDetails()
#     with engine.connect() as conn:
#         profileData = conn.execute(f"SELECT userId, email, firstName, lastName, address1, address2, zipcode, city, state, country, phone FROM users WHERE email = {session['email']}")
#     conn.close()
#     return render_template("editProfile.html", profileData=profileData, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

# yet to test, dn to do
# @app.route("/account/profile/changePassword", methods=["GET", "POST"])
# def changePassword():
#     if 'email' not in session:
#         return redirect(url_for('loginForm'))
#     if request.method == "POST":
#         oldPassword = request.form['oldpassword']
#         oldPassword = hashlib.md5(oldPassword.encode()).hexdigest()
#         newPassword = request.form['newpassword']
#         newPassword = hashlib.md5(newPassword.encode()).hexdigest()
#         with sqlite3.connect('database.db') as conn:
#             cur = conn.cursor()
#             cur.execute("SELECT userId, password FROM users WHERE email = ?", (session['email'], ))
#             userId, password = cur.fetchone()
#             if (password == oldPassword):
#                 try:
#                     cur.execute("UPDATE users SET password = ? WHERE userId = ?", (newPassword, userId))
#                     conn.commit()
#                     msg="Changed successfully"
#                 except:
#                     conn.rollback()
#                     msg = "Failed"
#                 return render_template("changePassword.html", msg=msg)
#             else:
#                 msg = "Wrong password"
#         conn.close()
#         return render_template("changePassword.html", msg=msg)
#     else:
#         return render_template("changePassword.html")

# yet to test, dn to do
# @app.route("/updateProfile", methods=["GET", "POST"])
# def updateProfile():
#     if request.method == 'POST':
#         email = request.form['email']
#         firstName = request.form['firstName']
#         lastName = request.form['lastName']
#         address1 = request.form['address1']
#         address2 = request.form['address2']
#         zipcode = request.form['zipcode']
#         city = request.form['city']
#         state = request.form['state']
#         country = request.form['country']
#         phone = request.form['phone']
#         with sqlite3.connect('database.db') as con:
#                 try:
#                     cur = con.cursor()
#                     cur.execute('UPDATE users SET firstName = ?, lastName = ?, address1 = ?, address2 = ?, zipcode = ?, city = ?, state = ?, country = ?, phone = ? WHERE email = ?', (firstName, lastName, address1, address2, zipcode, city, state, country, phone, email))

#                     con.commit()
#                     msg = "Saved Successfully"
#                 except:
#                     con.rollback()
#                     msg = "Error occured"
#         con.close()
#         return redirect(url_for('editProfile'))

@app.route("/loginForm")
def loginForm():
    if 'email' in session:
        return redirect(url_for('root'))
    else:
        return render_template('login.html', error='')

# yet to test, replace with amplify
# @app.route("/login", methods = ['POST', 'GET'])
# def login():
#     if request.method == 'POST':
#         email = request.form['email']
#         password = request.form['password']
#         if is_valid(email, password):
#             session['email'] = email
#             return redirect(url_for('root'))
#         else:
#             error = 'Invalid UserId / Password'
#             return render_template('login.html', error=error)

@app.route("/productDescription")
def productDescription():
    loggedIn, firstName, noOfItems = getLoginDetails()
    productId = request.args.get('productId')
    # eventually dn this if condition, just for testing so the route doesnt bug out
    if productId == None:
        productId = 1
    with engine.connect() as conn:
        productData = conn.execute(f'SELECT productId, name, price, description, image, stock FROM products WHERE productId = {productId}')
        productData = productData.all()[0]
    conn.close()
    return render_template("productDescription.html", data=productData, loggedIn = loggedIn, firstName = firstName, noOfItems = noOfItems)

# yet to test
@app.route("/addToCart")
def addToCart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    else:
        productId = int(request.args.get('productId'))
        # eventually dn this if condition, just for testing so the route doesnt bug out
        if productId == None:
            productId = 1
        with engine.connect() as conn:
            userId = conn.execute("SELECT userId FROM users WHERE email = ?", (session['email'], ))
            userId = userId.all()[0]
            try:
                conn.execute(f"INSERT INTO kart (userId, productId) VALUES ({userId}, {productId})")
                conn.commit()
                msg = "Added successfully"
            except:
                msg = "Error occurred"
        conn.close()
        return redirect(url_for('root'))

# yet to test
@app.route("/cart")
def cart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    loggedIn, firstName, noOfItems = getLoginDetails()
    email = session['email']
    with engine.connect() as conn:
        userId = conn.execute(f"SELECT userId FROM users WHERE email = '{email}'")
        userId = userId.add()[0]
        conn.execute(f"SELECT products.productId, products.name, products.price, products.image FROM cme_database.products, cme_database.kart WHERE products.productId = kart.productId AND kart.userId = {userId}")
        products = conn.fetchall()
    totalPrice = 0
    for row in products:
        totalPrice += row[2]
    return render_template("cart.html", products = products, totalPrice=totalPrice, loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

# yet to test
@app.route("/removeFromCart")
def removeFromCart():
    if 'email' not in session:
        return redirect(url_for('loginForm'))
    email = session['email']
    productId = int(request.args.get('productId'))
    # eventually dn this if condition, just for testing so the route doesnt bug out
    if productId == None:
        productId = 1
    with engine.connect() as conn:
        userId = conn.execute(f"SELECT userId FROM users WHERE email = '{email}'")
        userId = userId.all()[0]
        try:
            conn.execute("DELETE FROM kart WHERE userId = ? AND productId = ?", (userId, productId))
            conn.commit()
            msg = "removed successfully"
        except:
            msg = "error occurred"
    conn.close()
    return redirect(url_for('root'))

@app.route("/logout")
def logout():
    session.pop('email', None)
    return redirect(url_for('root'))

# def is_valid(email, password):
#     conn = engine.connect()
#     conn.execute('SELECT email, password FROM users')
#     data = conn.fetchall()
#     for row in data:
#         if row[0] == email and row[1] == hashlib.md5(password.encode()).hexdigest():
#             return True
#     return False

# replace with amplify
# @app.route("/register", methods = ['GET', 'POST'])
# def register():
#     if request.method == 'POST':
#         #Parse form data    
#         password = request.form['password']
#         email = request.form['email']
#         firstName = request.form['firstName']
#         lastName = request.form['lastName']
#         address1 = request.form['address1']
#         address2 = request.form['address2']
#         zipcode = request.form['zipcode']
#         city = request.form['city']
#         state = request.form['state']
#         country = request.form['country']
#         phone = request.form['phone']

#         with sqlite3.connect('database.db') as con:
#             try:
#                 cur = con.cursor()
#                 cur.execute('INSERT INTO users (password, email, firstName, lastName, address1, address2, zipcode, city, state, country, phone) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (hashlib.md5(password.encode()).hexdigest(), email, firstName, lastName, address1, address2, zipcode, city, state, country, phone))

#                 con.commit()

#                 msg = "Registered Successfully"
#             except:
#                 con.rollback()
#                 msg = "Error occured"
#         con.close()
#         return render_template("login.html", error=msg)

# replace with amplify
# @app.route("/registerationForm")
# def registrationForm():
#     return render_template("register.html")

def allowed_file(filename):
    return '.' in filename and \
            filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

# def parse(data):
#     ans = []
#     i = 0
#     while i < len(data):
#         curr = []
#         for j in range(7):
#             if i >= len(data):
#                 break
#             curr.append(data[i])
#             i += 1
#         ans.append(curr)
#     return ans

if __name__ == '__main__':
    app.run(debug=True)
