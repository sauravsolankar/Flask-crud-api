from ast import Import
from dotenv import load_dotenv
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Sequence
# import oracledb
from flask_restful import Resource, Api, reqparse, fields, marshal_with, abort
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
api = Api(app)
CORS(app)
# ---------------------------------------

class UserModel(db.Model):
    __tablename__ = 'users_table' 
    id = db.Column(db.Integer, Sequence('user_id_seq'), primary_key=True)
    name = db.Column(db.String(80), unique=False, nullable=False)
    email = db.Column(db.String(80), unique=False, nullable=False)

    def __repr__(self):
        return f"User(name={self.name}, email={self.email})"

user_args = reqparse.RequestParser()
user_args.add_argument("name", type=str, help="Name of the user is required", required=True)
user_args.add_argument("email", type=str, help="Email of the user is required", required=True)

user_Fields = {
    'id': fields.Integer,
    'name': fields.String,
    'email': fields.String
}

# =====================================================================
#   ORIGINAL TUTORIAL CLASSES (LEFT UNTOUCHED)
# =====================================================================
class Users(Resource):
    @marshal_with(user_Fields)
    def get(self):
        users = UserModel.query.all()
        return users
    
    @marshal_with(user_Fields)
    def post(self):
        args = user_args.parse_args()
        user = UserModel(name=args['name'], email=args['email'])
        db.session.add(user)
        db.session.commit()
        users = UserModel.query.all()
        return users, 201
    
class User(Resource):
    @marshal_with(user_Fields)
    def get(self, user_id):
        user = UserModel.query.filter_by(id=user_id).first()
        if not user:
            abort(404, message="User not found")
        return user
    
    @marshal_with(user_Fields)
    def patch(self, user_id):
        args = user_args.parse_args()
        user = UserModel.query.filter_by(id=user_id).first()
        if not user:
            abort(404, message="User not found")
        user.name = args['name']
        user.email = args['email']
        db.session.commit()
        return user
    
    @marshal_with(user_Fields)
    def delete(self, user_id):
        user = UserModel.query.filter_by(id=user_id).first()
        if not user:
            abort(404, message="User not found")
        db.session.delete(user)
        db.session.commit()
        return user 


# --- ROUTE REGISTRATIONS ---
api.add_resource(Users, "/api/users")
api.add_resource(User, "/api/users/<int:user_id>")

with app.app_context():
     db.create_all()


@app.route('/')
def home():
    return '<h1>Welcome to Saurav\'s Flask API - Auto Deployment Works!!</h1>'

from flask import request

@app.route('/update_server', methods=['POST'])
def webhook():
    if request.method == 'POST':
        import git

        # Path to your cloned project folder on PythonAnywhere
        repo = git.Repo('/home/solankarsaurav/Flask-crud-api')
        origin = repo.remotes.origin
        
        # Pull the latest changes from GitHub
        origin.pull()
        return 'Updated PythonAnywhere successfully', 200
    else:
        return 'Wrong event type', 400

if __name__ == '__main__':

        
    app.run(debug=True)