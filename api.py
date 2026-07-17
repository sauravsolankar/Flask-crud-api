from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Sequence
import oracledb
from flask_restful import Resource, Api, reqparse, fields, marshal_with, abort
from flask_cors import CORS

app = Flask(__name__)

# --- ORACLE CONNECTION CONFIGURATION ---
USERNAME = "api"
PASSWORD = "6969"
HOSTNAME = "localhost" 
PORT = "1521"          
SERVICE_NAME = "ORCL"  

app.config['SQLALCHEMY_DATABASE_URI'] = f"oracle+oracledb://{USERNAME}:{PASSWORD}@{HOSTNAME}:{PORT}/?service_name={SERVICE_NAME}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
api = Api(app)
CORS(app)
# ---------------------------------------

class UserModel(db.Model):
    __tablename__ = 'users_table' 
    id = db.Column(db.Integer, Sequence('user_id_seq'), primary_key=True)
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

# =====================================================================
#   NEW PLAYGROUND RESOURCE: EXPERIMENT WITH STORED PROCEDURES HERE!
# =====================================================================
class UserProcedure(Resource):
    
    @marshal_with(user_Fields)
    def get(self):
        try:
            raw_conn = db.engine.raw_connection()
            cursor = raw_conn.cursor()

            # 1. Create a special cursor variable in Python to receive the Oracle stream
            # If you are using the newer 'oracledb' package, use: oracledb.CURSOR
            # If you are using 'cx_Oracle', use: cx_Oracle.CURSOR
            cursor_var = cursor.var(oracledb.CURSOR)

            # 2. Call the procedure, passing our empty cursor variable as the argument
            cursor.callproc('get_all_users_proc', [cursor_var])

            # 3. Fetch all rows out of the returned cursor variable
            # getvalue() extracts the live database cursor object, and fetchall() grabs all the data records
            raw_users = cursor_var.getvalue().fetchall()

            cursor.close()
            raw_conn.close()

            # 4. Turn the raw database tuples into a clean format that matches user_Fields
            users = []
            for row in raw_users:
                users.append({
                    'id': row[0],
                    'name': row[1],
                    'email': row[2]
                })

            return users

        except Exception as e:
            abort(500, message=f"Procedure Error: {str(e)}")
    
    @marshal_with(user_Fields)
    def post(self):
        # 1. Parse incoming JSON arguments just like the old way
        args = user_args.parse_args()
        
        try:
            # 2. Grab the direct line connection to Oracle via SQLAlchemy
            raw_conn = db.engine.raw_connection()
            cursor = raw_conn.cursor()

            # 3. Call your stored procedure by its exact database name
            # Make sure you have created 'insert_user_proc' inside your Oracle DB!
            cursor.callproc('insert_user_proc', [args['name'], args['email']])

            # 4. Clean up the database connection channels
            cursor.close()
            raw_conn.close()

            # 5. Fetch all users from the database to return them, mimicking your original POST flow
            users = UserModel.query.all()
            return users, 201

        except Exception as e:
            # If the procedure fails (e.g., name duplicate or proc missing), abort gracefully
            abort(500, message=f"Procedure Error: {str(e)}")


class UserSingleProcedure(Resource):
    @marshal_with(user_Fields)
    def get(self, user_id):
        try:
            raw_conn = db.engine.raw_connection()
            cursor = raw_conn.cursor()

            # 1. Create variables in Python to catch the OUT data from Oracle
            out_name = cursor.var(str)
            out_email = cursor.var(str)

            # 2. Call the procedure passing the ID we want, and our two catch variables
            cursor.callproc('get_user_by_id_proc', [user_id, out_name, out_email])

            # 3. Extract the actual text values returned by Oracle
            name_val = out_name.getvalue()
            email_val = out_email.getvalue()

            cursor.close()
            raw_conn.close()

            # 4. If Oracle returned nothing (NULL), it means the user wasn't found
            if name_val is None:
                abort(404, message="User not found via procedure")

            # 5. Return a clean dictionary matching your user_Fields format
            return {
                'id': user_id,
                'name': name_val,
                'email': email_val
            }

        except Exception as e:
            abort(500, message=f"Procedure Error: {str(e)}")

    @marshal_with(user_Fields)
    def patch(self, user_id):
        # 1. Parse incoming JSON arguments just like your original route
        args = user_args.parse_args()
        
        try:
            raw_conn = db.engine.raw_connection()
            cursor = raw_conn.cursor()

            # 2. Call the update procedure passing the ID and new data
            cursor.callproc('update_user_proc', [user_id, args['name'], args['email']])

            cursor.close()
            raw_conn.close()

            # 3. Return the updated values back to the user to confirm success
            return {
                'id': user_id,
                'name': args['name'],
                'email': args['email']
            }

        except Exception as e:
            # If Oracle threw our -20001 error, we catch it here
            if "User not found" in str(e):
                abort(404, message="User not found for update via procedure")
            abort(500, message=f"Procedure Error: {str(e)}")

    @marshal_with(user_Fields)
    def delete(self, user_id):
        try:
            raw_conn = db.engine.raw_connection()
            cursor = raw_conn.cursor()

            # 1. Call the delete procedure passing the target ID
            cursor.callproc('delete_user_proc', [user_id])

            cursor.close()
            raw_conn.close()

            # 2. Return the ID of the deleted user to match your original API behavior
            return {
                'id': user_id,
                'name': 'Deleted successfully',
                'email': 'Deleted successfully'
            }

        except Exception as e:
            # Catch the custom exception if the user ID wasn't found in the database
            if "User not found" in str(e):
                abort(404, message="User not found for deletion via procedure")
            abort(500, message=f"Procedure Error: {str(e)}")

# --- ROUTE REGISTRATIONS ---
api.add_resource(Users, "/api/users")
api.add_resource(User, "/api/users/<int:user_id>")
api.add_resource(UserSingleProcedure, "/api/users-procedure/<int:user_id>")

# New Endpoint mapped to the new class
api.add_resource(UserProcedure, "/api/users-procedure")

with app.app_context():
     db.create_all()


@app.route('/')
def home():
    return '<h1>Welcome to Saurav\'s Flask API - Auto Deployment Works!!</h1>'

import git
from flask import request

@app.route('/update_server', methods=['POST'])
def webhook():
    if request.method == 'POST':
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