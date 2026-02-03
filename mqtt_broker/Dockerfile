FROM eclipse-mosquitto:latest

COPY mosquitto.conf /mosquitto/config/mosquitto.conf

# Ensure directories have correct permissions
RUN mkdir -p /mosquitto/data /mosquitto/log && \
    chmod -R 777 /mosquitto/data /mosquitto/log
