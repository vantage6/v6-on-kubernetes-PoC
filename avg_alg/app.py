import argparse
import csv
import time
import platform
import socket
import requests
import psutil


def get_ip_addresses(family):
    for interface, snics in psutil.net_if_addrs().items():
        for snic in snics:
            if snic.family == family:
                yield (interface, snic.address)


def is_internet_reachable():
    try:
        requests.get('https://8.8.8.8', timeout=1)
        return True
    except requests.exceptions.RequestException:
        return False


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


    ipv4s = list(get_ip_addresses(socket.AF_INET))
    ipv6s = list(get_ip_addresses(socket.AF_INET6))

    print(f'Host architecture:{platform.uname()[4]}')
    print("IPv4 Addresses:")
    for interface, ipv4 in ipv4s:
        print(f"{interface}: {ipv4}")

    print("\nIPv6 Addresses:")
    for interface, ipv6 in ipv6s:
        print(f"{interface}: {ipv6}")

    internet_reachable = is_internet_reachable()
    print(f'Internet access test result:{"successful(no isolation)" if internet_reachable else "failed(isolated env.)"}')    
    print('Waiting one minute before finishing the job (to simulate a more expensive task and to give you time to login on the POD)')
    time.sleep(120)
