import argparse
import csv
import time
import platform
import socket


def test_external_connectivity(ip_address='8.8.8.8', port=80):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)        
        #Connection timeout
        s.settimeout(5)
        #Connection attempt
        s.connect((ip_address, port))
        
        # If the connection is successful, close the socket and return False
        s.close()
        return False
    except socket.error as e:
        # If there's an error (which is expected if the pod is isolated), return True
        return True


if __name__ == '__main__':

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


    print(f'Host architecture:{platform.uname()[4]}')
    internet_connectivity = test_external_connectivity()
    print(f'Internet access test result:{"successful(no isolation)" if internet_connectivity else "failed(isolated env.)"}')    
    print('Waiting one minute before finishing the job (to simulate a more expensive task and to give you time to login on the POD)')
    time.sleep(60)
