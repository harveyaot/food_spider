FROM python:3.10

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

# Copy the rest of the application
COPY ./src /app/src
COPY ./data /app/data

# Create directory for Whoosh index
RUN mkdir -p recipe_index

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["python", "src/main.py"] 