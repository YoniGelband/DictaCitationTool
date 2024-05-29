import json
import requests
import webbrowser
import os
import re
import time
from collections import Counter
from zipfile import ZipFile
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

DOWNLOAD_PATH = config['paths']['downloads']
STORE_FILE_PATH = config['paths']['store_files']

START_INDEX = config.getint('indexes', 'START_INDEX')
END_INDEX = config.getint('indexes', 'END_INDEX')
COMMON_WORDS_DELETE = config.getint('indexes', 'COMMON_WORDS_DELETE')
COUNTED_WORD_DISPLAY = config.getint('indexes', 'COUNTED_WORD_DISPLAY')


def parseBook(book):
    starter_word_count = Counter()
    closer_word_count = Counter()
    common_word_count = Counter()

    if not os.path.exists(STORE_FILE_PATH + book['fileName']):
        book_path = downloadPages(book['fileName'])
    else:
        book_path = STORE_FILE_PATH + book['fileName']
        print(f"Skipping {book['fileName']}, already downloaded")

    # get json pages file
    parsePages(book_path, starter_word_count, closer_word_count, common_word_count)
    parseCounter(starter_word_count, common_word_count.most_common(COMMON_WORDS_DELETE))
    parseCounter(closer_word_count, common_word_count.most_common(COMMON_WORDS_DELETE))

    return {
        'starter_most_common': dict(starter_word_count.most_common(COUNTED_WORD_DISPLAY)),
        'closer_most_common': dict(closer_word_count.most_common(COUNTED_WORD_DISPLAY))
    }


def getPagesFile(file_url):
    if file_url.startswith('http'):
        # It's a webpage URL, fetch the data using requests
        response = requests.get(file_url)
        if response.status_code == 200:
            # Check if the response is successful (status code 200)
            try:
                data = json.loads(response.text)
                return data
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from {file_url}: {e}")
                return None
        else:
            print(f"Failed to fetch data from {file_url}. Status code: {response.status_code}")
            return None

    elif file_url.endswith('.json'):
        # It's a local JSON file path, read and load the file
        try:
            with open(file_url, 'r', encoding='utf-8') as file:
                data = json.load(file)
                return data
        except FileNotFoundError:
            print(f"File not found: {file_url}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {file_url}: {e}")
            return None

    else:
        print(f"Unsupported file URL format: {file_url}")
        return None


def downloadPages(book_file_name):
    response_json = getPagesFile('https://files.dicta.org.il/' + book_file_name + '/pages.json')
    extract_to = STORE_FILE_PATH + book_file_name

    # Create a directory for extraction
    if not os.path.exists(extract_to):
        os.makedirs(extract_to)
        print(f"{book_file_name} pages downloading...")

    for page in response_json:
        if page['fileName'].endswith('.html'):
            continue
        filename = page['fileName']
        file_url = 'https://files.dicta.org.il/' + book_file_name + '/' + filename
        file_path = DOWNLOAD_PATH + filename

        file_json = re.sub('zip$', 'json', filename)
        path_json = STORE_FILE_PATH + book_file_name + '/' + file_json

        # Check if the file already exists
        if os.path.exists(path_json):
            downloaded = True
            continue

        if not os.path.exists(file_path):
            downloaded = False
            # Download the file using requests
            with requests.get(file_url, stream=True) as response:
                response.raise_for_status()

                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

            # Wait for file to download
            while not os.path.exists(file_path):
                time.sleep(1)
        else:
            downloaded = True

        filename_json = re.sub('zip$', 'json', filename)
        # Process the zip file
        if not os.path.exists(extract_to + '/' + filename_json):
            with ZipFile(file_path, 'r') as zip_obj:
                zip_obj.extractall(extract_to)
    print('downloads completed successfully!' if not downloaded else 'book already downloaded!')
    return extract_to


def parsePages(book_path, starter_word_count, closer_word_count, common_word_count):
    # Iterate through the files in the directory
    print('Parsing pages...')
    for root, dirs, files in os.walk(book_path):
        for page_file in files:
            file_path = os.path.join(root, page_file)
            parsePage(file_path, starter_word_count, closer_word_count, common_word_count)
    print('parsing completed successfully!')


def newPage(response_json, page_name):
    found_file = False
    for page in response_json:
        if (page['displayName'] == page_name):
            filename = page['fileName']
            found_file = True
            break
    if not found_file:
        print("Page not found")
        exit(1)
    file_path = DOWNLOAD_PATH + filename
    webbrowser.open('https://files.dicta.org.il/prietshaim/' + filename)

    # waiting for download to complete
    while not os.path.exists(file_path):
        pass

    with ZipFile(file_path, 'r') as zip_obj:
        zip_obj.extractall()
        files = zip_obj.namelist()
        for file in files:
            filename = file

    return filename


def parallelEncountered(parallelID, encountered_nums):
    for num in parallelID:
        if num in encountered_nums:
            return True

    return False


def parsePage(page_file, starter_word_count, closer_word_count, common_word_count):
    with open(page_file, 'r', encoding='utf-8') as file:
        words = json.load(file)

    # tracker of numbers already encountered
    encountered_nums = []
    i = 0

    while (i < len(words['tokens'])):
        token = words['tokens'][i]
        common_word_count[token['str']] += 1

        # checking if word is a parallel and then skipping on words within the parallel
        if 'sourcesPostProcessedIDs' in token:
            if not parallelEncountered(token['sourcesPostProcessedIDs'], encountered_nums):
                parallelID = token['sourcesPostProcessedIDs']
                encountered_nums.extend(n for n in parallelID)
                updateCounter(starter_word_count, words, i)

            # skip over parallelID
            while parallelID == token['sourcesPostProcessedIDs']:
                if i + 1 >= len(words['tokens']):
                    break
                i += 1
                token = words['tokens'][i]
                if 'sourcesPostProcessedIDs' not in token or parallelID != token['sourcesPostProcessedIDs']:
                    x = i
                    updateCounter(closer_word_count, words, x)
                    parseCounter(closer_word_count, common_word_count.most_common(20))
                    break

                pass
        i += 1


def createString(words, x):
    global START_INDEX, END_INDEX
    if x < 10:
        START_INDEX = 0
        END_INDEX = 20 - (10 - x)
    elif x + 11 >= len(words['tokens']):
        END_INDEX = len(words['tokens']) - x - 1

    string = ''
    for j in range(START_INDEX, END_INDEX):
        if (x + j < len(words['tokens'])):
            if words['tokens'][x + j]['str'] != ' ':
                if words['tokens'][x + j]['str'] == 'עכ"ל':
                    string += '[MASK]'
                    continue
                string += words['tokens'][x + j]['str'] + ' '
    return string


def applyBert(string):
    berel_url = "http://54.213.196.28:8080/api"
    model = "ckpt_34800"

    body = {"data": string, "models": [model]}
    res = requests.post(berel_url, json=body)
    options = res.json()
    # options = [r[model] for r in options if r][0]
    print(options)


def updateCounter(word_counter, words, x):
    global START_INDEX, END_INDEX
    if x < 10:
        START_INDEX = 0
        END_INDEX = 20 - (10 - x)
    elif x + 11 >= len(words['tokens']):
        END_INDEX = len(words['tokens']) - x - 1

    for j in range(START_INDEX, END_INDEX):
        if (x + j < len(words['tokens'])):
            if words['tokens'][x + j]['str'] != ' ':
                word = words['tokens'][x + j]['str']
                # Bert option 1: find the common words while parsing
                # (create a string builder function and pass the string to bert)
                # Bert option 2: find the common words after parsing, itterate through the entire book
                # each time the word is encountered, fire a function to build a string and send it to burt
                word_counter[word] += 1


def parseCounter(word_counter, common_words):
    # Create a list of words to delete to avoid modifying the dictionary during iteration
    words_to_delete = [word for word, _ in common_words if word in word_counter]

    # Delete the words from the counter
    for word in words_to_delete:
        del word_counter[word]


def main():
    # initialize the dictionary
    books_dict = {}
    results_bool = False

    if os.path.exists('results.json'):
        results_bool = True
        with open('results.json', 'r', encoding='utf-8') as results:
            res = json.load(results)
    # open books json file
    try:
        with open('test.json', 'r', encoding='utf-8') as file:
            books = json.load(file)
            for book in books:
                if results_bool:
                    if (book['fileName'] in res):
                        print(f"Skipping {book['fileName']}, already processed")
                        continue

                # update dictionary with the book's most common words
                books_dict[book['fileName']] = parseBook(book)

        # Write the most common words to a JSON file
        if not results_bool:
            with open('results.json', 'w', encoding='utf-8') as file:
                json.dump(books_dict, file, ensure_ascii=False, indent=4)
        else:
            with open('results.json', 'w', encoding='utf-8') as file:
                res.update(books_dict)
                json.dump(res, file, ensure_ascii=False, indent=4)
        print('program complete, look for the results.json file')

    except FileNotFoundError:
        print(f"File not found")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from books.json: {e}")


main()
