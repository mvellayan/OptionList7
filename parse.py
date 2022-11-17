import glob
import re
import json
import csv


def load_data(data_dir: str, max_files: int = 999):
    # Get CSV files list from a folder
    file_str = data_dir + "*.csv"
    csv_files = glob.glob(file_str)
    csv_files = csv_files[0:max_files]
    if len(csv_files) == 0:
        print("No files in directory ", file_str, csv_files)
        exit(1)
    # print("          loading " + file_str + " file count: " + str(len(csv_files)))
    # Read each CSV file into DataFrame
    # This creates a list of dataframes
    all_file_lines = []
    for file in csv_files:
        with open(file, "r") as f:
            lines = f.readlines()
            all_file_lines.extend(lines)
    return all_file_lines


def get_next_table(i_working, i_max, lines):
    start = i_working

    while start < i_max:
        if "{" in lines[start] and "}" not in lines[start]:
            break
        else:
            start += 1
    end = start
    while end <= i_max:
        if "}" in lines[end] and "{" not in lines[end]:
            break
        else:
            end += 1
    # print(f"{lines[start]}\n{lines[end]}\n")
    return start, end


def get_table_name_description(start, end, i_max, lines):
    if "{" in lines[start]:
        table_name = re.sub('[^ \.\,\_\:\-a-zA-Z0-9]+', '', lines[start])
    else:
        print(f"start of table index [{start}: {lines[start]}] does not contain bracket")
        exit(1)
    table_description = re.sub('[^ \.\,\_\:\-a-zA-Z0-9]+', '', lines[start + 1][12:])
    return table_name, table_description


def get_field_attributes(start, end, table_name, lines):
    fields = []
    field = {}
    skip_line = False
    for line_idx in range(start, end + 1):

        if skip_line:
            skip_line = False
            continue

        line = lines[line_idx]
        if len(line.strip()) == 0:
            print(line, line.strip())
            continue

        if ord(line[0]) in range(97,123):
            if len(field) > 0:
                fields.append(field)
                field = {}
            field["table_name"] = table_name
            w = line.split("\t")
            field["field_name"] = w[0].strip()
            field["field_type"] = w[1].strip()
        else:
            l1 = line.strip()
            if ":" in l1:
                w = l1.split(":")
                if w[0].strip() == "Enum":
                    field[w[0].strip()] = lines[line_idx+1]
                    skip_line = True
                else:
                    field[w[0].strip()] = w[1].strip()
            else:
                if field.get("description", "empty") == "empty":
                    field["description"] = l1
                else:
                    field["description"] = field["description"] + "\n" + l1

    if len(field) > 0:
        fields.append(field)
    return fields


def write_to_csv(data, file_name):
    data_file = open(file_name, 'w')
    csv_writer = csv.writer(data_file)
    header = data[0].keys()
    csv_writer.writerow(header)
    for item in data:
        csv_writer.writerow(item.values())


all_tables = []
all_fields = []

def main():
    lines = load_data("/Users/Muthu/Desktop/SWAFS/udl/scraping/")
    i_working = 0
    i_max = len(lines)
    ctr = 0

    while i_working < i_max:
        ctr += 1

        start, end = get_next_table(i_working, i_max, lines)
        t_name, t_description = get_table_name_description(start, end, i_max, lines)

        all_tables.append({"name": t_name, "description": t_description})

        # store fields dictionary
        fields_dictionary = get_field_attributes(start + 2, end-1, t_name, lines)
        all_fields.extend(fields_dictionary)
        i_working = end + 1

        print(str(ctr) + ":  [" + t_name + "] [" + t_description[:90] + "]", len(all_fields), len(all_tables))

    write_to_csv(all_tables, "tables.csv")
    write_to_csv(all_fields, "fields.csv")

main()
