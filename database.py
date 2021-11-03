# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://cme_database:ilovecme@cme-database.cpufpabpntvq.us-east-1.rds.amazonaws.com'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# app.permanent_session_lifetime = timedelta(minutes=5)
# db = SQLAlchemy(app)

# class users(db.Model):
#     userId = db.Column(db.Integer, primary_key=True)
#     password = db.Column(db.String(144))
#     email = db.Column(db.String(144))
#     firstName = db.Column(db.String(144))
#     lastName = db.Column(db.String(144))

# class products(db.Model):
#     productId = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(144))
#     price = db.Column(db.Float)
#     description = db.Column(db.String(144))
#     image = db.Column(db.String(144))
#     stock = db.Column(db.Integer)
#     categoryId = db.Column(db.Integer)

# class kart(db.Model):
#     userId = db.Column(db.Integer, primary_key=True)
#     productId = db.Column(db.Integer)

# class categories(db.Model):
#     categoryId = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(144))