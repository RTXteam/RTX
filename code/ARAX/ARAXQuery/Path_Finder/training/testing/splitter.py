import json
import random


def split_data(train_percentage=0.8):
    with open('../data/DrugBank_aligned_with_KG2.json', 'r') as file:
        data = json.load(file)
    items = list(data.items())

    random.shuffle(items)

    split_index = int(len(items) * train_percentage)

    dict1_items = items[:split_index]
    dict2_items = items[split_index:]

    training = dict(dict1_items)
    testing = dict(dict2_items)

    with open('../data/training.json', 'w') as file1:
        json.dump(training, file1, indent=4)

    with open('../data/testing.json', 'w') as file2:
        json.dump(testing, file2, indent=4)


if __name__ == "__main__":
    split_data()
