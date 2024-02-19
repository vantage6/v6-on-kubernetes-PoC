# Use the official Python base image
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Copy the Python script into the container
COPY *.py reqs.txt /app/

# Install python dependencies
RUN pip install -r reqs.txt

# Set the entrypoint to the Python script
ENTRYPOINT ["python", "app.py"]

