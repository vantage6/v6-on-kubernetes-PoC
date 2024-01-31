# Use the official Python base image
FROM python:3.11

# Set the working directory in the container
WORKDIR /app

# Copy the Python script into the container
COPY *.py reqs.txt /app/

RUN pip install -r reqs.txt

# Set the entrypoint to the Python script
ENTRYPOINT ["python", "node.py"]

