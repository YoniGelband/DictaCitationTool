import json
import requests
import configparser
import os

config = configparser.ConfigParser()
config.read('config.ini')

START_INDEX = config.getint('indexes', 'START_INDEX')
END_INDEX = config.getint('indexes', 'END_INDEX')

def parsePages(book_path, citation_words, json_file_name):
    # Iterate through the files in the directory
    print('Parsing pages...')
    pages_dict = {}
    for root, dirs, files in os.walk(book_path):
        if os.path.exists(json_file_name + '.json'):
            with open (json_file_name + '.json', 'r', encoding='utf-8') as file:
                data = json.load(file)
        else:
            data = {}
        for page_file in files:
            if page_file in data:
                print (f'{page_file} already parsed, skipping...')
                continue

            print(f'parsing {page_file}...')
            page_path = os.path.join(root, page_file)
            pages_dict[page_file] = parsePage(page_path, citation_words)

            writeToJson(pages_dict, json_file_name)
    print('parsing completed successfully!')
    return pages_dict



def parsePage(page_file, closer_words):
    with open(page_file, 'r', encoding='utf-8') as file:
        words = json.load(file)
    list_of_masked_dicts = []
    i = 0
    while (i < len(words['tokens'])):
        token = words['tokens'][i]
        if token['str'] in closer_words:
            string = createString(words, i)
            masked_string = createMaskedString(words, i)
            masked_list = applyBert(masked_string)
            masked_dict = (createMaskedDict(token['str'], string, masked_list))
            list_of_masked_dicts.append(masked_dict)
        i += 1

    return list_of_masked_dicts

def createMaskedDict(hidden_word, string, masked_list):
    return {
        'hiddenWord': hidden_word,
        'originalString': string,
        'bertSuggestions': masked_list
    }
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
            string += words['tokens'][x + j]['str']
    return string
def createMaskedString(words, x):
    global START_INDEX, END_INDEX
    wanted_word_index = x
    if x < 10:
        START_INDEX = 0
        END_INDEX = 20 - (10 - x)
    elif x + 11 >= len(words['tokens']):
        END_INDEX = len(words['tokens']) - x - 1

    masked_string = ''
    for j in range(START_INDEX, END_INDEX):
        if (j == 0):
            masked_string += '[MASK]'
            continue

        if (x + j < len(words['tokens'])):
                masked_string += words['tokens'][x + j]['str']
    return masked_string
def applyBert(string):
    berel_url = "http://54.213.196.28:8080/api"
    model = "ckpt_34800"
    body = {"data": string, "models": [model]}
    res = requests.post(berel_url, json=body)
    options = res.json()
    #options = [r[model] for r in options if r][0]
    for list in options:
        if len(list) > 0:
            return list['mlmbert_34800']

def writeToJson(word_dict, filename):
    file_path = filename + '.json'
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(word_dict, file, ensure_ascii=False, indent=4)
    else:
        # Read existing data
        with open(file_path, 'r', encoding='utf-8') as file:
            if os.path.getsize(file_path) == 0:
                res = {}
            else:
                res = json.load(file)

        # Update the existing data with new data
        res.update(word_dict)

        # Write the updated data back to the file
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(res, file, ensure_ascii=False, indent=4)
    print('writing to json successful!')
def getWords():
    with open('results.json', 'r', encoding='utf-8') as file:
        data = json.load(file)

        for book in data:
            if book == 'prietshaim':
                starter_list = list(data[book]['starter_most_common'].items())[:10]
                end_list = list(data[book]['closer_most_common'].items())[:10]
                return ([word for word, count in starter_list],
                        [word for word, count in end_list])
def main():

    words = getWords()
    starter_words = words[0]
    closer_words = words[1]
    book_file = 'prietshaim'
    parsePages(book_file, starter_words, 'starter_bertResults')
    parsePages(book_file, closer_words, 'closer_bertResults')
    print('Program complete!')

main()


