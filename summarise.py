import openai
import os
import json
import requests
from pathlib import Path
import tiktoken
from tqdm import tqdm
import re

# load config from config.json
with open('config.json', 'r') as file:
    config = json.load(file)

OBSIDIAN_DIR = config['obsidian-dir']
EXCLUSIONS = config['conversation-exclusions']

keyword_replacements = {
    'Artificial Intelligence': 'AI',
    'Artificial intelligence': 'AI',
    'artificial intelligence': 'AI',
    'Artificial Intelligence (AI)': 'AI',
    'Artificial intelligence (AI)': 'AI',
    'artificial intelligence (AI)': 'AI',
}

openai.api_key = config['api-key']

bullet_point_system_message = "You are a helpful assistant. Your role is to extract key information from a transcript of a conversation into a bullet point list. The list items should be actual factual information, or specific opinions expressed, not just records of what was discussed or explored. Always give specifics, instead of referring to vague concepts, objects, or things."

summary_system_message = "You are a helpful assistant. Your role is to summarize a transcript of a conversation in an essay format. The summary should be an accurate, and complete description of the conversation. It should be a few paragraphs in length. It should not include any information that was not actually discussed. Do not mention the word \"conversation\" or in any way refer to the fact that this is a summary of a conversation."

title_system_message = "You are a helpful assistant. Your role is to come up with an appropriate title for a given piece of text. The title should be very short, three words or fewer. Your answer should only include the title, and nothing else. Answer in a single line and enclose the title in quotation marks, e.g. \"Title\"."

keywords_system_message = "You are a helpful assistant. Your role is to give a list of 5 keywords that summarize the topics discussed in a given piece of text. The keywords should be given as a numbered list, with each item on a new line. Each keyword must be a single word."

def extract_items(text):
    pattern = re.compile(r'\d+[\.:)]\s?(.+?)(?:[,;]|$)', re.MULTILINE)
    matches = pattern.findall(text)
    return matches

def get_all_notes():
    # get all notes from obsidian vault
    # find all .md files in all folders
    # return list of paths to all files that are not hidden or in hidden folders
    all_notes = []
    for root, dirs, files in os.walk(OBSIDIAN_DIR):
        for file in files:
            if file.endswith(".md") and not file.startswith('.'):
                all_notes.append(file.replace('.md', ''))
    return all_notes

def get_existing_keywords():
    # gets existing keywords in the Obsidian vault, which are basically just the filenames but only those that are short enough to be keywords, or are not numerical
    notes = get_all_notes()
    keywords = []
    for note in notes:
        if len(note.split()) < 4 and not note.isnumeric():
            keywords.append(note)
    return keywords

def count_tokens(text):
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
    encoded = enc.encode(text)
    return len(encoded)

def get_gpt_response(system_message, prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        max_tokens=1024,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ]
    )
    response_text = response['choices'][0]['message']['content']
    return response_text

def split_content(content, max_tokens=1500):
    words = content.split()
    fragments = []
    current_fragment = []
    current_tokens = 0
    
    for word in words:
        tokens = count_tokens(word)
        if current_tokens + tokens > max_tokens:
            fragments.append(' '.join(current_fragment))
            current_fragment = [word]
            current_tokens = tokens
        else:
            current_fragment.append(word)
            current_tokens += tokens
    
    fragments.append(' '.join(current_fragment))
    return fragments

def summarise(content, fragment_max_tokens=1500):
    fragments = split_content(content, fragment_max_tokens)
    summaries = []

    print("Processing fragments...")
    for fragment in tqdm(fragments):
        prompt = f"Please provide a bullet point summary of the key ideas and conclusions reached in the following conversation:\n\n{fragment}\n\n"
        summary = get_gpt_response(bullet_point_system_message, prompt)
        summaries.append(summary)

    all_bullet_points = '\n'.join(summaries)
    if count_tokens(all_bullet_points) < 2800:
        prompt = f"Please write an essay using the following bullet points as a guide:\n\n{all_bullet_points}"
        print("Generating summary...")
        essay = get_gpt_response(summary_system_message, prompt)
        return essay
    else:
        return all_bullet_points
    
def get_title(text):
    prompt = f"Please provide a title for the following essay:\n\n{text}"
    response = get_gpt_response(title_system_message, prompt)
    # extract title from response, enclosed in quotation marks
    title = response.split('"')[1]
    return title

def replace(keyword):
    if keyword in keyword_replacements:
        return keyword_replacements[keyword]
    else:
        return keyword

def get_keywords(text):
    existing_keywords = get_existing_keywords()
    prompt = f"Please provide a list of 5 keywords for the following essay:\n\n{text}\n\nEach keyword must be a single word. Here are some existing keywords that are relevant to the user: {'; '.join(existing_keywords)}. Include any of these that are relevant to the essay, and add any new keywords that are relevant to the essay."
    response = get_gpt_response(keywords_system_message, prompt)
    keywords = extract_items(response)
    # remove trailing punctuation from each keyword
    keywords = [keyword.strip('.,;:') for keyword in keywords]
    keywords = [replace(keyword.strip()) for keyword in keywords]
    return keywords

def enclose_keyword(text, keyword):
    keyword_pattern = re.compile(f'({keyword})', re.IGNORECASE)
    return keyword_pattern.sub(r'[[\1]]', text)

def process_files(input_dir, output_dir, log_file):

    with open(log_file, 'r') as log_f:
        processed_files = log_f.read().splitlines()

    for filename in os.listdir(input_dir):
        try:
            if filename not in processed_files and filename not in EXCLUSIONS:
                with open(f'{input_dir}/{filename}', 'r') as file:
                    content = file.read()
                summary = summarise(content)

                title = get_title(summary)
                print(f"Title: {title}")

                keywords = get_keywords(summary)

                for keyword in keywords:
                    summary = enclose_keyword(summary, keyword)

                keyword_string = ', '.join([f"[[{keyword}]]" for keyword in keywords])

                summary += f"\n\nKeywords: {keyword_string}"

                summary = f"_From conversation [[{filename.replace('.md', '')}]]_\n\n" + summary

                Path(output_dir).mkdir(parents=True, exist_ok=True)
                with open(f'{output_dir}/{title}.md', 'w') as out_file:
                    out_file.write(summary)

                with open(log_file, 'a') as log_f:
                    log_f.write(f'{filename}\n')
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"Error processing {filename}")
            print(e)

def main():
    input_directory = OBSIDIAN_DIR + 'ChatGPT conversations/ChatGPT/'
    output_directory = OBSIDIAN_DIR + 'ChatGPT summaries/'
    log_file_path = 'log_file.txt'

    if not os.path.exists(log_file_path):
        open(log_file_path, 'w').close()

    process_files(input_directory, output_directory, log_file_path)

if __name__ == '__main__':
    main()
