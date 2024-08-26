import streamlit as st
import os
import json
import csv
from langchain.llms import GooglePalm
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Define your LLM instance
api_key = "AIzaSyCk6H3OH1GCAetNELW0frBeTGsQ7xMewNc"
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
    "Blooms Taxonomy: Evaluate\n"
    "Course Outcome: CO1\n"
    "Program Outcome: PO1\n\n"
    "Ensure while giving the correct option number please don't give the correct answer text. "
    "The options are in a, b, c, d so you take it as 1, 2, 3, 4 and give the correct number. "
    "Ensure that each question has exactly one correct answer and three incorrect options. "
    "Provide the correct answer in full text. "
    "Inside the correct answer section, provide only the correct answer, not the option or any other words or symbols. "
    "Don't use ** before or after the question and the correct answer or anywhere else. "
    "Do not include any snippet-based MCQs."
)

# Function to generate MCQs
def generate_mcqs(topic, num_questions):
    prompt = prompt_template.format(topic=topic, num_questions=num_questions)
    response = llm(prompt)
    return response

# Function to write the output to a file
def save_to_file(filename, text):
    try:
        with open(filename, 'w') as file:
            file.write(text)
        logging.info(f"File saved: {filename}")
    except Exception as e:
        logging.error(f"Failed to save file {filename}: {e}")

# Function to convert text to JSON
def convert_txt_to_json(txt_file_path, json_file_path):
    """Convert a text file with MCQs into a JSON file with each question in a separate object."""

    def parse_question_blocks(lines):
        """Parse lines into a list of questions."""
        questions = []
        question = {}
        in_code_block = False

        for line in lines:
            line = line.strip()
            if line.startswith("Q"):
                if question:
                    questions.append(question)
                    question = {}
                question["question"] = line.lstrip("Q1. ").strip()
            elif line.startswith("```"):
                in_code_block = not in_code_block
                if in_code_block:
                    question["code"] = ""
                else:
                    question["code"] = ""  # Remove code block content
            elif line.startswith("Correct answer:"):
                answer_number = line.replace("Correct answer:", "").strip()
                question["answer"] = answer_number  # Directly use the provided number
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
            elif line.startswith("a)") or line.startswith("b)") or line.startswith("c)") or line.startswith("d)"):
                if "options" not in question:
                    question["options"] = {}
                key = line[0]
                question["options"][key] = line[2:].strip()
        
        if question:
            questions.append(question)
        
        return questions

    try:
        with open(txt_file_path, 'r', encoding='utf-8') as txt_file:
            lines = txt_file.readlines()

        questions = parse_question_blocks(lines)

        for q in questions:
            q["question"] = q["question"].lstrip("0123456789. ").strip()  # Strip question numbers
            
            if "options" in q:
                options = q.pop("options")
                for i, (key, value) in enumerate(sorted(options.items()), start=1):
                    q[f"ans{i}"] = value

            # Add default values
            q["blooms_taxonomy"] = "Evaluate"
            q["course_outcome"] = "CO1"
            q["program_outcome"] = "PO1"

        # Ensure the 'answer' field contains the option number
        # No conversion needed, directly use the number

        with open(json_file_path, 'w', encoding='utf-8') as json_file:
            json.dump(questions, json_file, indent=4)
            
        print(f"Successfully converted '{txt_file_path}' to '{json_file_path}'")
    
    except Exception as e:
        print(f"An error occurred: {e}")


# Function to convert JSON to CSV
def convert_json_to_csv(json_file_path, csv_file_path):
    """Convert a JSON file with MCQs into a CSV file."""
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)

        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
        
            # Extract headers from the first dictionary in the list
            headers = data[0].keys()
            csv_writer.writerow(headers)
        
            # Write each dictionary as a row in the CSV file
            for entry in data:
                csv_writer.writerow(entry.values())

        logging.info(f"Successfully converted '{json_file_path}' to '{csv_file_path}'")
    
    except Exception as e:
        logging.error(f"An error occurred: {e}")

# Streamlit application
st.title("MCQ Generator")

# Step 1: Generate MCQs
st.header("Step 1: Generate MCQs")
topic = st.text_input("Enter the topic:")
num_questions = st.number_input("Enter the number of questions:", min_value=1, max_value=1000, value=10)

if st.button("Generate MCQs"):
    if topic:
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
    else:
        st.warning("Please enter a topic.")

# Optionally, download the generated files
if os.path.exists("questions_prompt.txt"):
    with open("questions_prompt.txt", "rb") as f:
        st.download_button("Download MCQs Text", f, "questions_prompt.txt")

if os.path.exists("questions_prompt.json"):
    with open("questions_prompt.json", "rb") as f:
        st.download_button("Download MCQs JSON", f, "questions_prompt.json")

if os.path.exists("questions_prompt.csv"):
    with open("questions_prompt.csv", "rb") as f:
        st.download_button("Download MCQs CSV", f, "questions_prompt.csv")
