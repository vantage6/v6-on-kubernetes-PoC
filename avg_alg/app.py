import argparse
import csv
import time

# Parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('input_file', help='Input CSV file')
parser.add_argument('column_name', help='Name of the column to calculate average')
parser.add_argument('output_file', help='Output text file')
args = parser.parse_args()

print(f'Calculating avg of column {args.column_name} on file {args.input_file}')

# Open the CSV file
with open(args.input_file, 'r') as csv_file:
    csv_reader = csv.DictReader(csv_file)

    # Extract the specified column
    column_values = [float(row[args.column_name]) for row in csv_reader if args.column_name in row]

    # Calculate the average
    average = sum(column_values) / len(column_values) if column_values else 0

# Write the average to the output file
with open(args.output_file, 'w') as txt_file:
    txt_file.write(str(average))

print('Waiting one minute before finishing the job (to simulate a more expensive task and to give you time to login on the POD)')
time.sleep(60)
