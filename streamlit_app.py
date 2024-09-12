import streamlit as st
import os
import json
import csv
import logging
import time
import re
from langchain.llms import GooglePalm
from db_handler import create_table_for_mcqs, insert_mcqs_into_db, get_existing_mcqs, get_rds_connection

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Define your LLM instance
api_key = "AIzaSyB-xCwgjhaqeuSZhPhjiZ8QQwETQtryqtw"
llm = GooglePalm(google_api_key=api_key, temperature=0.4, model_name="gemini-1.5-flash-latest")

# Define the prompt template
prompt_template = (
    "Generate {num_questions} unique multiple-choice questions (MCQs) about {topic} with {difficulty} difficulty. "
    "Each question should have one correct answer and three incorrect options. "
    "The question should not involve any code and should be non-googlable. "
    "Format each question and answer as follows:\n\n"
    "Q1. [Question text]?\n"
    "a) [Option 1]\n"
    "b) [Option 2]\n"
    "c) [Option 3]\n"
    "d) [Option 4]\n"
    "Correct answer: [Correct option number]\n"
    "Difficulty: [Difficulty]\n"
    "Subject: [Subject Name]\n"
    "Topic: [Topic Name]\n"
    "Sub-topic: [Sub-topic Name]\n"
    "Tags: [Tags]\n\n"
)

# Function to generate MCQs with retry mechanism
def generate_mcqs(topic, num_questions, difficulty, max_retries=3):
    prompt = prompt_template.format(topic=topic, num_questions=num_questions,difficulty=difficulty)
    for attempt in range(max_retries):
        try:
            response = llm(prompt)
            return response
        except Exception as e:
            logging.error(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait for 2 seconds before retrying
            else:
                raise Exception("Failed to generate MCQs after multiple attempts")

# Function to save MCQs to a text file
def save_to_file(filename, text):
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(text)
        logging.info(f"File saved: {filename}")
    except Exception as e:
        logging.error(f"Failed to save file {filename}: {e}")

# MCQ Parsing function with updated handling for correct answer and options
def parse_mcqs_from_text(text):
    mcqs = []
    questions = text.split("**Q")

    for q in questions[1:]:  # Skip the first split part as it's empty
        try:
            # Extract the question text
            question_match = re.search(r'\d+\.\s*(.*?)\*\*', q)
            question = question_match.group(1) if question_match else "Unknown Question"

            # Extract the correct answer first (e.g., **Correct answer: a)**)
            correct_answer_match = re.search(r'\*\*Correct answer:\s*([a-d])\)\*\*', q)
            correct_answer = correct_answer_match.group(1) if correct_answer_match else None

            if correct_answer is None:
                logging.error(f"Invalid or missing correct answer in question: {q}")
                continue

            # Convert the correct answer letter (a, b, c, d) to a number (1, 2, 3, 4)
            correct_answer_num = {"a": 1, "b": 2, "c": 3, "d": 4}.get(correct_answer)

            # Extract options, but ensure only the lines starting with a) to d) are captured
            options = re.findall(r'([a-d])\)\s*(.*?)(?=\n[a-d]\)|$)', q, re.DOTALL)
            if len(options) != 4:
                logging.error(f"Error: Expected 4 options but found {len(options)}")
                continue  # Skip this question if it doesn't have exactly 4 options

            ans1, ans2, ans3, ans4 = [opt[1] for opt in options]

            # Extract additional fields like difficulty, subject, etc.
            difficulty_match = re.search(r'Difficulty:\s*(.*?)\n', q)
            difficulty = difficulty_match.group(1) if difficulty_match else "Unknown"

            subject_match = re.search(r'Subject:\s*(.*?)\n', q)
            subject_name = subject_match.group(1) if subject_match else "Unknown"

            topic_match = re.search(r'Topic:\s*(.*?)\n', q)
            topic_name = topic_match.group(1) if topic_match else "Unknown"

            sub_topic_match = re.search(r'Sub-topic:\s*(.*?)\n', q)
            sub_topic_name = sub_topic_match.group(1) if sub_topic_match else ""

            tags_match = re.search(r'Tags:\s*(.*?)\n', q)
            tags = tags_match.group(1) if tags_match else ""

            # Create the MCQ dictionary
            mcq = {
                "question": question,
                "ans1": ans1,
                "ans2": ans2,
                "ans3": ans3,
                "ans4": ans4,
                "correct_answer": correct_answer_num,  # Store the numeric representation of the correct answer
                "difficulty": difficulty,
                "subject_name": subject_name,
                "topic_name": topic_name,
                "sub_topic_name": sub_topic_name,
                "tags": tags
            }
            mcqs.append(mcq)

        except Exception as e:
            logging.error(f"Error parsing question: {q}")
            logging.error(f"Error: {str(e)}")

    return mcqs

# Function to check for duplicates and remove them
def remove_duplicate_mcqs(new_mcqs):
    existing_mcqs = get_existing_mcqs()  # Function that fetches all MCQs from the database
    non_duplicate_mcqs = []
    
    for new_mcq in new_mcqs:
        if not any(existing_mcq["question"] == new_mcq["question"] for existing_mcq in existing_mcqs):
            non_duplicate_mcqs.append(new_mcq)

    logging.info(f"Removed duplicates. {len(non_duplicate_mcqs)} unique MCQs remain.")
    return non_duplicate_mcqs

# Convert text file to JSON
def convert_txt_to_json(txt_file_path, json_file_path):
    try:
        with open(txt_file_path, 'r', encoding='utf-8') as txt_file:
            text = txt_file.read()
        
        mcqs = parse_mcqs_from_text(text)

        with open(json_file_path, 'w', encoding='utf-8') as json_file:
            json.dump(mcqs, json_file, indent=4)
        
        logging.info(f"Successfully converted {txt_file_path} to {json_file_path}")
    except Exception as e:
        logging.error(f"Error converting text to JSON: {str(e)}")
# Function to save unique MCQs to a text file
def save_unique_mcqs_to_file(filename, mcqs):
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            for i, mcq in enumerate(mcqs, 1):
                file.write(f"Q{i}. {mcq['question']}\n")
                file.write(f"a) {mcq['ans1']}\n")
                file.write(f"b) {mcq['ans2']}\n")
                file.write(f"c) {mcq['ans3']}\n")
                file.write(f"d) {mcq['ans4']}\n")
                file.write(f"Correct answer: {mcq['correct_answer']}\n")
                file.write(f"Difficulty: {mcq['difficulty']}\n")
                file.write(f"Subject: {mcq['subject_name']}\n")
                file.write(f"Topic: {mcq['topic_name']}\n")
                file.write(f"Sub-topic: {mcq['sub_topic_name']}\n")
                file.write(f"Tags: {mcq['tags']}\n")
                file.write("\n")
        logging.info(f"Unique MCQs saved to {filename}.")
    except Exception as e:
        logging.error(f"Failed to save unique MCQs to file {filename}: {e}")

# Convert JSON to CSV
def convert_json_to_csv(json_file_path, csv_file_path):
    try:
        with open(json_file_path, 'r', encoding='utf-8') as json_file:
            mcqs = json.load(json_file)
        
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["question", "ans1", "ans2", "ans3", "ans4", "correct_answer", "difficulty", "subject_name", "topic_name", "sub_topic_name", "tags"])
            
            for mcq in mcqs:
                writer.writerow([
                    mcq["question"], mcq["ans1"], mcq["ans2"], mcq["ans3"], mcq["ans4"], 
                    mcq["correct_answer"], mcq["difficulty"], mcq["subject_name"], 
                    mcq["topic_name"], mcq["sub_topic_name"], mcq["tags"]
                ])
        
        logging.info(f"Successfully converted {json_file_path} to {csv_file_path}")
    except Exception as e:
        logging.error(f"Error converting JSON to CSV: {str(e)}")


# Define input and output file paths
input_file_path = 'unique_mcq.txt'  # Replace with your actual text file path
output_csv = 'questions.csv'

# Function to clean unwanted characters
def clean_text(text):
    return text.replace('`', '').replace('**', '').strip()

# Function to extract details from each question block
def parse_question_block(block):
    lines = block.strip().split('\n')

    # Extracting relevant parts from the text block
    question_match = re.search(r'Q\d+\.\s(.+)', lines[0])
    if question_match:
        question = clean_text(question_match.group(1))
    else:
        return None  # If question pattern not found, skip this block

    ans1 = clean_text(lines[1].split(') ')[1])
    ans2 = clean_text(lines[2].split(') ')[1])
    ans3 = clean_text(lines[3].split(') ')[1])
    ans4 = clean_text(lines[4].split(') ')[1])
    
    correct_answer_letter = re.search(r'Correct answer: (\w)', lines[5]).group(1).lower()
    correct_answer_index = {'a': 1, 'b': 2, 'c': 3, 'd': 4}[correct_answer_letter]
    
    difficulty = clean_text(re.search(r'Difficulty: (\w+)', lines[6]).group(1))
    subject_name = clean_text(re.search(r'Subject: (\w+)', lines[7]).group(1))
    topic_name = clean_text(re.search(r'Topic: (.+)', lines[8]).group(1))
    sub_topic_name = clean_text(re.search(r'Sub-topic: (.+)', lines[9]).group(1))
    tags = clean_text(re.search(r'Tags: (.+)', lines[10]).group(1))

    return {
        'question': question,
        'ans1': ans1,
        'ans2': ans2,
        'ans3': ans3,
        'ans4': ans4,
        'answer': correct_answer_index,
        'difficulty': difficulty,
        'subject_name': subject_name,
        'topic_name': topic_name,
        'sub_topic_name': sub_topic_name,
        'blooms_taxonomy': 'Evaluate',  # Default value for blooms_taxonomy
        'tags': tags,  # Adding tags as a separate column
        'course_outcome': 'CO1',  # Placeholder, change if needed
        'program_outcome': 'PO1'  # Placeholder, change if needed
    }

# Function to parse MCQs from text file and save to CSV
def parse_and_save_mcqs(input_text, output_csv):
    try:
        # Split the input text into question blocks based on two line breaks between questions
        question_blocks = input_text.strip().split('\n\n')
        
        with open(output_csv, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=[
                'question', 'ans1', 'ans2', 'ans3', 'ans4', 'answer', 'difficulty', 
                'subject_name', 'topic_name', 'sub_topic_name', 'blooms_taxonomy', 
                'tags',  # Adding the new tags column
                'course_outcome', 'program_outcome'
            ])
            writer.writeheader()
            
            for block in question_blocks:
                parsed_data = parse_question_block(block)
                if parsed_data:
                    writer.writerow(parsed_data)
        return True

    except Exception as e:
        logging.error(f"Error during CSV generation: {str(e)}")
        return False
# Check DB Connection at the Beginning
def check_db_connection():
    conn = get_rds_connection()
    if conn is None:
        st.error("Database connection is not available. Please check the RDS instance.")
        return False
    conn.close()
    return True
# Streamlit application
st.title("OG MCQ Generator")

if not check_db_connection():
    st.stop()  # Stop further execution if DB is not connected

# Upload input text file
# uploaded_file = st.file_uploader("Choose a text file", type="txt")

# Inputs for topic and number of questions
topic = st.text_input("Enter the topic: (example : ec2, hooks)")
difficulty = st.radio("Select difficulty level:", ('easy', 'medium', 'hard'))
num_questions = st.number_input("Enter the number of questions:", min_value=1, max_value=1000, value=10)

# Filenames for saving files
text_filename = 'questions_prompt_mcq.txt'
json_filename = 'questions_prompt.json'
csv_filename = 'questions_prompt.csv'
unique_mcq_filename = 'unique_mcq.txt'

if st.button("Cook MCQs"):
    if topic:
        try:
            # Step 1: Generate MCQs
            mcqs = generate_mcqs(topic, num_questions, difficulty)
            save_to_file(text_filename, mcqs)
            st.success(f"MCQs generated with {difficulty} difficulty and saved to {text_filename}.")

            # Step 2: Parse and check for duplicates
            mcqs_parsed = parse_mcqs_from_text(mcqs)
            mcqs_unique = remove_duplicate_mcqs(mcqs_parsed)

            if mcqs_unique:
                # Step 3: Insert the unique MCQs into the database
                create_table_for_mcqs()  # Ensure table exists
                insert_mcqs_into_db(mcqs_unique)
                st.success(f"Unique MCQs with {difficulty} difficulty inserted into the database.")
                # Save unique MCQs to a text file
                save_unique_mcqs_to_file(unique_mcq_filename, mcqs_unique)
                st.success(f"Unique MCQs saved to {unique_mcq_filename}.")

                # Provide a download button for unique MCQ text file
                # with open(unique_mcq_filename, "rb") as file:
                    # st.download_button(label="Download Unique MCQs", data=file, file_name=unique_mcq_filename)

            else:
                st.warning("No new MCQs to insert. All generated questions are duplicates.")

             # Step 1: Read the input text from the file
            if os.path.exists(input_file_path):
                with open(input_file_path, 'r') as file:
                    input_text = file.read()

                # Step 2: Parse and save the MCQs to CSV
                csv_created = parse_and_save_mcqs(input_text, output_csv)

                if csv_created:
                    st.success(f"CSV file '{output_csv}' has been created.")
                    # Provide a download button for the CSV file
                    with open(output_csv, "rb") as file:
                        st.download_button(label="Download CSV", data=file, file_name=output_csv)
                else:
                    st.error("Failed to generate the CSV file.")
            else:
                st.error(f"Input file '{input_file_path}' does not exist.")
        

     
            
            # # Step 4: Convert to JSON and CSV
            # convert_txt_to_json(text_filename, json_filename)
            # st.success(f"Text file converted to JSON: {json_filename}")
            
            # convert_json_to_csv(json_filename, csv_filename)
            # st.success(f"JSON file converted to CSV: {csv_filename}")

  
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

# # If a file is uploaded, process and save as CSV
# if uploaded_file:
#     try:
#         # Read the input text from the uploaded file
#         input_text = uploaded_file.read().decode("utf-8")
        
#         # Parse and save the MCQs to CSV
#         parse_and_save_mcqs(input_text, output_csv)
#         st.success(f"CSV file '{output_csv}' has been created.")
        
#         # Provide a download button for the CSV file
#         with open(output_csv, "rb") as file:
#             st.download_button(label="Download CSV", data=file, file_name=output_csv)

#     except Exception as e:
#         st.error(f"An error occurred: {str(e)}")
