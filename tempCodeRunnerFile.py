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
