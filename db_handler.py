import json
import csv
import mysql.connector
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# MySQL Connection Setup to Create the Database
def get_rds_connection(create_db=False):
    try:
        if create_db:
            conn = mysql.connector.connect(
                host='mcqdb.czg8iug263qh.us-east-1.rds.amazonaws.com',  # Replace with your RDS endpoint
                user='root',  # Replace with your DB username
                password='Farook22'  # Replace with your DB password
            )
            logging.info("Connected to MySQL server without a database.")
            cursor = conn.cursor()
            cursor.execute("CREATE DATABASE IF NOT EXISTS mcq")
            logging.info("Database 'mcq' created or already exists.")
            conn.commit()
            cursor.close()
            conn.close()
            logging.info("Connection closed after database creation.")
        
        # Now connect to the specific database
        conn = mysql.connector.connect(
            host='mcqdb.czg8iug263qh.us-east-1.rds.amazonaws.com',
            user='root',
            password='Farook22',
            database='mcq'
        )
        logging.info("Connected to the 'mcq' database.")
        return conn
    except mysql.connector.Error as err:
        logging.error(f"Database connection or creation failed: {err}")
        return None

# Function to check for duplicates and remove them
def remove_duplicate_mcqs(new_mcqs):
    existing_mcqs = get_existing_mcqs()  # Fetch existing MCQs from the database

    # Normalize existing questions from the database
    existing_questions = {mcq['question'].strip().lower() for mcq in existing_mcqs}

    # Log existing questions fetched from the database
    logging.info(f"Existing MCQs in the database: {existing_questions}")

    non_duplicate_mcqs = []

    for new_mcq in new_mcqs:
        # Normalize the new question for comparison
        new_question_normalized = new_mcq["question"].strip().lower()

        # Log the new question being compared
        logging.info(f"Comparing new question: {new_question_normalized}")

        # Check if the new question exists in the database
        if new_question_normalized not in existing_questions:
            non_duplicate_mcqs.append(new_mcq)  # Add non-duplicate MCQs to the list
        else:
            logging.info(f"Duplicate found for question: {new_question_normalized}")
    
    logging.info(f"Removed duplicates. {len(non_duplicate_mcqs)} unique MCQs remain.")
    return non_duplicate_mcqs

# Function to fetch all existing MCQs from the database
def get_existing_mcqs():
    conn = get_rds_connection()
    if conn is None:
        logging.error("Failed to connect to RDS.")
        return []

    cursor = conn.cursor(dictionary=True)

    query = "SELECT question FROM mcqs"  # Fetch only the question column
    cursor.execute(query)

    existing_mcqs = cursor.fetchall()
    
    # Log how many MCQs were fetched from the database
    logging.info(f"Fetched {len(existing_mcqs)} existing MCQs from the database.")
    
    cursor.close()
    conn.close()
    
    return existing_mcqs

# Create the 'mcqs' table if it doesn't exist
def create_table_for_mcqs():
    get_rds_connection(create_db=True)
    
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

# Insert new MCQs into the database
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

# Save unique MCQs to the text file using regex
def save_unique_mcqs_to_text(unique_mcqs, text_filename):
    try:
        with open(text_filename, 'w', encoding='utf-8') as text_file:
            for mcq in unique_mcqs:
                # Construct the question and options format using regex
                mcq_text = f"**Q. {mcq['question']}**\n"
                mcq_text += f"a) {mcq['ans1']}\n"
                mcq_text += f"b) {mcq['ans2']}\n"
                mcq_text += f"c) {mcq['ans3']}\n"
                mcq_text += f"d) {mcq['ans4']}\n"
                mcq_text += f"**Correct answer: {mcq['correct_answer']}**\n"
                mcq_text += f"**Difficulty: {mcq['difficulty']}**\n"
                mcq_text += f"**Subject: {mcq['subject_name']}**\n"
                mcq_text += f"**Topic: {mcq['topic_name']}**\n"
                mcq_text += f"**Sub-topic: {mcq['sub_topic_name']}**\n"
                mcq_text += f"**Tags: {mcq.get('tags', '')}**\n\n"

                text_file.write(mcq_text)
        
        logging.info(f"Unique MCQs saved to text file: {text_filename}")
    except Exception as e:
        logging.error(f"Failed to save MCQs to text file: {e}")

# Process the MCQs, remove duplicates, and save them to the text file
def process_and_save_unique_mcqs_to_text(new_mcqs, text_filename):
    # Remove duplicates before inserting into the DB
    unique_mcqs = remove_duplicate_mcqs(new_mcqs)

    if unique_mcqs:
        # Insert unique MCQs into the database
        insert_mcqs_into_db(unique_mcqs)

        # Save the unique MCQs to the text file
        save_unique_mcqs_to_text(unique_mcqs, text_filename)

        logging.info(f"Unique MCQs successfully processed and saved to text file.")
    else:
        logging.info("No new MCQs to insert. All generated questions are duplicates.")

# Streamlit MCQ Generation Process (Assuming MCQs are dynamically generated)
def generate_mcqs():
    # Example: Replace with actual MCQ generation logic
    return [
        {
            "question": "What is AWS Lambda?",
            "ans1": "A compute service",
            "ans2": "A storage service",
            "ans3": "A database service",
            "ans4": "An analytics service",
            "correct_answer": 1,
            "difficulty": "Easy",
            "subject_name": "AWS",
            "topic_name": "Compute",
            "sub_topic_name": "Lambda",
            "tags": "Compute, AWS, Lambda"
        },
        # Add dynamically generated MCQs here
    ]

# Example usage in your existing workflow
if __name__ == "__main__":
    # Dynamically generate MCQs
    new_mcqs = generate_mcqs()

    # Define file name for the text file
    text_filename = 'unique_mcqs.txt'

    # Process the MCQs and save unique ones to DB and text file
    process_and_save_unique_mcqs_to_text(new_mcqs, text_filename)
