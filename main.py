from datetime import timedelta
from flask import *
import boto3, requests
import sqlite3, hashlib, os
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, text
import key_config as keys
from secretsManager import get_secret

app = Flask(__name__)
app.secret_key = "random string"
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = set(["jpeg", "jpg", "png", "gif"])

s3_secrets = get_secret("S3_CME_Credentials")
ses_secrets = get_secret("SES_CME_Credentials")

s3 = boto3.client(
    "s3",
    aws_access_key_id=s3_secrets["access_key"],
    aws_secret_access_key=s3_secrets["secret_access_key"],
)

ses = boto3.client(
    "ses",
    region_name="us-east-1",
    aws_access_key_id=ses_secrets["access_id"],
    aws_secret_access_key=ses_secrets["access_secret"],
)

BUCKET_NAME = "keithprojectbucket"

# engine = create_engine('mysql+mysqldb://cme_database:ilovecme@cme-database.cpufpabpntvq.us-east-1.rds.amazonaws.com:3306/cme_database')
secrets_dict = get_secret("RDS_MYSQL_CME_Credentials")
engine = create_engine(
    f"mysql+mysqldb://{secrets_dict['username']}:{secrets_dict['password']}@{secrets_dict['host']}:{secrets_dict['port']}/{secrets_dict['database']}"
)


def getLoginDetails():
    with engine.connect() as conn:
        # cur = conn.cursor()
        if "email" not in session:
            loggedIn = False
            firstName = ""
            noOfItems = 0
        else:
            loggedIn = True
            user = conn.execute(
                f"SELECT userId, firstName FROM users WHERE email = '{session['email']}'"
            )
            userformatted = user.all()[0]
            userId = userformatted[0]
            firstName = userformatted[1]
            products = conn.execute(
                f"SELECT count(productId) FROM kart WHERE userId = '{userId}'"
            )
            noOfItems = products.all()[0][0]
            # noOfItems = 0
    conn.close()
    return (loggedIn, firstName, noOfItems)


def sendEmail(des, content):
    response = ses.send_email(
        Source="keithtan.2019@scis.smu.edu.sg",
        Destination={"ToAddresses": [str(des)]},
        Message={
            "Subject": {
                "Data": content["subject"],
            },
            "Body": {
                "Text": {
                    "Data": content["body"],
                },
            },
        },
    )
    print(response)


@app.route("/")
def root():
    loggedIn, firstName, noOfItems = getLoginDetails()
    with engine.connect() as conn:
        categoryData = conn.execute("SELECT * from categories")
        productData = conn.execute(text("SELECT * from products"))
        return render_template(
            "home.html",
            productData=productData,
            loggedIn=loggedIn,
            firstName=firstName,
            noOfItems=noOfItems,
            categoryData=categoryData,
        )


@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form["searchQuery"]
    # for key,value in request.form:
    #     print(key, ": ", value)
    with engine.connect() as conn:
        productData = conn.execute(
            f"SELECT * FROM cme_database.products WHERE name = '{query}'"
        )
    conn.close()
    return render_template("home.html", productData=productData)


@app.route("/add")
def admin():
    if "email" not in session:
        return redirect(url_for("loginForm"))
    else:
        with engine.connect() as conn:
            categories = conn.execute("SELECT categoryId, name FROM categories")

    return render_template("add.html", categories=categories)


@app.route("/addItem", methods=["GET", "POST"])
def addItem():
    if "email" not in session:
        return redirect(url_for("loginForm"))
    else:
        if request.method == "POST":
            name = request.form["name"]
            price = int(request.form["price"])
            description = request.form["description"]
            stock = int(request.form["stock"])
            categoryId = int(request.form["category"])

            image = request.files["image"]
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)

                # need this if not s3.upload_file will get error
                image.save(filename)

                s3.upload_file(
                    filename,
                    BUCKET_NAME,
                    "CME/" + filename,
                    ExtraArgs={"ACL": "public-read"},
                )
                with engine.connect() as conn:
                    try:
                        conn.execute(
                            text(
                                f"INSERT INTO cme_database.products(name, price, description, image, stock, categoryId) VALUES ('{name}', {price}, '{description}', '{filename}', {stock}, {categoryId})"
                            )
                        )
                        msg = "added successfully"
                        sendEmail(
                            session["email"],
                            {
                                "subject": f"Successfully listed new item {name}",
                                "body": f"New item {name} listed",
                            },
                        )
                    except:
                        msg = "error occurred"
                conn.close()
            else:
                msg = "error occurred, invalid file type"

        print(msg)
        return redirect(url_for("root"))


# got use??
@app.route("/remove")
def remove():
    if "email" not in session:
        return redirect(url_for("loginForm"))
    else:
        with engine.connect() as conn:
            data = conn.execute(
                "SELECT productId, name, price, description, image, stock FROM products"
            )
        conn.close()
    return render_template("remove.html", data=data)


# got use??
@app.route("/removeItem")
def removeItem():
    productId = request.args.get("productId")
    with engine.connect() as conn:
        try:
            conn.execute(
                f"DELETE FROM cme_database.products WHERE productID = {productId}"
            )
            msg = "Deleted successfully"
        except:
            msg = "Error occurred"
    conn.close()
    print(msg)
    return redirect(url_for("cart"))


@app.route("/displayCategory")
def displayCategory():
    loggedIn, firstName, noOfItems = getLoginDetails()
    categoryId = request.args.get("categoryId")
    with engine.connect() as conn:
        data = conn.execute(
            f"SELECT products.productId, products.name, products.price, products.image, categories.name FROM cme_database.products, cme_database.categories WHERE products.categoryId = categories.categoryId AND categories.categoryId = {categoryId}"
        )
        productData = conn.execute(
            f"SELECT * from products where categoryId={categoryId}"
        )
    conn.close()
    categoryName = data.all()[0][4]

    return render_template(
        "displayCategory.html",
        productData=productData,
        loggedIn=loggedIn,
        firstName=firstName,
        noOfItems=noOfItems,
        categoryName=categoryName,
    )


# yet to test
# @app.route("/account/profile")
# def profileHome():
#     if 'email' not in session:
#         return redirect(url_for('root'))
#     loggedIn, firstName, noOfItems = getLoginDetails()
#     return render_template("profileHome.html", loggedIn=loggedIn, firstName=firstName, noOfItems=noOfItems)

# yet to test
# @app.route("/account/profile/edit")
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
    if "email" in session:
        return redirect(url_for("root"))
    else:
        return render_template("login.html", error="")


# yet to test, replace with amplify
@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if is_valid(email, password):
            session["email"] = email
            return redirect(url_for("root"))
        else:
            error = "Invalid UserId / Password"
            return render_template("login.html", error=error)


@app.route("/productDescription")
def productDescription():
    loggedIn, firstName, noOfItems = getLoginDetails()
    productId = request.args.get("productId")
    # eventually dn this if condition, just for testing so the route doesnt bug out
    if productId == None:
        productId = 1
    with engine.connect() as conn:
        product = conn.execute(
            f"SELECT productId, name, price, description, image, stock FROM products WHERE productId = {productId}"
        )
        product = product.all()[0]
    conn.close()
    return render_template(
        "productDescription.html",
        data=product,
        loggedIn=loggedIn,
        firstName=firstName,
        noOfItems=noOfItems,
    )


# yet to test
@app.route("/addToCart")
def addToCart():
    if "email" not in session:
        return redirect(url_for("loginForm"))
    else:
        productId = int(request.args.get("productId"))
        print(productId)
        with engine.connect() as conn:
            userId = conn.execute(
                f"SELECT userId FROM users WHERE email = '{session['email']}'"
            )
            userId = userId.all()[0][0]
            print(userId)
            # try:
            conn.execute(
                f"INSERT INTO kart (userId, productId) VALUES ({userId}, {productId})"
            )
            # conn.commit()
            # msg = "Added successfully"
            # except:
            #     msg = "Error occurred"
        conn.close()
        return redirect(url_for("root"))


# yet to test
@app.route("/cart")
def cart():
    if "email" not in session:
        return redirect(url_for("loginForm"))
    loggedIn, firstName, noOfItems = getLoginDetails()
    email = session["email"]
    with engine.connect() as conn:
        userId = conn.execute(f"SELECT userId FROM users WHERE email = '{email}'")
        userId = userId.all()[0][0]
        print(userId)
        products = conn.execute(
            f"SELECT products.productId, products.name, products.price, products.image FROM cme_database.products, cme_database.kart WHERE products.productId = kart.productId AND kart.userId = {userId}"
        )
        products = products.all()
    totalPrice = 0
    for row in products:
        totalPrice += row[2]
    return render_template(
        "cart.html",
        products=products,
        totalPrice=totalPrice,
        loggedIn=loggedIn,
        firstName=firstName,
        noOfItems=noOfItems,
    )


# yet to test
@app.route("/removeFromCart")
def removeFromCart():
    if "email" not in session:
        return redirect(url_for("loginForm"))
    email = session["email"]
    productId = int(request.args.get("productId"))
    with engine.connect() as conn:
        userId = conn.execute(f"SELECT userId FROM users WHERE email = '{email}'")
        userId = userId.all()[0][0]
        try:
            conn.execute(
                f"DELETE FROM kart WHERE userId = {userId} AND productId = {productId}"
            )
            # conn.commit()
            msg = "removed successfully"
        except:
            msg = "error occurred"
    conn.close()
    return redirect(url_for("root"))


@app.route("/checkout")
def checkout():
    if "email" not in session:
        return redirect(url_for("loginForm"))
    loggedIn, firstName, noOfItems = getLoginDetails()
    with engine.connect() as conn:
        userId = conn.execute(
            f"SELECT userId FROM users WHERE email = '{session['email']}'"
        )
        userId = userId.all()[0][0]
        # print(lastName)
        products = conn.execute(
            f"SELECT products.productId, products.name, products.price, products.image FROM cme_database.products, cme_database.kart WHERE products.productId = kart.productId AND kart.userId = {userId}"
        )
        products = products.all()
        totalPrice = 0
    for row in products:
        totalPrice += row[2]
    return render_template(
        "checkout.html",
        products=products,
        totalPrice=totalPrice,
        loggedIn=loggedIn,
        firstName=firstName,
        noOfItems=noOfItems,
    )


@app.route("/checkoutSuccess")
def checkoutSuccess():
    if "email" not in session:
        return redirect(url_for("loginForm"))
    sendEmail(
        session["email"],
        {"subject": f"Your new order", "body": f"You've just wasted money"},
    )
    return f"You've just wasted money"


@app.route("/logout")
def logout():
    session.pop("email", None)
    return redirect(url_for("root"))


def is_valid(email, password):
    conn = engine.connect()
    data = conn.execute(
        f"SELECT email, password FROM users WHERE email = '{email}' and password = '{password}'"
    )
    data = data.fetchall()
    if len(data) == 1:
        return True
    return False


# replace with amplify
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        password = request.form["password"]
        email = request.form["email"]
        firstName = request.form["firstName"]
        lastName = request.form["lastName"]
        address1 = request.form["address1"]
        address2 = request.form["address2"]
        zipcode = int(request.form["zipcode"])
        city = request.form["city"]
        state = request.form["state"]
        country = request.form["country"]
        phone = request.form["phone"]

        msg = ""
        with engine.connect() as conn:
            try:
                conn.execute(
                    f"INSERT INTO users (password, email, firstName, lastName, address1, address2, zipcode, city, state, country, phone) VALUES ('{password}', '{email}', '{firstName}', '{lastName}', '{address1}', '{address2}', {zipcode}, '{city}', '{state}', '{country}', '{phone}')"
                )
                # conn.commit()
                msg = "Registered Successfully"
                response = ses.verify_email_address(EmailAddress=f"{email}")
            except:
                msg = "Error occurred"
        conn.close()
        return render_template("login.html", error=msg)


# replace with amplify
@app.route("/registrationForm")
def registrationForm():
    return render_template("register.html")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1] in ALLOWED_EXTENSIONS


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

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
