# Echo - An AI Mental Health Companion

> Echo is an AI-driven chatbot designed to provide a safe, empathetic, and private space for mental well-being. Built with Python, Streamlit, and Google Gemini Pro, it helps users manage stress, anxiety, and loneliness through persistent multi-chat conversations.

## Key Features
Advanced AI Persona:** Guided by a detailed master prompt for honest empathy and helpful guidance.
Secure User Accounts:** Authentication with password hashing ensures privacy for every user.
Persistent Multi-Chat System:** Users can create and switch between multiple, separate conversations which are all saved permanently to a local SQLite database.
Secret Vent Mode:** A unique privacy feature where a user can enter a completely separate, private space with its own independent chat history.
Personalized Memory:** Echo uses its AI to identify and remember key facts and user strengths to provide context-aware, personalized responses over time.

## Technologies Used

`Python` `Streamlit` `SQLite` `Google Gemini Pro` `bcrypt` `python-dotenv`

## Getting Started

To get a local copy up and running, follow these simple steps.

### Prerequisites

* Python 3.8+
* A Google Gemini API Key

### Installation

1.  Clone the repo:
    ```sh
    git clone [https://github.com/avvaruyasaswini/Echo.git](https://github.com/avvaruyasaswini/Echo.git)
    ```

2.  Navigate into the project folder:
    ```sh
    cd Echo
    ```

3.  Create and activate a virtual environment:
    ```sh
    python -m venv venv
    venv\Scripts\activate
    ```

4.  Install the required packages (you will need to create a `requirements.txt` file for this step):
    ```sh
    pip install -r requirements.txt
    ```

5.  Create a `.env` file in the root directory and add your Google API Key:
    ```
    GOOGLE_API_KEY="YOUR_API_KEY_HERE"
    ```

6.  Run the application:
    ```sh
    streamlit run app.py
    ```
