import mysql.connector


def get_db_connection():

    connection = mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",
        password="Shrau@05",
        database="resume_builder"
    )

    return connection