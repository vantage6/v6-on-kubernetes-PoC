from flask import Flask, request
import requests
import psutil
import socket
import platform

app = Flask(__name__)

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


@app.route('/', methods=['GET', 'POST'])
def handle_request():
    if request.method == 'POST':
        data = request.data.decode('utf-8')  # Decode the data if it's POST
    else:
        data = request.args.to_dict()  # Get query parameters if it's GET

    return f"Message-forwarded: {data}"

if __name__ == '__main__':
    ipv4s = list(get_ip_addresses(socket.AF_INET))
    ipv6s = list(get_ip_addresses(socket.AF_INET6))

    print('Running HTTP Proxy Server at')
    print(f'Host architecture:{platform.uname()[4]}')
    print("IPv4 Addresses:")
    for interface, ipv4 in ipv4s:
        print(f"{interface}: {ipv4}")

    print("\nIPv6 Addresses:")
    for interface, ipv6 in ipv6s:
        print(f"{interface}: {ipv6}")
    
    internet_reachable = is_internet_reachable()
    print(f'The proxy server {"has outbound traffic enabled" if internet_reachable else "has outbound traffic BLOCKED"}')    


    app.run(host='0.0.0.0', port=8080)
