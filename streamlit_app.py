import streamlit as st
import os
import json
import csv
from langchain.llms import GooglePalm
import logging
import time
import re
from db_handler import create_table_for_mcqs, insert_mcqs_into_db

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Define your LLM instance
api_key = "AIzaSyB-xCwgjhaqeuSZhPhjiZ8QQwETQtryqtw"
llm = GooglePalm(google_api_key=api_key, temperature=0.4, model_name="gemini-1.5-flash-latest")

# Define the prompt template
prompt_template = (
    "Generate {num_questions} unique multiple-choice questions (MCQs) about {topic}. "
    "Each question should have one correct answer and three incorrect options. "
    "Snippet type questions are not needed and it should be non-googlable and should not be repeated. "
    "The question should not involve any code. "
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
    "Ensure while giving the correct option number please don't give the correct answer text. "
    "The options are in a, b, c, d so you take it as 1, 2, 3, 4 and give the correct number. "
    "Ensure that each question has exactly one correct answer and three incorrect options. "
    "Inside the correct answer section, provide only the correct answer number, not the option or any other words or symbols. "
    "Don't use ** before or after the question and the correct answer or anywhere else. "
    "Do not include any snippet-based MCQs."
)

# Function to generate MCQs with retry mechanism
def generate_mcqs(topic, num_questions, max_retries=3):
    prompt = prompt_template.format(topic=topic, num_questions=num_questions)
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


# Define your MCQ parser function
def parse_mcqs_from_text(text):
    """Parse MCQs from the given text and return a list of dictionaries."""
    mcqs = []
    questions = text.split("**Q")
    
    for q in questions[1:]:  # Skip the first split part as it's empty
        try:
            # Extract question
            question_match = re.search(r'\d+\.\s*(.*?)\*\*', q)
            question = question_match.group(1) if question_match else "Unknown Question"

            # Extract options
            options = re.findall(r'([a-d])\)\s*(.*?)\n', q)
            ans1, ans2, ans3, ans4 = [opt[1] for opt in options]

            # Extract correct answer
            correct_answer_match = re.search(r'\*\*Correct answer:\s*(\d+)', q)
            correct_answer = int(correct_answer_match.group(1)) if correct_answer_match else None

            # Extract difficulty, subject, topic, sub-topic, and tags
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
                "correct_answer": correct_answer,
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


# Function to write the output to a file
def save_to_file(filename, text):
    try:
        with open(filename, 'w') as file:
            file.write(text)
        logging.info(f"File saved: {filename}")
    except Exception as e:
        logging.error(f"Failed to save file {filename}: {e}")

def parse_question_blocks(lines):
    """Parse lines into a list of questions."""
    questions = []
    question = {}
    current_question = ""
    in_question = False

    # Default values for the additional fields
    default_blooms_taxonomy = "Evaluate"
    default_course_outcome = "CO1"
    default_program_outcome = "PO1"

    for line_num, line in enumerate(lines, 1):
        try:
            line = line.strip()
            logging.debug(f"Processing line {line_num}: {line}")

        
            # Check for different formats and delimiters
            if line.startswith("## Question") or line.startswith("**Q"):
                if in_question and question:
                    question["question"] = current_question.strip()
                    question["blooms_taxonomy"] = default_blooms_taxonomy
                    question["course_outcome"] = default_course_outcome
                    question["program_outcome"] = default_program_outcome
                    questions.append(question)
                    logging.debug(f"Appended question: {question}")
                
                question = {}
                
                # Extract the question text depending on the prefix
                if line.startswith("**Q"):
                    # Extract text after the first period and before any '**' if present
                    current_question = line.split('.', 1)[-1].split('**', 1)[0].strip()
                else:
                    # For lines starting with "## Question", strip digits and stop at '**'
                    current_question = line.lstrip("Q1234567890. ").split('**', 1)[0].strip()
                
                in_question = True

            elif line.startswith("a)") or line.startswith("b)") or line.startswith("c)") or line.startswith("d)"):
                if "options" not in question:
                    question["options"] = {}
                key = line[0]
                question["options"][key] = line[2:].strip()
            
            elif line.startswith("Correct answer:"):
                # Extract the correct answer number
                answer_match = re.search(r'\d+', line)
                if answer_match:
                    question["answer"] = answer_match.group()
                else:
                    logging.error(f"Invalid correct answer format in line {line_num}: {line}")
            
            elif line.startswith("**Correct answer:"):
                question["answer"] = line.replace("Correct answer:", "").strip() 
            
            elif line.startswith("Difficulty:"):
                question["difficulty"] = line.replace("Difficulty:", "").strip()
            
            elif line.startswith("Subject:"):
                question["subject_name"] = line.replace("Subject:", "").strip()
            
            elif line.startswith("Topic:"):
                question["topic_name"] = line.replace("Topic:", "").strip()
            
            elif line.startswith("Sub-topic:"):
                question["sub_topic_name"] = line.replace("Sub-topic:", "").strip()
            
            elif line.startswith("Tags:"):
                question["tags"] = line.replace("Tags:", "").strip()
            
            else:
                if in_question:
                    # Use regex to remove potential correct answer text from the question
                    current_question = re.sub(r'\*\*.*?Correct answer:\s*\d+', '', current_question).strip()
                    current_question += " " + line.rstrip('**')

        except Exception as e:
            logging.error(f"Error parsing line {line_num}: {line}")
            logging.error(f"Error details: {str(e)}")

    if in_question and question:
        question["question"] = current_question.strip()
        question["blooms_taxonomy"] = default_blooms_taxonomy
        question["course_outcome"] = default_course_outcome
        question["program_outcome"] = default_program_outcome
        questions.append(question)
        logging.debug(f"Appended final question: {question}")
    
    logging.info(f"Total questions parsed: {len(questions)}")
    return questions




def convert_txt_to_json(txt_file_path, json_file_path):
    """Convert a text file with MCQs into a JSON file with each question in a separate object."""
    try:
        with open(txt_file_path, 'r', encoding='utf-8') as txt_file:
            lines = txt_file.readlines()

        logging.info(f"Read {len(lines)} lines from {txt_file_path}")

        questions = parse_question_blocks(lines)

        if not questions:
            logging.error("No questions were parsed from the input file.")
            return

        formatted_questions = []
        for q in questions:
            if "question" not in q or "options" not in q:
                logging.error(f"Question object is missing required fields: {q}")
                continue

            formatted_q = {
                "question": q["question"],
                "ans1": q["options"].get("a", ""),
                "ans2": q["options"].get("b", ""),
                "ans3": q["options"].get("c", ""),
                "ans4": q["options"].get("d", ""),
                "answer": q.get("answer", ""),
                "difficulty": q.get("difficulty", ""),
                "subject_name": q.get("subject_name", ""),
                "topic_name": q.get("topic_name", ""),
                "sub_topic_name": q.get("sub_topic_name", ""),
                
            }
            formatted_questions.append(formatted_q)

        with open(json_file_path, 'w', encoding='utf-8') as json_file:
            json.dump(formatted_questions, json_file, indent=4)
            
        logging.info(f"Successfully converted '{txt_file_path}' to '{json_file_path}'")
    
    except Exception as e:
        logging.error(f"An error occurred during text to JSON conversion: {e}")
        logging.error("Content of the text file:")
        with open(txt_file_path, 'r', encoding='utf-8') as txt_file:
            logging.error(txt_file.read())
def convert_json_to_csv(json_file_path, csv_file_path):
    """Convert a JSON file with MCQs into a CSV file."""
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)

        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
        
            # Ensure headers include all required fields
            headers = [
                "question", "ans1", "ans2", "ans3", "ans4", "answer", 
                "difficulty", "subject_name", "topic_name", "sub_topic_name",
                "blooms_taxonomy", "course_outcome", "program_outcome"
            ]
            csv_writer.writerow(headers)
        
            # Write each dictionary as a row in the CSV file
            for entry in data:
                row = [
                    entry.get("question", ""),
                    entry.get("ans1", ""),
                    entry.get("ans2", ""),
                    entry.get("ans3", ""),
                    entry.get("ans4", ""),
                    entry.get("answer", ""),
                    entry.get("difficulty", ""),
                    entry.get("subject_name", ""),
                    entry.get("topic_name", ""),
                    entry.get("sub_topic_name", ""),
                    entry.get("blooms_taxonomy", "Evaluate"),  # Default value
                    entry.get("course_outcome", "CO1"),       # Default value
                    entry.get("program_outcome", "PO1")       # Default value
                ]
                csv_writer.writerow(row)

        logging.info(f"Successfully converted '{json_file_path}' to '{csv_file_path}'")
    
    except Exception as e:
        logging.error(f"An error occurred during JSON to CSV conversion: {e}")

# Function to convert JSON to CSV
def convert_txt_to_json(txt_file_path, json_file_path):
    """Convert a text file with MCQs into a JSON file with each question in a separate object."""
    try:
        with open(txt_file_path, 'r', encoding='utf-8') as txt_file:
            lines = txt_file.readlines()

        logging.info(f"Read {len(lines)} lines from {txt_file_path}")

        questions = parse_question_blocks(lines)

        if not questions:
            logging.error("No questions were parsed from the input file.")
            return

        formatted_questions = []
        for q in questions:
            if "question" not in q or "options" not in q:
                logging.error(f"Question object is missing required fields: {q}")
                continue

            formatted_q = {
                "question": q["question"],
                "ans1": q["options"].get("a", ""),
                "ans2": q["options"].get("b", ""),
                "ans3": q["options"].get("c", ""),
                "ans4": q["options"].get("d", ""),
                "answer": q.get("answer", ""),
                "difficulty": q.get("difficulty", ""),
                "subject_name": q.get("subject_name", ""),
                "topic_name": q.get("topic_name", ""),
                "sub_topic_name": q.get("sub_topic_name", ""),
                "blooms_taxonomy": "Evaluate",  # Default value
                "course_outcome": "CO1",       # Default value
                "program_outcome": "PO1"       # Default value
            }
            formatted_questions.append(formatted_q)

        with open(json_file_path, 'w', encoding='utf-8') as json_file:
            json.dump(formatted_questions, json_file, indent=4)
            
        logging.info(f"Successfully converted '{txt_file_path}' to '{json_file_path}'")
    
    except Exception as e:
        logging.error(f"An error occurred during text to JSON conversion: {e}")
        logging.error("Content of the text file:")
        with open(txt_file_path, 'r', encoding='utf-8') as txt_file:
            logging.error(txt_file.read())


# Streamlit application
st.title("MCQ Generator")
# Read MCQs from an existing text file
text_filename = 'questions_prompt.txt'
json_filename = 'questions_prompt.json'
csv_filename = 'questions_prompt.csv'
# Step 1: Generate MCQs
st.header("Step 1: Generate MCQs")
topic = st.text_input("Enter the topic:")
num_questions = st.number_input("Enter the number of questions:", min_value=1, max_value=1000, value=10)

if st.button("Generate MCQs"):
    if topic:
        try:
            mcqs = generate_mcqs(topic, num_questions)
            save_to_file('questions_prompt.txt', mcqs)
            st.success("MCQs generated and saved to questions_prompt.txt.")
             
            # Convert text file to JSON
            convert_txt_to_json('questions_prompt.txt', 'questions_prompt.json')
            st.success("Text file converted to JSON.")

            
            # Convert JSON file to CSV
            convert_json_to_csv('questions_prompt.json', 'questions_prompt.csv')
            st.success("JSON file converted to CSV.")
            
            st.text_area("Generated MCQs", mcqs, height=300)
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            logging.exception("Exception occurred")

             # Step 2: Create the table in the database (if it doesn't already exist)
            create_table_for_mcqs()
                    #   # Step 3: Insert the generated MCQs into the database
            if mcqs:
                insert_mcqs_into_db(mcqs)
                st.success(f"MCQs for topic '{topic}' generated and saved to the database.")
            else:
                st.error("Failed to generate MCQs.") 
    else:
        st.warning("Please enter a topic.")

# Step 1: Automatically read the MCQs from the existing text file
if os.path.exists(text_filename):
    with open(text_filename, 'r', encoding='utf-8') as file:
        mcqs_text = file.read()

    st.success(f"MCQs loaded from {text_filename}")

    # Step 2: Parse MCQs from the text file and insert them into the database
    mcqs = parse_mcqs_from_text(mcqs_text)
    create_table_for_mcqs()  # Ensure the table exists
    insert_mcqs_into_db(mcqs)
    st.success("MCQs inserted into the database.")

    # Step 3: Convert text file to JSON
    convert_txt_to_json(text_filename, json_filename)
    st.success(f"MCQs text file converted to JSON: {json_filename}")

    # Step 4: Convert JSON file to CSV
    convert_json_to_csv(json_filename, csv_filename)
    st.success(f"MCQs JSON file converted to CSV: {csv_filename}")

    # Provide download links for generated files
    if os.path.exists(json_filename):
        with open(json_filename, "rb") as f:
            st.download_button("Download MCQs JSON", f, json_filename)

    if os.path.exists(csv_filename):
        with open(csv_filename, "rb") as f:
            st.download_button("Download MCQs CSV", f, csv_filename)

else:
    st.error(f"File {text_filename} not found. Please create or upload the file.")


