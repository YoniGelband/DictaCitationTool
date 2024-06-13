import json
import os

def openResults(file_name):
    if not os.path.exists(file_name):
        print ("file not found")
        return {}
    with open(file_name, 'r', encoding='utf-8') as file:
        return json.load(file)

def createList(position_dict):
    for key in position_dict:
        print (position_dict[key])
def writeToJson(position_list, file_name):
    if os.path.exists(file_name):
        with open(file_name, 'r', encoding='utf-8') as file:
            data = json.load(file)
            data.update(position_list)
    else:
        with open(file_name, 'w', encoding='utf-8') as file:
            json.dump(position_list, file)

def main():
    starter_dict = openResults('starter_bertResults.json')
    closer_dict = openResults('closer_bertResults.json')
    starter_list = createList(starter_dict)
    closer_list = createList(closer_dict)
    #writeToJson(starter_list, 'starter_positions.json')
    #writeToJson(closer_list, 'closer_positions.json')
