from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource, Api, reqparse, fields, marshal_with, abort

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
api = Api(app)

class UserModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)

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
        users = UserModel.query.all()
        return users

api.add_resource(Users, "/api/users")
api.add_resource(User, "/api/users/<int:user_id>")

@app.route('/')
def home():
    return '<h1>Welcome to the Flask API!</h1>'

if __name__ == '__main__':
    app.run(debug=True)