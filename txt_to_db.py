import streamlit as st
import json  # Fix for the 'json' is not defined error
import logging  # Fix for the 'logging' is not defined error
from db_handler import create_table_for_mcqs, insert_mcqs_into_db

# Define your MCQ parser function
import re

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
            print(f"Error parsing question: {q}")
            print(f"Error: {str(e)}")

    return mcqs

# Streamlit application
st.title("MCQ Generator")

# Step 1: Generate MCQs from a file
st.header("Step 1: Generate MCQs")
file_upload = st.file_uploader("Upload a text file with MCQs", type=["txt"])

if file_upload is not None:
    try:
        # Read the uploaded text file
        text = file_upload.read().decode('utf-8')

        # Parse the MCQs from the uploaded text
        mcqs = parse_mcqs_from_text(text)

        # Display the parsed MCQs
        st.success(f"Parsed {len(mcqs)} MCQs from the file.")
        st.text_area("Parsed MCQs", json.dumps(mcqs, indent=4), height=300)

        # Step 2: Create the table in the database (if it doesn't already exist)
        create_table_for_mcqs()

        # Step 3: Insert the parsed MCQs into the database
        if mcqs:
            insert_mcqs_into_db(mcqs)
            st.success(f"MCQs inserted into the database.")
        else:
            st.error("No MCQs to insert.")
    
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        logging.exception("Exception occurred")
