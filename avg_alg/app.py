import argparse
import csv
import time
import platform
import socket
import requests
import psutil


#FQDN must match internal domain name defined on proxy_pod_deployment.yaml
PROXY_FQDN = 'v6proxy.v6proxy-subdomain.v6-jobs'
PROXY_PORT = '8080'


def get_ip_addresses(family):
    for interface, snics in psutil.net_if_addrs().items():
        for snic in snics:
            if snic.family == family:
                yield (interface, snic.address)


def is_proxy_reachable():
    try:
        requests.get(f'http://{PROXY_FQDN}:{PROXY_PORT}', timeout=1)
        return True
    except requests.exceptions.RequestException:
        return False


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
    print(f'Internet access :{"ENABLED" if internet_reachable else "DISABLED"}')    

    proxy_rechable = is_proxy_reachable()
    print(f'V6-proxy status :{f"REACHABLE at {PROXY_FQDN}" if proxy_rechable else f"DISABLED or unreachable at {PROXY_FQDN}"}')    

    print('Waiting five minutes before finishing the job (to simulate a more expensive task and to give you time to login on the POD)')
    time.sleep(300)
