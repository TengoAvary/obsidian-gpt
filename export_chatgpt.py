import json
from datetime import datetime
import os

# load config from config.json
with open('config.json', 'r') as file:
    config = json.load(file)

def read_conversations(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def get_conversations(conversation_data):
    conversations = []
    for item in conversation_data:
        title = item['title']
        filename = datetime.fromtimestamp(item['create_time']).strftime('%Y%m%d%H%M%S')
        create_date = datetime.fromtimestamp(item['create_time']).strftime('%Y-%m-%d')
        messages = []
        for key, mapping_item in item['mapping'].items():
            if mapping_item['message']:
              author = mapping_item['message']['author']['role']
              if author == 'assistant':
                author = 'GPT'
              elif author == 'user':
                author = 'You'
              message = mapping_item['message']['content']['parts'][0]
              if author != 'system':
                messages.append({
                    'author': author,
                    'message': message
                })
        conversations.append({
            'title': title,
            'filename': filename,
            'create_date': create_date,
            'messages': messages
        })
    return conversations

def create_markdown(conversation):
    title = conversation['title']
    filename = conversation['filename']
    create_date = conversation['create_date']
    messages = conversation['messages']

    markdown_content = f"From a conversation with GPT on {create_date}\n\n"

    for message_item in messages:
        author = message_item['author']
        message = message_item['message']
        markdown_content += f"**{author}**:\n{message}\n\n"

    return markdown_content

def main():
    input_file = 'data/conversations.json'
    output_dir = config['obsidian-dir'] + 'ChatGPT conversations/ChatGPT'
    # create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    conversation_data = read_conversations(input_file)
    conversations = get_conversations(conversation_data)
    for conversation in conversations:
        markdown_content = create_markdown(conversation)
        filename = conversation['filename']
        title = conversation['title']
        # replace forward slashes with hyphens
        title = title.replace('/', '--')
        # remove trailing full stop if present
        if title[-1] == '.':
            title = title[:-1]
        # replace colons with hyphens
        title = title.replace(':', ' -')
        # remove question marks and quotation marks, and new lines
        title = title.replace('?', '')
        title = title.replace('"', '')
        title = title.replace('\n', '')
        file_path = f"{output_dir}/{filename} - {title}.md"
        # if the file already exists, remove it
        if os.path.exists(file_path):
            os.remove(file_path)
        # write markdown file
        with open(file_path, 'w') as file:
            print(f"Writing {file_path}")
            file.write(markdown_content)

def remove_close_duplicates():
  # remove files that are identical up to a trailing full stop, in output_dir
  output_dir = config['obsidian-dir'] + 'ChatGPT conversations/ChatGPT'
  files = os.listdir(output_dir)
  files.sort()
  print(files)
  for i in range(len(files) - 1):
    file = files[i]
    next_file = files[i + 1]
    with open(f"{output_dir}/{file}", 'r') as file_open:
      content = file_open.read()
    with open(f"{output_dir}/{next_file}", 'r') as next_file_open:
      next_content = next_file_open.read()
    if content == next_content:
      # os.remove(f"{output_dir}/{next_file}")
      print(f"{file} and {next_file} are identical")
      # remove the one with the extra full stop
      if '..' in file:
        os.remove(f"{output_dir}/{file}")
      else:
        os.remove(f"{output_dir}/{next_file}")

if __name__ == '__main__':
    main()
    # remove_close_duplicates()
