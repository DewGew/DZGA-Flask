# Dockerfile for DZGA-Flask

# Install minimal Python 3.
FROM python:3-alpine

RUN mkdir -p config

COPY *.py /
COPY modules/ /modules/
COPY templates/ /templates/
COPY modules/ /modules/
COPY static/ /static/
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Create volume
VOLUME /config
VOLUME /uploads
VOLUME /instance

# Configure Services and Port
CMD ["python3", "/smarthome.py"]

EXPOSE 8181
