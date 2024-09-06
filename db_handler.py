import mysql.connector
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# MySQL Connection Setup to Create the Database
def get_rds_connection(create_db=False):
    try:
        if create_db:
            # Connect without specifying a database to create the database first
            conn = mysql.connector.connect(
                host='mcq.c30y8giyaus3.us-east-1.rds.amazonaws.com',  # Replace with your RDS endpoint
                user='root',  # Replace with your DB username
                password='Farook22'  # Replace with your DB password
            )
            logging.info("Connected to MySQL server without a database.")
            
            cursor = conn.cursor()

            # Try creating the database
            cursor.execute("CREATE DATABASE IF NOT EXISTS mcq")
            logging.info("Database 'mcq' created or already exists.")
            
            conn.commit()
            cursor.close()
            conn.close()
            logging.info("Connection closed after database creation.")
        
        # Now connect to the specific database
        conn = mysql.connector.connect(
            host='mcq.c30y8giyaus3.us-east-1.rds.amazonaws.com',  # Replace with your RDS endpoint
            user='root',  # Replace with your DB username
            password='Farook22',  # Replace with your DB password
            database='mcq'  # Now connect to the 'mcq' database
        )
        logging.info("Connected to the 'mcq' database.")
        return conn
    except mysql.connector.Error as err:
        logging.error(f"Database connection or creation failed: {err}")
        return None

# Create the 'mcqs' table if it doesn't exist
def create_table_for_mcqs():
    # Ensure that the 'mcq' database exists and create it if necessary
    get_rds_connection(create_db=True)
    
    # Now connect to the 'mcq' database
    conn = get_rds_connection()
    if conn is None:
        logging.error("Failed to connect to RDS.")
        return

    cursor = conn.cursor()

    create_table_query = '''
        CREATE TABLE IF NOT EXISTS mcqs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            question TEXT NOT NULL,
            ans1 TEXT,
            ans2 TEXT,
            ans3 TEXT,
            ans4 TEXT,
            correct_answer INT,
            difficulty TEXT,
            subject_name TEXT,
            topic_name TEXT,
            sub_topic_name TEXT
        )
    '''

    try:
        cursor.execute(create_table_query)
        conn.commit()
        logging.info("Table 'mcqs' created successfully or already exists.")
    except mysql.connector.Error as err:
        logging.error(f"Error creating table: {err}")
    finally:
        cursor.close()
        conn.close()

# Example usage:
if __name__ == "__main__":
    create_table_for_mcqs()

def insert_mcqs_into_db(mcqs):
    conn = get_rds_connection()
    if conn is None:
        logging.error("Failed to connect to the 'mcq' database.")
        return

    cursor = conn.cursor()

    insert_query = '''
        INSERT INTO mcqs (
            question, ans1, ans2, ans3, ans4, correct_answer, difficulty, subject_name, topic_name, sub_topic_name
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    '''

    try:
        for q in mcqs:
            cursor.execute(insert_query, (
                q.get("question"), q.get("ans1"), q.get("ans2"), q.get("ans3"), q.get("ans4"),
                q.get("correct_answer"), q.get("difficulty", "Medium"), 
                q.get("subject_name", "General"), q.get("topic_name", "Unknown"), 
                q.get("sub_topic_name", "")
            ))
        conn.commit()
        logging.info("MCQs inserted successfully into the database.")
    except mysql.connector.Error as err:
        logging.error(f"Error inserting MCQs into the database: {err}")
    finally:
        cursor.close()
        conn.close()
