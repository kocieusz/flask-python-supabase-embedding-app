from flask import Flask, render_template, request, jsonify
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import OpenAI
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

from supabase import create_client, Client

# Initialize Supabase Client
key = os.environ.get('SUPABASE_KEY')
url = os.environ.get('SUPABASE_URL')
supabase: Client = create_client(url, key)

# Initialize OpenAI Client
opeani_key = url = os.environ.get('OPENAI_KEY')
client = OpenAI(api_key=opeani_key)

app = Flask(__name__)

def calculate_similarity(embedding, embeddings_list):
    similarities = cosine_similarity(embedding, embeddings_list)
    return similarities[0]

def convert_embedding(str_embedding):
    return np.fromstring(str_embedding.strip("[]"), sep=',', dtype=float)

@app.route('/get_similar_ids', methods=['GET'])
def get_similar_ids():
    inputed_text = 'text'

    response = client.embeddings.create(
        input=inputed_text,
        model="text-embedding-ada-002"
    )
    # Convert embedding to numpy array
    embedding = np.array(response.data[0].embedding).reshape(1, -1)

    
    data = supabase.table("embeddings").select("id, embedding").execute().data
    db_embeddings = [convert_embedding(row['embedding']) for row in data]
    ids = [row['id'] for row in data]

    similarities = calculate_similarity(embedding, np.array(db_embeddings))
    top_indices = np.argsort(similarities)[::-1][:5]

    top_ids = [ids[index] for index in top_indices]
    return jsonify(top_ids)

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/search_companies', methods=['GET', 'POST'])
def search_companies():
    if request.method == 'POST':
        # Get user input (text to vectorize and search)
        inputed_text = request.form['inputed_text']

        # Get embeddings from OpenAI
        response = client.embeddings.create(
            input=inputed_text,
            model="text-embedding-ada-002"
        )
        # Convert embedding to numpy array
        embedding = np.array(response.data[0].embedding).reshape(1, -1)

        # Get embeddings from Supabase
        data = supabase.table("embedings").select("company_id, embedding").execute().data
        db_embeddings = [np.fromstring(row['embedding'].strip("[]"), sep=',') for row in data]
        ids = [row['company_id'] for row in data]

        # Calculate similarities and get top 5 IDs
        similarities = cosine_similarity(embedding, np.array(db_embeddings))[0]
        top_indices = np.argsort(similarities)[::-1][:5]
        top_ids = [ids[index] for index in top_indices]
        print(top_ids)

        # Query companies based on top IDs
        companies = supabase.table('raw_companies_database').select("name, size, industry, website, description").in_("id", top_ids).execute().data
        return render_template('results.html', companies=companies)

    return render_template('index.html')

@app.route("/companies-data")
def companies_data():
    response = supabase.table('raw_companies_database').select("name", "size", "industry", "website", "description").execute()
    companies_data = response.data
    if not companies_data:
        return "No data found."
    return render_template("companies-data.html", companies=companies_data)

@app.route("/home")
def home():
    return render_template("home.html")