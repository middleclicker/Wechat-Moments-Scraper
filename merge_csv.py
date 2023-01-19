import csv

# Very Basic Merge
# TODO: Implement row by row data merge, not just uuid checks.

# ['uuid', 'author', 'content', 'media', 'time', 'likes', 'comments', 'scraped_date', 'contributor']
def loader(fileName):
    all_pyq = []
    with open(fileName) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        for row in csv_reader:
            pyq_data = {}
            if line_count > 0:
                pyq_data["uuid"] = row[0]
                pyq_data["author"] = row[1]
                pyq_data["content"] = row[2]
                pyq_data["media"] = row[3]
                pyq_data["time"] = row[4]
                pyq_data["likes"] = row[5]
                pyq_data["comments"] = row[6]
                pyq_data["scraped_date"] = row[7]
                pyq_data["contributor"] = row[8]
                all_pyq.append(pyq_data)

            line_count += 1

    return all_pyq


def search(data, id):
    for row in data:
        if id == row["uuid"]:
            return True
    return False

def merge(filename1, filename2):
    file1 = loader(filename1) # Combined.csv
    file2 = loader(filename2)

    for data in file1:
        uuid = data["uuid"]
        if not search(file2, uuid):
            file2.append(data)

    unsuccessful = []
    filename = "combined.csv"
    with open(filename, 'w', newline='') as file:
        header = ['uuid', 'author', 'content', 'media', 'time', 'likes', 'comments', 'scraped_date', 'contributor']
        writer = csv.DictWriter(file, fieldnames=header)
        writer.writeheader()
        for row in file2:
            try:
                writer.writerow(row)
            except Exception as e:
                unsuccessful.append(row)
