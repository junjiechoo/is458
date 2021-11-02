from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy(app)

engine = create_engine('mysql://cme_database:ilovecme@cme-database.cpufpabpntvq.us-east-1.rds.amazonaws.com')

