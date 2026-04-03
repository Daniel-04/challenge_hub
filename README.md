# challenge_hub

Community driven platform for users to share and solve programming challenges. It works entirely without user accounts, and automated moderation.

## Features

* **Anonymous Sessions**: No accounts are needed. Establishing a session requires the browser to solve a Proof of Work algorithm (SHA-256 computation with 5 leading zeroes).
* **Automated Moderation**: Discussion posts and challenges are passed through `all-MiniLM-L6-v2` and `unitary/toxic-bert` NLP models to filter toxic and off-topic discussion.
* **Markdown and Math**: Built-in MathJax processing across all challenges and comments.

## Setup & Installation

### Option 1: Docker

Because challenge_hub uses [an external Python microservice](https://github.com/daniel-04/moderation_api) for moderation inferences, setup is easiest with Docker Compose.

1. Clone repo and `cd` into the project.
2. Run docker compose:

   ```bash
   docker-compose up --build
   ```
3. Access Challenge Hub at `http://localhost:8080/`.

### Option 2: venv

Docker is a terrible thing, and should have never been created.

1. Clone repo and `cd` into the project.
2. Initialize a local python venv and install requirements:

   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Run initial database migrations:

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
4. Export Moderation API URL (optional, ignore for no moderation):

   ```bash
   export MODERATION_API_URL="http://localhost:8080/moderate"
   ```
5. Run development server:

   ```bash
   python manage.py runserver 8000
   ```
6. Access at `http://localhost:8000/`.
